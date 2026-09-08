# MCP Control Hub

MCP Control Hub הוא אתר סטטי ומרכז התקנה לשני שרתי MCP מקומיים:

- **Browser Dual-Control MCP** — Chrome/Playwright עם ניווט, לחיצה, הקלדה, screenshots ו-Live Viewer מקומי.
- **Computer Control MCP** — Python/PyAutoGUI עם screenshot, עכבר ומקלדת.

האתר נמצא ב-`index.html` בשורש ולכן אפשר לפרוס אותו כאתר סטטי פשוט ב-Vercel או Netlify, בלי Next.js, בלי build ובלי Root Directory מיוחד.

## התקנה מקומית

האתר מזהה אוטומטית Windows, macOS או Linux ומציג רק את חבילת ההתקנה של המערכת שזוהתה. אפשר ללחוץ **שנה מערכת** אם הזיהוי אינו נכון.

חבילות ההתקנה נפרדות:

- `downloads/MCP-Control-Hub-Windows.zip`
- `downloads/MCP-Control-Hub-macOS.zip`
- `downloads/MCP-Control-Hub-Linux.zip`

### Windows

1. הורד וחלץ את `MCP-Control-Hub-Windows.zip`.
2. לחץ פעמיים על `INSTALL-WINDOWS.bat`.
3. חלופה ידנית בלבד:

```powershell
powershell -ExecutionPolicy Bypass -File ".\INSTALL-WINDOWS.ps1"
```

אין צורך ב-`cd`, אין צורך להעתיק prompt של PowerShell, ואין נתיב שצריך לשנות. המתקין משתמש ב-`$PSScriptRoot` ומתקין ל:

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

## תיקון Browser MCP

ה-Playwright launch options משתמשים כעת במערך `string[]` רגיל עבור `args` ולא ב-readonly tuple. זה מתקן את שגיאת TypeScript שבה `readonly ["--disable-infobars"]` לא היה ניתן להעברה ל-`launchPersistentContext`.

## קובצי הגדרה

האתר מייצר קובצי JSON/TOML להורדה לפי AI + מערכת ההפעלה. הקבצים מפעילים את השרתים מתוך מיקום ההתקנה הקבוע.

AI בטרמינל מקבל בכוונה רק את `computer-control` MCP.

## דרישות מקומיות

- Node.js 20+
- npm
- Python 3
- הרשאות Screen Recording / Accessibility לפי מערכת ההפעלה

## מבנה

```text
index.html
INSTALL-WINDOWS.bat
INSTALL-WINDOWS.ps1
INSTALL-MACOS.sh
INSTALL-LINUX.sh
downloads/
  MCP-Control-Hub-Windows.zip
  MCP-Control-Hub-macOS.zip
  MCP-Control-Hub-Linux.zip
servers/
  browser-mcp/
  computer-mcp/
apps/web/index.html
```

`apps/web/index.html` נשאר כעותק תאימות לפרויקט Vercel ישן. לפריסה חדשה עדיף להשתמש ב-`index.html` שבשורש.

## Pairing code

After installation, MCP Control Hub generates one stable 8-character pairing code for the computer. Enter that code on the website before downloading an AI configuration. The generated config passes it as `MCP_PAIRING_CODE`; both local MCP servers compare it with the locally stored code and refuse to start if it does not match.

- Windows: `%LOCALAPPDATA%\MCP-Control-Hub\SHOW-PAIRING-CODE.bat`
- macOS/Linux: `~/.mcp-control-hub/SHOW-PAIRING-CODE.sh`

