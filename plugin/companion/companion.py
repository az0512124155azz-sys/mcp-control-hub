from __future__ import annotations

import base64
import io
import json
import os
import secrets
import time
from pathlib import Path
from typing import Any

import pyautogui
import websocket
from playwright.sync_api import BrowserContext, Page, sync_playwright

APP_DIR = Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "MCP-Control-Hub"
PAIRING_FILE = APP_DIR / "pairing-code.txt"
PLUGIN_WS_URL = os.environ.get(
    "MCP_CONTROL_HUB_PLUGIN_WS",
    "wss://mcp-control-hub-plugin.onrender.com/companion",
)

APP_DIR.mkdir(parents=True, exist_ok=True)


def get_pairing_code() -> str:
    if PAIRING_FILE.exists():
        code = PAIRING_FILE.read_text(encoding="utf-8").strip().upper()
        if code:
            return code
    alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
    code = "".join(secrets.choice(alphabet) for _ in range(8))
    PAIRING_FILE.write_text(code + "\n", encoding="utf-8")
    return code


class BrowserController:
    def __init__(self) -> None:
        self._pw = None
        self._context: BrowserContext | None = None
        self._page: Page | None = None

    def ensure(self) -> Page:
        if self._page and not self._page.is_closed():
            return self._page
        if self._pw is None:
            self._pw = sync_playwright().start()
        profile = APP_DIR / "chrome-profile"
        profile.mkdir(parents=True, exist_ok=True)
        self._context = self._pw.chromium.launch_persistent_context(
            str(profile),
            headless=False,
            channel="chrome",
            viewport={"width": 1440, "height": 900},
            args=["--disable-infobars"],
        )
        pages = self._context.pages
        self._page = pages[0] if pages else self._context.new_page()
        return self._page

    def open(self) -> dict[str, Any]:
        page = self.ensure()
        return {"url": page.url}

    def navigate(self, url: str) -> dict[str, Any]:
        page = self.ensure()
        page.goto(url, wait_until="domcontentloaded", timeout=30000)
        return {"url": page.url, "title": page.title()}

    def click(self, x: float, y: float) -> dict[str, Any]:
        page = self.ensure()
        page.mouse.click(x, y)
        return {"clicked": True, "x": x, "y": y}

    def type_text(self, text: str) -> dict[str, Any]:
        page = self.ensure()
        page.keyboard.type(text)
        return {"typed": len(text)}

    def snapshot(self) -> dict[str, Any]:
        page = self.ensure()
        png = page.screenshot(type="png")
        return {
            "base64": base64.b64encode(png).decode("ascii"),
            "width": page.viewport_size["width"] if page.viewport_size else None,
            "height": page.viewport_size["height"] if page.viewport_size else None,
            "url": page.url,
        }


browser = BrowserController()


def desktop_snapshot() -> dict[str, Any]:
    shot = pyautogui.screenshot()
    buf = io.BytesIO()
    shot.save(buf, format="PNG")
    return {
        "base64": base64.b64encode(buf.getvalue()).decode("ascii"),
        "width": shot.width,
        "height": shot.height,
    }


def run_operation(operation: str, args: dict[str, Any]) -> Any:
    if operation == "browser.open":
        return browser.open()
    if operation == "browser.navigate":
        return browser.navigate(str(args["url"]))
    if operation == "browser.click":
        return browser.click(float(args["x"]), float(args["y"]))
    if operation == "browser.type":
        return browser.type_text(str(args["text"]))
    if operation == "browser.snapshot":
        return browser.snapshot()
    if operation == "computer.snapshot":
        return desktop_snapshot()
    if operation == "mouse.move":
        pyautogui.moveTo(
            int(args["x"]),
            int(args["y"]),
            duration=float(args.get("duration") or 0),
        )
        return {"moved": True}
    if operation == "mouse.click":
        pyautogui.click(
            button=str(args.get("button") or "left"),
            clicks=int(args.get("clicks") or 1),
        )
        return {"clicked": True}
    if operation == "keyboard.type":
        pyautogui.write(
            str(args["text"]),
            interval=float(args.get("interval") or 0),
        )
        return {"typed": len(str(args["text"]))}
    raise ValueError(f"Unsupported operation: {operation}")


def ws_url(pairing_code: str) -> str:
    separator = "&" if "?" in PLUGIN_WS_URL else "?"
    return f"{PLUGIN_WS_URL}{separator}code={pairing_code}"


def on_message(ws: websocket.WebSocketApp, raw: str) -> None:
    try:
        message = json.loads(raw)
        request_id = message["id"]
        operation = message["operation"]
        args = message.get("args") or {}
        try:
            result = run_operation(operation, args)
            ws.send(json.dumps({"id": request_id, "ok": True, "result": result}))
        except Exception as exc:  # noqa: BLE001
            ws.send(json.dumps({"id": request_id, "ok": False, "error": str(exc)}))
    except Exception as exc:  # noqa: BLE001
        print(f"Invalid command: {exc}", flush=True)


def run() -> None:
    pairing_code = get_pairing_code()
    print("\nMCP Control Hub Companion", flush=True)
    print("=========================", flush=True)
    print(f"Pairing code: {pairing_code}", flush=True)
    print(f"Connecting to: {PLUGIN_WS_URL}", flush=True)
    print("Keep this window open while using the plugin.\n", flush=True)

    while True:
        try:
            app = websocket.WebSocketApp(
                ws_url(pairing_code),
                on_open=lambda _ws: print("Connected to MCP Control Hub Plugin.", flush=True),
                on_message=on_message,
                on_close=lambda _ws, code, reason: print(f"Disconnected ({code}): {reason}", flush=True),
                on_error=lambda _ws, error: print(f"WebSocket error: {error}", flush=True),
            )
            app.run_forever(ping_interval=20, ping_timeout=10)
        except KeyboardInterrupt:
            print("Stopping companion.", flush=True)
            return
        except Exception as exc:  # noqa: BLE001
            print(f"Connection failed: {exc}", flush=True)
        time.sleep(3)


if __name__ == "__main__":
    run()
