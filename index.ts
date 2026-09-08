import { createServer, type Server as HttpServer } from "node:http";
import { randomBytes } from "node:crypto";
import { homedir } from "node:os";
import { join } from "node:path";
import { URL } from "node:url";

import { McpServer } from "@modelcontextprotocol/server";
import { serveStdio } from "@modelcontextprotocol/server/stdio";
import { chromium, type BrowserContext, type Page } from "playwright";
import { WebSocketServer, type WebSocket } from "ws";
import * as z from "zod/v4";

/**
 * Browser MCP
 * -----------
 * The MCP transport itself is stdio. The AI host launches this process and
 * sends tool calls over stdin/stdout.
 *
 * A separate localhost-only WebSocket viewer provides a live visual stream.
 * MCP is a tool/context protocol, not a video transport, so keeping the viewer
 * as a small sidecar is both simpler and more accurate than pretending video
 * is a native MCP primitive.
 */

class BrowserRuntime {
  private context: BrowserContext | null = null;
  private page: Page | null = null;

  private httpServer: HttpServer | null = null;
  private wss: WebSocketServer | null = null;
  private streamTimer: NodeJS.Timeout | null = null;
  private streamToken: string | null = null;
  private streamPort: number | null = null;
  private streamFps = 3;
  private streamQuality = 70;

  private ensurePage(): Page {
    if (!this.page || this.page.isClosed()) {
      throw new Error("Browser is not running. Call browser_launch first.");
    }
    return this.page;
  }

  async launch(url = "about:blank", width = 1440, height = 900) {
    if (this.context) {
      await this.close();
    }

    const userDataDir = process.env.MCP_BROWSER_PROFILE_DIR || join(homedir(), ".mcp-browser-profile");
    const common = {
      headless: false,
      viewport: { width, height },
      args: ["--disable-infobars"],
    };

    try {
      // Prefer the user's installed Google Chrome when it exists.
      this.context = await chromium.launchPersistentContext(userDataDir, {
        ...common,
        channel: "chrome",
      });
    } catch (error) {
      console.error("Google Chrome channel was unavailable; falling back to Playwright Chromium.");
      console.error(error instanceof Error ? error.message : String(error));
      this.context = await chromium.launchPersistentContext(userDataDir, common);
    }

    this.page = this.context.pages()[0] ?? (await this.context.newPage());
    await this.page.setViewportSize({ width, height });
    if (url && url !== "about:blank") {
      await this.page.goto(url, { waitUntil: "domcontentloaded" });
    }

    return this.status();
  }

  async status() {
    if (!this.page || this.page.isClosed()) {
      return { running: false, liveViewer: null };
    }
    return {
      running: true,
      url: this.page.url(),
      title: await this.page.title().catch(() => ""),
      liveViewer:
        this.streamToken && this.streamPort
          ? `http://127.0.0.1:${this.streamPort}/?token=${this.streamToken}`
          : null,
    };
  }

  async navigate(url: string) {
    const page = this.ensurePage();
    await page.goto(url, { waitUntil: "domcontentloaded" });
    return { url: page.url(), title: await page.title() };
  }

  async click(selector?: string, x?: number, y?: number, button: "left" | "right" | "middle" = "left") {
    const page = this.ensurePage();
    if (selector) {
      await page.locator(selector).first().click({ button });
      return { clicked: selector, url: page.url() };
    }
    if (typeof x === "number" && typeof y === "number") {
      await page.mouse.click(x, y, { button });
      return { clicked: { x, y, button }, url: page.url() };
    }
    throw new Error("Provide either selector or both x and y coordinates.");
  }

  async type(selector: string, text: string, clear = true) {
    const page = this.ensurePage();
    const locator = page.locator(selector).first();
    await locator.focus();
    if (clear) {
      await locator.fill("");
    }
    await locator.type(text, { delay: 15 });
    return { typed: text.length, selector };
  }

  async press(key: string, selector?: string) {
    const page = this.ensurePage();
    if (selector) {
      await page.locator(selector).first().press(key);
    } else {
      await page.keyboard.press(key);
    }
    return { pressed: key, selector: selector ?? null };
  }

  async pageText(maxChars = 12000) {
    const page = this.ensurePage();
    const text = await page.locator("body").innerText().catch(() => "");
    return {
      url: page.url(),
      title: await page.title().catch(() => ""),
      text: text.slice(0, Math.max(200, Math.min(maxChars, 50000))),
    };
  }

  async screenshot(type: "png" | "jpeg" = "png", quality = 80) {
    const page = this.ensurePage();
    if (type === "jpeg") {
      return page.screenshot({ type: "jpeg", quality: Math.max(20, Math.min(quality, 100)) });
    }
    return page.screenshot({ type: "png" });
  }

  async startLiveView(port = 7311, fps = 3, quality = 70) {
    this.ensurePage();
    await this.stopLiveView();

    this.streamToken = randomBytes(24).toString("hex");
    this.streamPort = Math.max(1024, Math.min(port, 65535));
    this.streamFps = Math.max(1, Math.min(fps, 10));
    this.streamQuality = Math.max(30, Math.min(quality, 90));

    const token = this.streamToken;

    this.httpServer = createServer((req, res) => {
      const requestUrl = new URL(req.url ?? "/", `http://127.0.0.1:${this.streamPort}`);
      if (requestUrl.searchParams.get("token") !== token) {
        res.writeHead(403, { "content-type": "text/plain; charset=utf-8" });
        res.end("Invalid viewer token");
        return;
      }

      res.writeHead(200, {
        "content-type": "text/html; charset=utf-8",
        "cache-control": "no-store",
              });
      res.end(viewerHtml(token));
    });

    this.wss = new WebSocketServer({ server: this.httpServer });
    this.wss.on("connection", (socket, request) => {
      const requestUrl = new URL(request.url ?? "/", `http://127.0.0.1:${this.streamPort}`);
      if (requestUrl.searchParams.get("token") !== token) {
        socket.close(1008, "Invalid token");
        return;
      }
      this.attachViewerInput(socket);
    });

    await new Promise<void>((resolve, reject) => {
      this.httpServer!.once("error", reject);
      this.httpServer!.listen(this.streamPort!, "127.0.0.1", () => resolve());
    });

    this.scheduleFrame();

    return {
      viewerUrl: `http://127.0.0.1:${this.streamPort}/?token=${token}`,
      boundTo: "127.0.0.1",
      fps: this.streamFps,
      note: "Open this local URL in a browser or a host side panel that supports local web views.",
    };
  }

  private attachViewerInput(socket: WebSocket) {
    socket.on("message", async (raw) => {
      try {
        const page = this.ensurePage();
        const message = JSON.parse(raw.toString()) as Record<string, unknown>;

        if (message.type === "click") {
          const x = Number(message.x);
          const y = Number(message.y);
          if (Number.isFinite(x) && Number.isFinite(y)) {
            await page.mouse.click(x, y);
          }
        } else if (message.type === "text") {
          const text = String(message.text ?? "");
          if (text) await page.keyboard.insertText(text);
        } else if (message.type === "key") {
          const key = String(message.key ?? "");
          if (key) await page.keyboard.press(key);
        }
      } catch (error) {
        console.error("Viewer input error:", error instanceof Error ? error.message : String(error));
      }
    });
  }

  private scheduleFrame() {
    if (!this.wss || !this.page || this.page.isClosed()) return;

    const delay = Math.round(1000 / this.streamFps);
    this.streamTimer = setTimeout(async () => {
      try {
        if (this.wss && this.wss.clients.size > 0 && this.page && !this.page.isClosed()) {
          const jpg = await this.page.screenshot({ type: "jpeg", quality: this.streamQuality });
          const viewport = this.page.viewportSize();
          const payload = JSON.stringify({
            type: "frame",
            data: jpg.toString("base64"),
            width: viewport?.width ?? 0,
            height: viewport?.height ?? 0,
            url: this.page.url(),
            title: await this.page.title().catch(() => ""),
          });
          for (const client of this.wss.clients) {
            if (client.readyState === 1) client.send(payload);
          }
        }
      } catch (error) {
        console.error("Live-view frame error:", error instanceof Error ? error.message : String(error));
      } finally {
        this.scheduleFrame();
      }
    }, delay);
  }

  async stopLiveView() {
    if (this.streamTimer) clearTimeout(this.streamTimer);
    this.streamTimer = null;

    if (this.wss) {
      for (const client of this.wss.clients) client.close();
      this.wss.close();
      this.wss = null;
    }

    if (this.httpServer) {
      await new Promise<void>((resolve) => this.httpServer!.close(() => resolve())).catch(() => undefined);
      this.httpServer = null;
    }

    this.streamToken = null;
    this.streamPort = null;
  }

  async close() {
    await this.stopLiveView();
    if (this.context) await this.context.close().catch(() => undefined);
    this.context = null;
    this.page = null;
    return { closed: true };
  }
}

function viewerHtml(token: string) {
  return `<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width,initial-scale=1" />
<title>MCP Browser Live View</title>
<style>
  *{box-sizing:border-box} body{margin:0;font-family:Inter,system-ui,sans-serif;background:#0b0d12;color:#fff}
  header{height:48px;display:flex;align-items:center;gap:12px;padding:0 14px;border-bottom:1px solid #262b35;background:#11141b}
  #status{font-size:12px;color:#9aa4b2}.dot{width:8px;height:8px;border-radius:50%;background:#42d392;display:inline-block;margin-right:6px}
  main{height:calc(100vh - 96px);display:grid;place-items:center;padding:8px;overflow:hidden}
  #screen{max-width:100%;max-height:100%;object-fit:contain;border:1px solid #2b3240;border-radius:8px;outline:none;cursor:default;background:#080a0e}
  footer{height:48px;display:flex;gap:8px;padding:8px;border-top:1px solid #262b35;background:#11141b}
  input{flex:1;border:1px solid #303746;border-radius:7px;background:#0b0d12;color:#fff;padding:0 10px}
  button{border:0;border-radius:7px;padding:0 14px;font-weight:650;cursor:pointer}
</style>
</head>
<body>
<header><span><span class="dot"></span>MCP Browser Live View</span><span id="status">connecting…</span></header>
<main><img id="screen" tabindex="0" alt="Live browser frame" /></main>
<footer><input id="text" placeholder="Type into the currently focused browser element"/><button id="send">Send</button></footer>
<script>
  const token=${JSON.stringify(token)};
  const ws=new WebSocket('ws://127.0.0.1:'+location.port+'/?token='+encodeURIComponent(token));
  const screen=document.getElementById('screen'); const status=document.getElementById('status');
  ws.onopen=()=>status.textContent='connected'; ws.onclose=()=>status.textContent='disconnected';
  ws.onmessage=(event)=>{const m=JSON.parse(event.data); if(m.type==='frame'){screen.src='data:image/jpeg;base64,'+m.data; status.textContent=(m.title||m.url||'connected');}};
  screen.addEventListener('click',(event)=>{const r=screen.getBoundingClientRect(); if(!screen.naturalWidth)return; const x=(event.clientX-r.left)*(screen.naturalWidth/r.width); const y=(event.clientY-r.top)*(screen.naturalHeight/r.height); ws.send(JSON.stringify({type:'click',x,y})); screen.focus();});
  screen.addEventListener('keydown',(event)=>{if(['Tab','Enter','Escape','ArrowUp','ArrowDown','ArrowLeft','ArrowRight','Backspace','Delete','Home','End','PageUp','PageDown'].includes(event.key)){event.preventDefault();ws.send(JSON.stringify({type:'key',key:event.key}));}});
  document.getElementById('send').addEventListener('click',()=>{const input=document.getElementById('text'); if(input.value){ws.send(JSON.stringify({type:'text',text:input.value}));input.value='';screen.focus();}});
  document.getElementById('text').addEventListener('keydown',(event)=>{if(event.key==='Enter'){event.preventDefault();document.getElementById('send').click();}});
</script>
</body></html>`;
}

const runtime = new BrowserRuntime();

function textResult(value: unknown) {
  return { content: [{ type: "text" as const, text: JSON.stringify(value, null, 2) }] };
}

function buildServer() {
  const server = new McpServer({ name: "browser-dual-control", version: "1.0.0" });

  server.registerTool(
    "browser_launch",
    {
      description: "Launch a visible real Chrome window (or Chromium fallback) that both the user and AI can operate.",
      inputSchema: z.object({
        url: z.string().default("about:blank"),
        width: z.number().int().min(800).max(3840).default(1440),
        height: z.number().int().min(600).max(2160).default(900),
      }),
    },
    async ({ url, width, height }) => textResult(await runtime.launch(url, width, height)),
  );

  server.registerTool(
    "browser_status",
    { description: "Return current browser and live-view status.", inputSchema: z.object({}) },
    async () => textResult(await runtime.status()),
  );

  server.registerTool(
    "browser_navigate",
    {
      description: "Navigate the current browser tab to an absolute URL.",
      inputSchema: z.object({ url: z.string().url() }),
    },
    async ({ url }) => textResult(await runtime.navigate(url)),
  );

  server.registerTool(
    "browser_click",
    {
      description: "Click an element by CSS/text locator, or click exact viewport coordinates.",
      inputSchema: z.object({
        selector: z.string().optional(),
        x: z.number().optional(),
        y: z.number().optional(),
        button: z.enum(["left", "right", "middle"]).default("left"),
      }),
    },
    async ({ selector, x, y, button }) => textResult(await runtime.click(selector, x, y, button)),
  );

  server.registerTool(
    "browser_type",
    {
      description: "Focus an element and type text into it.",
      inputSchema: z.object({
        selector: z.string(),
        text: z.string(),
        clear: z.boolean().default(true),
      }),
    },
    async ({ selector, text, clear }) => textResult(await runtime.type(selector, text, clear)),
  );

  server.registerTool(
    "browser_press",
    {
      description: "Press a Playwright keyboard key/combo, optionally on a specific element.",
      inputSchema: z.object({ key: z.string(), selector: z.string().optional() }),
    },
    async ({ key, selector }) => textResult(await runtime.press(key, selector)),
  );

  server.registerTool(
    "browser_page_text",
    {
      description: "Read visible page text so the model can reason about the current page without relying only on pixels.",
      inputSchema: z.object({ maxChars: z.number().int().min(200).max(50000).default(12000) }),
    },
    async ({ maxChars }) => textResult(await runtime.pageText(maxChars)),
  );

  server.registerTool(
    "browser_screenshot",
    {
      description: "Capture the current browser viewport and return it as an MCP image content block.",
      inputSchema: z.object({
        type: z.enum(["png", "jpeg"]).default("png"),
        quality: z.number().int().min(20).max(100).default(80),
      }),
    },
    async ({ type, quality }) => {
      const image = await runtime.screenshot(type, quality);
      return {
        content: [
          {
            type: "image" as const,
            data: image.toString("base64"),
            mimeType: type === "png" ? "image/png" : "image/jpeg",
          },
        ],
      };
    },
  );

  server.registerTool(
    "browser_start_live_view",
    {
      description: "Start a localhost-only WebSocket live viewer with shared mouse/keyboard input.",
      inputSchema: z.object({
        port: z.number().int().min(1024).max(65535).default(7311),
        fps: z.number().int().min(1).max(10).default(3),
        quality: z.number().int().min(30).max(90).default(70),
      }),
    },
    async ({ port, fps, quality }) => textResult(await runtime.startLiveView(port, fps, quality)),
  );

  server.registerTool(
    "browser_stop_live_view",
    { description: "Stop the localhost live viewer.", inputSchema: z.object({}) },
    async () => {
      await runtime.stopLiveView();
      return textResult({ stopped: true });
    },
  );

  server.registerTool(
    "browser_close",
    { description: "Close the browser and viewer.", inputSchema: z.object({}) },
    async () => textResult(await runtime.close()),
  );

  return server;
}

process.on("SIGINT", () => void runtime.close().finally(() => process.exit(0)));
process.on("SIGTERM", () => void runtime.close().finally(() => process.exit(0)));

// serveStdio keeps stdout reserved for the MCP protocol. Diagnostic logs go to stderr.
void serveStdio(buildServer);
console.error("Browser Dual-Control MCP is ready on stdio.");
