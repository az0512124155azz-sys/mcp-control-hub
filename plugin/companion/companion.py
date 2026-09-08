from __future__ import annotations

import base64
import io
import json
import os
import secrets
import subprocess
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
        if self._page:
            try:
                if not self._page.is_closed():
                    # Touch the browser connection so a closed context is not
                    # mistaken for a usable page.
                    self._page.title()
                    return self._page
            except Exception:  # noqa: BLE001
                self._page = None
                self._context = None
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

    @staticmethod
    def page_state(page: Page, **extra: Any) -> dict[str, Any]:
        png = page.screenshot(type="png")
        return {
            **extra,
            "base64": base64.b64encode(png).decode("ascii"),
            "width": page.viewport_size["width"] if page.viewport_size else None,
            "height": page.viewport_size["height"] if page.viewport_size else None,
            "url": page.url,
            "title": page.title(),
        }

    def open(self) -> dict[str, Any]:
        page = self.ensure()
        return self.page_state(page)

    def navigate(self, url: str) -> dict[str, Any]:
        page = self.ensure()
        page.goto(url, wait_until="domcontentloaded", timeout=30000)
        return self.page_state(page)

    def click(self, x: float, y: float) -> dict[str, Any]:
        page = self.ensure()
        page.mouse.click(x, y)
        page.wait_for_timeout(350)
        return self.page_state(page, clicked=True, x=x, y=y)

    def click_text(self, text: str) -> dict[str, Any]:
        page = self.ensure()
        target = page.get_by_text(text, exact=False).first
        target.click(timeout=10000)
        page.wait_for_timeout(350)
        return self.page_state(page, clicked_text=text)

    def type_text(self, text: str) -> dict[str, Any]:
        page = self.ensure()
        page.keyboard.insert_text(text)
        page.wait_for_timeout(250)
        return self.page_state(page, typed=len(text))

    def fill(self, text: str, target: str) -> dict[str, Any]:
        page = self.ensure()
        candidates = [
            page.get_by_label(target, exact=False),
            page.get_by_placeholder(target, exact=False),
            page.get_by_role("textbox", name=target, exact=False),
        ]
        for candidate in candidates:
            try:
                if candidate.count() and candidate.first.is_visible():
                    candidate.first.fill(text, timeout=10000)
                    page.wait_for_timeout(250)
                    return self.page_state(page, filled=target, typed=len(text))
            except Exception:  # noqa: BLE001
                continue
        raise ValueError(f'No visible text field matched "{target}".')

    def press(self, key: str) -> dict[str, Any]:
        page = self.ensure()
        page.keyboard.press(key)
        page.wait_for_timeout(350)
        return self.page_state(page, pressed=key)

    def snapshot(self) -> dict[str, Any]:
        page = self.ensure()
        elements = page.locator(
            "a, button, input, textarea, select, [role=button], [role=link], [role=textbox]"
        ).evaluate_all(
            """els => els.filter(el => {
              const r = el.getBoundingClientRect();
              const s = getComputedStyle(el);
              return r.width > 0 && r.height > 0 && s.visibility !== 'hidden' && s.display !== 'none';
            }).slice(0, 80).map((el, index) => ({
              index,
              tag: el.tagName.toLowerCase(),
              role: el.getAttribute('role') || '',
              text: (el.innerText || el.value || '').trim().slice(0, 120),
              label: el.getAttribute('aria-label') || '',
              placeholder: el.getAttribute('placeholder') || '',
              type: el.getAttribute('type') || ''
            }))"""
        )
        return self.page_state(page, elements=elements)


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
    if operation == "browser.click_text":
        return browser.click_text(str(args["text"]))
    if operation == "browser.type":
        return browser.type_text(str(args["text"]))
    if operation == "browser.fill":
        return browser.fill(str(args["text"]), str(args["target"]))
    if operation == "browser.press":
        return browser.press(str(args["key"]))
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
        if args.get("x") is not None and args.get("y") is not None:
            pyautogui.moveTo(int(args["x"]), int(args["y"]), duration=0.2)
        pyautogui.click(
            button=str(args.get("button") or "left"),
            clicks=int(args.get("clicks") or 1),
        )
        time.sleep(0.35)
        return {**desktop_snapshot(), "clicked": True}
    if operation == "keyboard.type":
        text = str(args["text"])
        subprocess.run(
            ["powershell", "-NoProfile", "-Command", "Set-Clipboard -Value ([Console]::In.ReadToEnd())"],
            input=text,
            text=True,
            check=True,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        pyautogui.hotkey("ctrl", "v")
        if args.get("press_enter"):
            pyautogui.press("enter")
        time.sleep(0.35)
        return {**desktop_snapshot(), "typed": len(text)}
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
