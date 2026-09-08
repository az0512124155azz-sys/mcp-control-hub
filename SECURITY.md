# Security model

Both MCP servers are designed to run locally on the user's computer.

## Browser MCP

- MCP transport is `stdio`; there is no public MCP port.
- The optional live viewer binds to `127.0.0.1` only.
- Every viewer session receives a random token. WebSocket connections without that token are rejected.
- Chrome starts in an isolated profile by default (`~/.mcp-browser-profile`) rather than reusing your everyday browser profile.

## Computer Control MCP

- MCP transport is `stdio`; there is no network listener.
- Screenshots require `MCP_COMPUTER_ALLOW_SCREENSHOTS=1`.
- Mouse and keyboard actions require `MCP_COMPUTER_ALLOW_ACTIONS=1`.
- PyAutoGUI's corner fail-safe remains enabled: rapidly move the pointer to the top-left corner to abort an action sequence.
- Keep your MCP host's approval prompts enabled unless you fully trust the model and the current task.

Never expose these local-control servers directly to the public Internet without adding authentication, authorization, audit logs, rate limits, and a strict permission model.
