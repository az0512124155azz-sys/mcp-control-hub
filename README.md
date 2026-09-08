# MCP Control Hub — Static Edition

הגרסה הזו בנויה בכוונה בלי Next.js, בלי npm לאתר, בלי build ובלי framework.

## פריסה

הקובץ `index.html` נמצא בשורש המאגר ולכן אפשר לפרוס את המאגר ישירות ב-Vercel, Netlify, GitHub Pages או כל אחסון סטטי.

- Build command: **ריק**
- Output/Publish directory: **`.`** או ברירת מחדל
- Root directory: **שורש המאגר**

לנוחות, יש גם עותק זהה ב-`apps/web/index.html`, כך שגם פרויקט Vercel ישן שנשאר מוגדר עם `apps/web` עדיין ימצא אתר תקין.

## שרתי MCP

קוד השרתים נשאר תחת `servers/` ואינו נדרש לבניית האתר.

## AI clients supported by the guide

The static guide now includes setup flows for GPT / ChatGPT, Codex Desktop / IDE, Claude Desktop, Cursor, VS Code, Windsurf, Cline, and a generic Terminal AI mode.

**Terminal AI restriction:** terminal-based agents such as Codex CLI, Claude Code, Gemini CLI, or OpenCode are intentionally given only the `computer-control` MCP server. The `browser-dual-control` MCP server is not included in Terminal AI configuration examples.

For ChatGPT, the guide clearly explains that ChatGPT does not connect directly to a local stdio MCP server; a supported remote MCP connection or Secure MCP Tunnel is required.
