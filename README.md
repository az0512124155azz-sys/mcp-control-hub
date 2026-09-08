# MCP Control Hub

MCP Control Hub הוא אתר סטטי ומרכז התקנה לשני שרתי MCP מקומיים:

- Browser Dual-Control MCP — Chrome/Playwright עם ניווט, לחיצה, הקלדה, screenshots ו-Live Viewer מקומי.
- Computer Control MCP — Python/PyAutoGUI עם screenshot, עכבר ומקלדת.

האתר נמצא ב-`index.html` בשורש ולכן אפשר לפרוס אותו כאתר סטטי פשוט ב-Vercel או Netlify, בלי Next.js, בלי build ובלי Root Directory מיוחד.

## התקנה מקומית בלי נתיבים ידניים

הגרסה הזאת לא משתמשת יותר בנתיבי דוגמה כמו `C:\Users\you\...`.

המשתמש מוריד את `downloads/MCP-Control-Hub-Local.zip`, מחלץ אותו, ואז מריץ את המתקין של מערכת ההפעלה מתוך התיקייה שחולצה:

### Windows

```powershell
powershell -ExecutionPolicy Bypass -File .\INSTALL-WINDOWS.ps1
```

המתקין משתמש ב-`$PSScriptRoot`, ולכן הוא מזהה לבד את התיקייה שממנה הופעל. הוא מעתיק את השרתים למיקום קבוע:

```text
%LOCALAPPDATA%\MCP-Control-Hub
```

### macOS

```bash
chmod +x ./INSTALL-MACOS.sh
./INSTALL-MACOS.sh
```

### Linux

```bash
chmod +x ./INSTALL-LINUX.sh
./INSTALL-LINUX.sh
```

ב-macOS וב-Linux ההתקנה הקבועה נמצאת ב:

```text
~/.mcp-control-hub
```

## קובצי הגדרה

האתר מייצר קובצי JSON/TOML להורדה לפי AI + מערכת ההפעלה. הקבצים לא תלויים במיקום שאליו המשתמש חילץ את ZIP ההתקנה; הם מפעילים את השרתים מתוך מיקום ההתקנה הקבוע.

AI בטרמינל מקבל בכוונה רק את `computer-control` MCP.

## דרישות מקומיות

- Node.js 20+
- npm
- Python 3
- הרשאות Screen Recording / Accessibility לפי מערכת ההפעלה

## מבנה

```text
index.html
INSTALL-WINDOWS.ps1
INSTALL-MACOS.sh
INSTALL-LINUX.sh
downloads/
  MCP-Control-Hub-Local.zip
servers/
  browser-mcp/
  computer-mcp/
apps/web/index.html
```

`apps/web/index.html` נשאר כעותק תאימות לפרויקט Vercel ישן, אבל לפריסה חדשה עדיף להשתמש ב-`index.html` שבשורש.
