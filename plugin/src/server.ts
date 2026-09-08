import { randomUUID } from "node:crypto";
import { createServer } from "node:http";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

import cors from "cors";
import express from "express";
import { WebSocket, WebSocketServer } from "ws";
import { z } from "zod";

import {
  registerAppResource,
  registerAppTool,
  RESOURCE_MIME_TYPE,
} from "@modelcontextprotocol/ext-apps/server";
import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StreamableHTTPServerTransport } from "@modelcontextprotocol/sdk/server/streamableHttp.js";

const PORT = Number(process.env.PORT || 8787);
const HOST = process.env.HOST || "0.0.0.0";
const WIDGET_URI = "ui://mcp-control-hub/control-panel-v1.html";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const widgetHtml = fs.readFileSync(path.resolve(__dirname, "..", "widget", "index.html"), "utf8");
const assetsDirectory = path.resolve(__dirname, "..", "assets");

type Companion = {
  code: string;
  socket: WebSocket;
  connectedAt: number;
};

type Pending = {
  resolve: (value: unknown) => void;
  reject: (error: Error) => void;
  timer: NodeJS.Timeout;
};

const companions = new Map<string, Companion>();
const sessions = new Map<string, { pairingCode: string; lastUsed: number }>();
const pending = new Map<string, Pending>();

type BrowserResult = {
  base64?: string;
  width?: number;
  height?: number;
  url?: string;
  title?: string;
  [key: string]: unknown;
};

function browserToolResult(message: string, result: BrowserResult) {
  return {
    content: [
      { type: "text" as const, text: message },
      ...(result.base64
        ? [{ type: "image" as const, data: result.base64, mimeType: "image/png" }]
        : []),
    ],
    structuredContent: {
      mode: "chrome",
      url: result.url,
      title: result.title,
      width: result.width,
      height: result.height,
    },
  };
}

function normalizePairingCode(value: string) {
  return value.trim().toUpperCase().replace(/[^A-Z0-9]/g, "");
}

function getPairingCodeForSession(sessionToken?: string) {
  if (sessionToken) {
    const session = sessions.get(sessionToken);
    if (session) {
      session.lastUsed = Date.now();
      return session.pairingCode;
    }

    // Some MCP clients pass the pairing code back instead of structuredContent.
    const possiblePairingCode = normalizePairingCode(sessionToken);
    if (companions.get(possiblePairingCode)?.socket.readyState === WebSocket.OPEN) {
      return possiblePairingCode;
    }
  }

  // Personal installations normally have one online companion. Let clients
  // continue after pair_device even when they do not retain its session token.
  const onlineCompanions = [...companions.values()].filter(
    (companion) => companion.socket.readyState === WebSocket.OPEN,
  );
  if (onlineCompanions.length === 1) return onlineCompanions[0].code;
  if (onlineCompanions.length === 0) {
    throw new Error("The MCP Control Hub Companion is offline. Start it and try again.");
  }
  throw new Error("More than one companion is online. Pair this chat again before controlling a computer.");
}

async function sendCommand(pairingCode: string, operation: string, args: Record<string, unknown>) {
  const companion = companions.get(pairingCode);
  if (!companion || companion.socket.readyState !== WebSocket.OPEN) {
    throw new Error("The MCP Control Hub Companion is offline. Start it on the paired computer and try again.");
  }

  const id = randomUUID();
  const payload = JSON.stringify({ id, operation, args });

  return await new Promise<unknown>((resolve, reject) => {
    const timer = setTimeout(() => {
      pending.delete(id);
      reject(new Error(`Timed out waiting for the local companion while running ${operation}.`));
    }, 90_000);

    pending.set(id, { resolve, reject, timer });
    companion.socket.send(payload, (error) => {
      if (!error) return;
      clearTimeout(timer);
      pending.delete(id);
      reject(error);
    });
  });
}

function createPluginServer() {
  const server = new McpServer(
    { name: "mcp-control-hub", version: "0.1.0" },
    {
      instructions:
        "MCP Control Hub controls the user's paired local computer. Pair once with pair_device, then use Chrome tools for browser-only work and Computer tools for whole-screen input. Prefer the least-powerful tool that completes the task.",
    },
  );

  registerAppResource(
    server,
    "MCP Control Hub panel",
    WIDGET_URI,
    {
      mimeType: RESOURCE_MIME_TYPE,
      description: "Status panel for MCP Control Hub pairing and control modes.",
    },
    async () => ({
      contents: [
        {
          uri: WIDGET_URI,
          mimeType: RESOURCE_MIME_TYPE,
          text: widgetHtml,
          _meta: {
            ui: {
              prefersBorder: true,
              csp: { connectDomains: [], resourceDomains: [] },
            },
          },
        },
      ],
    }),
  );

  registerAppTool(
    server,
    "pair_device",
    {
      title: "Pair MCP Control Hub",
      description: "Use this when the user wants to connect their locally installed MCP Control Hub Companion to the plugin.",
      inputSchema: { pairing_code: z.string().min(6).max(32) },
      annotations: { readOnlyHint: true, destructiveHint: false, openWorldHint: false },
      _meta: { ui: { resourceUri: WIDGET_URI } },
    },
    async ({ pairing_code }) => {
      const code = normalizePairingCode(pairing_code);
      const companion = companions.get(code);
      if (!companion || companion.socket.readyState !== WebSocket.OPEN) {
        return {
          isError: true,
          content: [{ type: "text" as const, text: "No online companion was found for that pairing code." }],
          structuredContent: { paired: false },
        };
      }

      const sessionToken = randomUUID();
      sessions.set(sessionToken, { pairingCode: code, lastUsed: Date.now() });
      return {
        content: [{ type: "text" as const, text: "Paired successfully. Chrome Control and Computer Control are ready." }],
        structuredContent: {
          paired: true,
          session_token: sessionToken,
          capabilities: ["chrome", "computer"],
        },
      };
    },
  );

  registerAppTool(
    server,
    "control_status",
    {
      title: "Check control status",
      description: "Use this when the user wants to know whether their paired computer is currently connected.",
      inputSchema: { session_token: z.string().optional() },
      annotations: { readOnlyHint: true, destructiveHint: false, openWorldHint: false },
      _meta: { ui: { resourceUri: WIDGET_URI } },
    },
    async ({ session_token }) => {
      const code = getPairingCodeForSession(session_token);
      const online = companions.get(code)?.socket.readyState === WebSocket.OPEN;
      return {
        content: [{ type: "text" as const, text: online ? "The paired computer is online." : "The paired computer is offline." }],
        structuredContent: { paired: true, online },
      };
    },
  );

  const sessionSchema = { session_token: z.string().optional() };

  registerAppTool(
    server,
    "chrome_open",
    {
      title: "Open Chrome",
      description: "Use this when the user wants to open the controlled Chrome browser on their paired computer.",
      inputSchema: sessionSchema,
      annotations: { readOnlyHint: false, destructiveHint: false, openWorldHint: true },
      _meta: { ui: { resourceUri: WIDGET_URI } },
    },
    async ({ session_token }) => {
      const result = (await sendCommand(getPairingCodeForSession(session_token), "browser.open", {})) as BrowserResult;
      return browserToolResult("Chrome is open and ready. Use the screenshot to continue.", result);
    },
  );

  registerAppTool(
    server,
    "chrome_navigate",
    {
      title: "Navigate Chrome",
      description: "Use this when the user wants the paired Chrome browser to open a URL.",
      inputSchema: { session_token: z.string().optional(), url: z.string().url() },
      annotations: { readOnlyHint: false, destructiveHint: false, openWorldHint: true },
      _meta: { ui: { resourceUri: WIDGET_URI } },
    },
    async ({ session_token, url }) => {
      const result = (await sendCommand(getPairingCodeForSession(session_token), "browser.navigate", { url })) as BrowserResult;
      return browserToolResult(`Opened ${url} in Chrome. Use the screenshot to continue.`, result);
    },
  );

  registerAppTool(
    server,
    "chrome_click",
    {
      title: "Click in Chrome",
      description: "Click a Chrome element by its visible text when possible. Use screenshot coordinates only when the element has no useful text.",
      inputSchema: {
        session_token: z.string().optional(),
        element_text: z.string().optional(),
        x: z.number().nonnegative().optional(),
        y: z.number().nonnegative().optional(),
      },
      annotations: { readOnlyHint: false, destructiveHint: false, openWorldHint: true },
      _meta: { ui: { resourceUri: WIDGET_URI } },
    },
    async ({ session_token, element_text, x, y }) => {
      const operation = element_text ? "browser.click_text" : "browser.click";
      if (!element_text && (x === undefined || y === undefined)) {
        throw new Error("Provide element_text or both x and y.");
      }
      const result = (await sendCommand(getPairingCodeForSession(session_token), operation, element_text ? { text: element_text } : { x, y })) as BrowserResult;
      return browserToolResult(element_text ? `Clicked “${element_text}”. Use the updated screenshot to continue.` : `Clicked Chrome at ${x}, ${y}. Use the updated screenshot to continue.`, result);
    },
  );

  registerAppTool(
    server,
    "chrome_type",
    {
      title: "Type in Chrome",
      description: "Enter Unicode text in Chrome. Provide target with the field label or placeholder when the field is not already focused.",
      inputSchema: { session_token: z.string().optional(), text: z.string().max(10_000), target: z.string().optional() },
      annotations: { readOnlyHint: false, destructiveHint: false, openWorldHint: true },
      _meta: { ui: { resourceUri: WIDGET_URI } },
    },
    async ({ session_token, text, target }) => {
      const result = (await sendCommand(getPairingCodeForSession(session_token), target ? "browser.fill" : "browser.type", target ? { text, target } : { text })) as BrowserResult;
      return browserToolResult("Typed the requested text in Chrome. Use the updated screenshot to continue.", result);
    },
  );

  registerAppTool(
    server,
    "chrome_press",
    {
      title: "Press a key in Chrome",
      description: "Press a keyboard key such as Enter, Tab, Escape, ArrowDown, or Control+A in the controlled Chrome page.",
      inputSchema: { session_token: z.string().optional(), key: z.string().min(1).max(80) },
      annotations: { readOnlyHint: false, destructiveHint: false, openWorldHint: true },
      _meta: { ui: { resourceUri: WIDGET_URI } },
    },
    async ({ session_token, key }) => {
      const result = (await sendCommand(getPairingCodeForSession(session_token), "browser.press", { key })) as BrowserResult;
      return browserToolResult(`Pressed ${key} in Chrome. Use the updated screenshot to continue.`, result);
    },
  );

  registerAppTool(
    server,
    "chrome_snapshot",
    {
      title: "See Chrome",
      description: "Use this when the AI needs a fresh screenshot of the controlled Chrome page before deciding what to do next.",
      inputSchema: sessionSchema,
      annotations: { readOnlyHint: true, destructiveHint: false, openWorldHint: false },
      _meta: { ui: { resourceUri: WIDGET_URI } },
    },
    async ({ session_token }) => {
      const result = (await sendCommand(getPairingCodeForSession(session_token), "browser.snapshot", {})) as { base64?: string; width?: number; height?: number };
      if (!result?.base64) throw new Error("The local companion did not return a Chrome screenshot.");
      const elements = Array.isArray((result as BrowserResult).elements)
        ? JSON.stringify((result as BrowserResult).elements)
        : "[]";
      return {
        content: [
          { type: "text" as const, text: `Fresh Chrome screenshot. Visible interactive elements: ${elements}` },
          { type: "image" as const, data: result.base64, mimeType: "image/png" },
        ],
        structuredContent: { mode: "chrome", width: result.width, height: result.height },
      };
    },
  );

  registerAppTool(
    server,
    "computer_windows",
    {
      title: "List desktop windows",
      description: "List visible desktop window titles before taking a desktop screenshot. Use a returned title with computer_snapshot to avoid capturing the Claude or ChatGPT window.",
      inputSchema: sessionSchema,
      annotations: { readOnlyHint: true, destructiveHint: false, openWorldHint: false },
      _meta: { ui: { resourceUri: WIDGET_URI } },
    },
    async ({ session_token }) => {
      const result = (await sendCommand(getPairingCodeForSession(session_token), "computer.windows", {})) as { windows?: string[] };
      return {
        content: [{ type: "text" as const, text: `Visible desktop windows: ${JSON.stringify(result.windows || [])}` }],
        structuredContent: { windows: result.windows || [] },
      };
    },
  );

  registerAppTool(
    server,
    "computer_snapshot",
    {
      title: "See the computer screen",
      description: "Capture a specific desktop app window. Call computer_windows first and pass window_title. Do not capture the Claude or ChatGPT window because that creates a recursive screenshot.",
      inputSchema: { session_token: z.string().optional(), window_title: z.string().optional() },
      annotations: { readOnlyHint: true, destructiveHint: false, openWorldHint: false },
      _meta: { ui: { resourceUri: WIDGET_URI } },
    },
    async ({ session_token, window_title }) => {
      const result = (await sendCommand(getPairingCodeForSession(session_token), "computer.snapshot", { window_title })) as BrowserResult;
      if (!result?.base64) throw new Error("The local companion did not return a desktop screenshot.");
      return {
        content: [
          { type: "text" as const, text: window_title ? `Fresh screenshot of desktop window “${window_title}”. Coordinates are relative to this image.` : "Fresh full-desktop screenshot. Prefer passing a non-Claude window_title to avoid recursive captures." },
          { type: "image" as const, data: result.base64, mimeType: "image/png" },
        ],
        structuredContent: { mode: "computer", width: result.width, height: result.height, window_title: result.window_title },
      };
    },
  );

  registerAppTool(
    server,
    "mouse_move",
    {
      title: "Move mouse",
      description: "Use this when the user wants the AI to move the mouse pointer on the paired computer.",
      inputSchema: { session_token: z.string().optional(), x: z.number().nonnegative(), y: z.number().nonnegative(), duration: z.number().min(0).max(5).optional() },
      annotations: { readOnlyHint: false, destructiveHint: false, openWorldHint: false },
      _meta: { ui: { resourceUri: WIDGET_URI } },
    },
    async ({ session_token, x, y, duration }) => {
      await sendCommand(getPairingCodeForSession(session_token), "mouse.move", { x, y, duration });
      return { content: [{ type: "text" as const, text: `Moved the mouse to ${x}, ${y}.` }] };
    },
  );

  registerAppTool(
    server,
    "mouse_click",
    {
      title: "Click mouse",
      description: "Click a desktop coordinate from the latest computer_snapshot. Coordinates must use the original screenshot width and height returned by that tool.",
      inputSchema: { session_token: z.string().optional(), x: z.number().nonnegative().optional(), y: z.number().nonnegative().optional(), button: z.enum(["left", "right", "middle"]).default("left"), clicks: z.number().int().min(1).max(3).default(1) },
      annotations: { readOnlyHint: false, destructiveHint: false, openWorldHint: false },
      _meta: { ui: { resourceUri: WIDGET_URI } },
    },
    async ({ session_token, x, y, button, clicks }) => {
      const result = (await sendCommand(getPairingCodeForSession(session_token), "mouse.click", { x, y, button, clicks })) as BrowserResult;
      return {
        content: [
          { type: "text" as const, text: `Clicked the ${button} mouse button${x !== undefined && y !== undefined ? ` at ${x}, ${y}` : ""}.` },
          ...(result.base64 ? [{ type: "image" as const, data: result.base64, mimeType: "image/png" }] : []),
        ],
        structuredContent: { mode: "computer", width: result.width, height: result.height },
      };
    },
  );

  registerAppTool(
    server,
    "keyboard_type",
    {
      title: "Type on the computer",
      description: "Paste Unicode text, including Hebrew, into the focused desktop field. Optionally press Enter afterward.",
      inputSchema: { session_token: z.string().optional(), text: z.string().max(10_000), press_enter: z.boolean().optional() },
      annotations: { readOnlyHint: false, destructiveHint: false, openWorldHint: false },
      _meta: { ui: { resourceUri: WIDGET_URI } },
    },
    async ({ session_token, text, press_enter }) => {
      const result = (await sendCommand(getPairingCodeForSession(session_token), "keyboard.type", { text, press_enter })) as BrowserResult;
      return {
        content: [
          { type: "text" as const, text: "Pasted the requested Unicode text on the paired computer." },
          ...(result.base64 ? [{ type: "image" as const, data: result.base64, mimeType: "image/png" }] : []),
        ],
        structuredContent: { mode: "computer", width: result.width, height: result.height },
      };
    },
  );

  return server;
}

const app = express();
app.use(
  cors({
    origin: true,
    methods: ["GET", "POST", "DELETE", "OPTIONS"],
    allowedHeaders: ["Content-Type", "Mcp-Session-Id", "MCP-Protocol-Version", "Accept"],
    exposedHeaders: ["Mcp-Session-Id"],
  }),
);
app.use(express.json({ limit: "4mb" }));
app.use("/assets", express.static(assetsDirectory, { maxAge: "1d", immutable: false }));

app.get("/", (_req, res) => {
  res.type("html").send(`<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>MCP Control Hub</title>
    <link rel="icon" href="/assets/icon.png" />
    <style>
      :root { color-scheme: dark; font-family: Inter, ui-sans-serif, system-ui, sans-serif; }
      body { min-height: 100vh; margin: 0; display: grid; place-items: center; background: #041936; color: #fff; }
      main { width: min(520px, calc(100% - 48px)); text-align: center; }
      img { width: 180px; height: 180px; border-radius: 36px; box-shadow: 0 20px 60px #0008; }
      h1 { margin: 24px 0 8px; font-size: clamp(2rem, 7vw, 3rem); }
      p { margin: 8px 0; color: #b7d7ff; line-height: 1.6; }
      code { color: #28e2ff; }
    </style>
  </head>
  <body>
    <main>
      <img src="/assets/logo.png" alt="MCP Control Hub logo" />
      <h1>MCP Control Hub</h1>
      <p>The service is online and ready for ChatGPT.</p>
      <p>Streamable HTTP endpoint: <code>/mcp</code></p>
    </main>
  </body>
</html>`);
});

app.get("/health", (_req, res) => {
  res.json({ ok: true, service: "mcp-control-hub-plugin", companions: companions.size });
});

async function handleMcp(req: express.Request, res: express.Response) {
  const server = createPluginServer();
  const transport = new StreamableHTTPServerTransport({
    sessionIdGenerator: undefined,
    enableJsonResponse: true,
  });

  res.on("close", () => {
    void transport.close();
    void server.close();
  });

  try {
    await server.connect(transport);
    await transport.handleRequest(req, res, req.method === "POST" ? req.body : undefined);
  } catch (error) {
    console.error("Error handling MCP request:", error);
    if (!res.headersSent) res.status(500).send("Internal server error");
  }
}

app.post("/mcp", handleMcp);
app.get(
  "/mcp",
  (req, res, next) => {
    const accept = (req.header("accept") || "").toLowerCase();
    if (accept.includes("text/event-stream")) {
      next();
      return;
    }

    res.json({
      ok: true,
      service: "mcp-control-hub-plugin",
      transport: "streamable-http",
      message: "MCP endpoint is ready. Connect ChatGPT to this URL.",
    });
  },
  handleMcp,
);
app.delete("/mcp", handleMcp);

const httpServer = createServer(app);
const wss = new WebSocketServer({ noServer: true });

httpServer.on("upgrade", (req, socket, head) => {
  const url = new URL(req.url || "/", `http://${req.headers.host || "localhost"}`);
  if (url.pathname !== "/companion") {
    socket.destroy();
    return;
  }
  const code = normalizePairingCode(url.searchParams.get("code") || "");
  if (code.length < 6) {
    socket.destroy();
    return;
  }
  wss.handleUpgrade(req, socket, head, (ws) => {
    (ws as WebSocket & { pairingCode?: string }).pairingCode = code;
    wss.emit("connection", ws, req);
  });
});

wss.on("connection", (socket) => {
  const code = (socket as WebSocket & { pairingCode?: string }).pairingCode!;
  const old = companions.get(code);
  if (old && old.socket !== socket) old.socket.close(4000, "New companion connection replaced this one.");
  companions.set(code, { code, socket, connectedAt: Date.now() });

  socket.on("message", (raw) => {
    try {
      const message = JSON.parse(raw.toString()) as { id?: string; ok?: boolean; result?: unknown; error?: string };
      if (!message.id) return;
      const waiter = pending.get(message.id);
      if (!waiter) return;
      clearTimeout(waiter.timer);
      pending.delete(message.id);
      if (message.ok === false) waiter.reject(new Error(message.error || "Local companion command failed."));
      else waiter.resolve(message.result);
    } catch {
      // Ignore malformed companion messages rather than crashing the plugin server.
    }
  });

  socket.on("close", () => {
    if (companions.get(code)?.socket === socket) companions.delete(code);
  });
});

setInterval(() => {
  const cutoff = Date.now() - 12 * 60 * 60 * 1000;
  for (const [token, session] of sessions) {
    if (session.lastUsed < cutoff) sessions.delete(token);
  }
}, 15 * 60 * 1000).unref();

httpServer.listen(PORT, HOST, () => {
  console.log(`MCP Control Hub plugin server listening on http://${HOST}:${PORT}`);
  console.log(`MCP endpoint: http://${HOST}:${PORT}/mcp`);
  console.log(`Companion WebSocket: ws://${HOST}:${PORT}/companion?code=PAIRING_CODE`);
});
