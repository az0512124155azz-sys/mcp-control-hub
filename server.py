"""Computer Control MCP.

This server intentionally uses stdio and exposes no network listener. The AI
host launches the process locally, then calls tools that wrap PyAutoGUI.

Safety defaults:
- screenshots are blocked unless MCP_COMPUTER_ALLOW_SCREENSHOTS=1
- mouse/keyboard actions are blocked unless MCP_COMPUTER_ALLOW_ACTIONS=1
- PyAutoGUI FAILSAFE stays enabled; moving the pointer to the top-left corner
  aborts PyAutoGUI activity.
"""

from __future__ import annotations

import io
import os
import platform
from typing import Literal

import pyautogui
import pyperclip
from mcp.server import MCPServer
from mcp.server.mcpserver import Image


mcp = MCPServer("Computer Control MCP")

# Keep the human emergency stop. Do not disable this in production.
pyautogui.FAILSAFE = True
pyautogui.PAUSE = float(os.getenv("MCP_COMPUTER_ACTION_PAUSE", "0.05"))


def _flag(name: str) -> bool:
    return os.getenv(name, "0").strip().lower() in {"1", "true", "yes", "on"}


def _require_screenshots() -> None:
    if not _flag("MCP_COMPUTER_ALLOW_SCREENSHOTS"):
        raise PermissionError(
            "Screen capture is disabled. Set MCP_COMPUTER_ALLOW_SCREENSHOTS=1 "
            "in the MCP host configuration and restart the server."
        )


def _require_actions() -> None:
    if not _flag("MCP_COMPUTER_ALLOW_ACTIONS"):
        raise PermissionError(
            "Mouse/keyboard control is disabled. Set MCP_COMPUTER_ALLOW_ACTIONS=1 "
            "in the MCP host configuration and restart the server."
        )


def _validate_point(x: int, y: int) -> tuple[int, int]:
    width, height = pyautogui.size()
    if not (0 <= x < width and 0 <= y < height):
        raise ValueError(f"Point ({x}, {y}) is outside the primary screen {width}x{height}.")
    return x, y


@mcp.tool()
def computer_status() -> dict:
    """Return OS, screen size, pointer position and permission-gate status."""
    width, height = pyautogui.size()
    x, y = pyautogui.position()
    return {
        "platform": platform.system(),
        "platform_release": platform.release(),
        "primary_screen": {"width": width, "height": height},
        "pointer": {"x": x, "y": y},
        "screenshots_enabled": _flag("MCP_COMPUTER_ALLOW_SCREENSHOTS"),
        "actions_enabled": _flag("MCP_COMPUTER_ALLOW_ACTIONS"),
        "failsafe": True,
        "failsafe_hint": "Move the pointer rapidly to the top-left corner to trigger PyAutoGUI FailSafeException.",
    }


@mcp.tool()
def computer_screenshot() -> Image:
    """Capture the primary screen and return it as an MCP image block."""
    _require_screenshots()
    shot = pyautogui.screenshot()
    buffer = io.BytesIO()
    shot.save(buffer, format="PNG", optimize=True)
    return Image(data=buffer.getvalue(), format="png")


@mcp.tool()
def computer_move_mouse(x: int, y: int, duration: float = 0.2) -> dict:
    """Move the pointer to an absolute coordinate on the primary screen."""
    _require_actions()
    x, y = _validate_point(x, y)
    pyautogui.moveTo(x, y, duration=max(0.0, min(duration, 5.0)))
    return {"x": x, "y": y}


@mcp.tool()
def computer_click(
    x: int | None = None,
    y: int | None = None,
    button: Literal["left", "right", "middle"] = "left",
    clicks: int = 1,
    interval: float = 0.08,
) -> dict:
    """Click at an optional coordinate, or click at the current pointer position."""
    _require_actions()
    if (x is None) != (y is None):
        raise ValueError("Provide both x and y, or neither.")
    if x is not None and y is not None:
        _validate_point(x, y)
    pyautogui.click(
        x=x,
        y=y,
        clicks=max(1, min(clicks, 5)),
        interval=max(0.0, min(interval, 1.0)),
        button=button,
    )
    px, py = pyautogui.position()
    return {"clicked": True, "x": px, "y": py, "button": button, "clicks": clicks}


@mcp.tool()
def computer_drag_mouse(
    x: int,
    y: int,
    duration: float = 0.5,
    button: Literal["left", "right", "middle"] = "left",
) -> dict:
    """Drag the pointer from its current location to an absolute coordinate."""
    _require_actions()
    x, y = _validate_point(x, y)
    pyautogui.dragTo(x, y, duration=max(0.0, min(duration, 8.0)), button=button)
    return {"x": x, "y": y, "button": button}


@mcp.tool()
def computer_type_text(text: str, interval: float = 0.01, use_clipboard: bool = True) -> dict:
    """Type text into the focused app. Clipboard mode supports Unicode such as Hebrew."""
    _require_actions()
    interval = max(0.0, min(interval, 1.0))

    if use_clipboard:
        # PyAutoGUI's key-by-key writer is ASCII-oriented. Pasting from the OS
        # clipboard works much better for Unicode text and non-English scripts.
        previous = None
        try:
            previous = pyperclip.paste()
        except Exception:
            previous = None

        pyperclip.copy(text)
        if platform.system() == "Darwin":
            pyautogui.hotkey("command", "v")
        else:
            pyautogui.hotkey("ctrl", "v")

        # Restore the user's clipboard when possible.
        if previous is not None:
            try:
                pyperclip.copy(previous)
            except Exception:
                pass
    else:
        pyautogui.write(text, interval=interval)

    return {"typed_characters": len(text), "method": "clipboard" if use_clipboard else "key-by-key"}


@mcp.tool()
def computer_press_key(key: str, presses: int = 1, interval: float = 0.08) -> dict:
    """Press a named key such as enter, tab, esc, f5 or left."""
    _require_actions()
    pyautogui.press(key, presses=max(1, min(presses, 20)), interval=max(0.0, min(interval, 1.0)))
    return {"key": key, "presses": presses}


@mcp.tool()
def computer_hotkey(keys: list[str]) -> dict:
    """Press a key combination, for example [\"ctrl\", \"shift\", \"p\"]."""
    _require_actions()
    if not keys or len(keys) > 6:
        raise ValueError("Provide between 1 and 6 keys.")
    pyautogui.hotkey(*keys)
    return {"hotkey": keys}


@mcp.tool()
def computer_scroll(clicks: int, x: int | None = None, y: int | None = None) -> dict:
    """Scroll vertically. Positive values scroll up; negative values scroll down."""
    _require_actions()
    if (x is None) != (y is None):
        raise ValueError("Provide both x and y, or neither.")
    if x is not None and y is not None:
        _validate_point(x, y)
        pyautogui.moveTo(x, y, duration=0.1)
    pyautogui.scroll(max(-100, min(clicks, 100)))
    return {"scrolled": max(-100, min(clicks, 100))}


def main() -> None:
    """Console-script entrypoint."""
    mcp.run()


if __name__ == "__main__":
    main()
