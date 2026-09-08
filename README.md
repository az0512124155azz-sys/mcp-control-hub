# MCP Control Hub — Static Edition

האתר בנוי כאתר סטטי פשוט: `index.html` בשורש, בלי Next.js, בלי build ובלי framework.

## פריסה

אפשר לפרוס את המאגר ישירות ב-Vercel, Netlify, GitHub Pages או כל אחסון סטטי.

- Build command: **ריק**
- Output/Publish directory: **`.`** או ברירת מחדל
- Root directory: **שורש המאגר**

יש גם עותק זהה ב-`apps/web/index.html` כדי שפרויקט Vercel ישן שמוגדר על `apps/web` ימשיך לעבוד.

## מדריך התקנה אינטראקטיבי

המדריך תומך ב-**Windows, macOS ו-Linux**. בחירת מערכת ההפעלה משנה את נתיב הפרויקט, פקודות ההתקנה, נתיב קובץ ההגדרה והוראות ההרשאות כך שיוצגו רק ההוראות הרלוונטיות למערכת שנבחרה.

הלקוחות במדריך: GPT / ChatGPT, Codex Desktop / IDE, Claude Desktop, Cursor, VS Code, Windsurf, Cline ו-AI בטרמינל.

במקום לדרוש מהמשתמש ליצור קובץ JSON/TOML ידנית, האתר מייצר אותו לפי ה-AI + מערכת ההפעלה + נתיב הפרויקט ומאפשר **להוריד את הקובץ המוכן** בלחיצה אחת. תצוגת הקוד וכפתור ההעתקה נשארו כאפשרות נוספת.

**Terminal AI restriction:** כל AI שרץ במצב Terminal מקבל בכוונה רק את `computer-control` MCP. ה-`browser-dual-control` אינו נכלל בקובץ שמיוצר למצב הזה.

## שרתי MCP

קוד השרתים נשאר תחת `servers/` ואינו נדרש לבניית האתר:

- `servers/browser-mcp` — Chrome / Browser Dual-Control MCP
- `servers/computer-mcp` — Computer Control MCP

## הערת ChatGPT

ChatGPT אינו משתמש ישירות בקובץ stdio מקומי כמו Clients מקומיים. לכן כפתור ההורדה עבור ChatGPT מוריד קובץ הוראות מוכן לחיבור דרך MCP מרוחק / Tunnel תואם, בעוד שאר הלקוחות מורידים את קובץ ההגדרה שלהם.
