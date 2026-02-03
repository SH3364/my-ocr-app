# SIM Management System (SOAP API)

מערכת מבוססת Google Apps Script לניהול ובדיקת סטטוס סימים דרך Wireless Provisioning API.

## תכונות
- בדיקת סטטוס סים (MDN) וזיהוי תוכנית.
- הפעלה אוטומטית יומית.
- שמירת דוחות ב-Google Drive בפורמט CSV.
- ממשק Web App פשוט לניהול והורדת דוחות.

## הוראות התקנה
1. צור פרויקט חדש ב-[Google Apps Script](https://script.google.com).
2. העתק את תוכן `Code.js` לקובץ הקוד.
3. צור קובץ HTML בשם `Index` והעתק אליו את תוכן `Index.html`.
4. בצע פריסה (Deploy) כ-Web App.
5. הגדר Trigger ידני לפונקציה `dailySimCheck` לריצה יומית.

## הגדרות
יש לעדכן את המשתנה `SIM_DATABASE` בתוך `Code.js` עם רשימת הסימים שלך.
