# MCP Control Hub Plugin

This folder is the ChatGPT Plugin/App version of MCP Control Hub. Users should not configure local stdio MCP entries manually.

## Architecture

- `src/server.ts` — remote ChatGPT Plugin server. It exposes a Streamable HTTP MCP endpoint at `/mcp` and a WebSocket endpoint at `/companion`.
- `widget/index.html` — ChatGPT embedded UI with separate **Chrome Control** and **Computer Control** modes.
- `companion/` — local Windows companion. It keeps the real browser, screen, mouse and keyboard on the user's computer.
- Pairing is one-time per plugin session. The local companion displays an 8-character code; call `pair_device` with that code to obtain a short-lived `session_token` for later tool calls.

## Plugin tools

### Pairing

- `pair_device`
- `control_status`

### Chrome Control

- `chrome_open`
- `chrome_navigate`
- `chrome_click`
- `chrome_type`
- `chrome_snapshot`

### Computer Control

- `computer_snapshot`
- `mouse_move`
- `mouse_click`
- `keyboard_type`

## Local development

```bash
cd plugin
npm install
npm run build
npm start
```

The plugin server starts on port `8787` by default:

- MCP: `http://localhost:8787/mcp`
- Companion socket: `ws://localhost:8787/companion`
- Health: `http://localhost:8787/health`

### Windows companion

From `plugin/companion` run:

```powershell
powershell -ExecutionPolicy Bypass -File .\INSTALL-WINDOWS.ps1
```

Then start:

```text
%LOCALAPPDATA%\MCP-Control-Hub-Plugin\START-COMPANION.cmd
```

For a deployed plugin, set `MCP_CONTROL_HUB_PLUGIN_WS` to the public secure WebSocket URL before starting the companion, for example:

```powershell
$env:MCP_CONTROL_HUB_PLUGIN_WS='wss://YOUR-SERVICE.onrender.com/companion'
& "$env:LOCALAPPDATA\MCP-Control-Hub-Plugin\START-COMPANION.cmd"
```

## Deploy

`render.yaml` is included because the plugin needs a long-lived WebSocket connection from the local companion. Deploy the `plugin` directory as a Node web service, then connect ChatGPT to:

```text
https://YOUR-SERVICE.onrender.com/mcp
```

The local companion must connect to:

```text
wss://YOUR-SERVICE.onrender.com/companion
```

## Current status

This is the first end-to-end plugin architecture: remote plugin server, embedded ChatGPT UI, pairing, Chrome actions, desktop screenshots, mouse and keyboard actions, and the local companion transport. Before public release, add production authentication, durable session storage, rate limiting, TLS-only companion connections, explicit permission UI, and a public privacy policy.

## OpenAI docs used

- https://developers.openai.com/plugins/build/app-quickstart
- https://developers.openai.com/plugins/build/mcp-server
- https://developers.openai.com/plugins/build/chatgpt-ui
- https://developers.openai.com/plugins/reference
