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
