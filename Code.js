/**
 * Google Apps Script - SIM Management System (SOAP API)
 * GitHub Version
 */

const SOAP_URL = "https://wirelessprovisioning.com/desktopmodules/telispire.webservices/mdnservices.asmx";
const TARGET_PLAN = "Prepaid Refills - Talk Only - 4G HD";
const FOLDER_NAME = "SIM_Reports_Archive";

// רשימת הסימים והחנויות - ניתן לעדכן כאן ידנית
const SIM_DATABASE = [
  { mdn: "1234567890", store: "חנות א" },
  { mdn: "0987654321", store: "חנות ב" }
];

/**
 * מציג את דף הבית של ה-Web App
 */
function doGet() {
  return HtmlService.createTemplateFromFile('Index')
    .evaluate()
    .setTitle('מערכת ניהול סימים')
    .setXFrameOptionsMode(HtmlService.XFrameOptionsMode.ALLOWALL)
    .addMetaTag('viewport', 'width=device-width, initial-scale=1');
}

/**
 * בדיקת סים בודד מול ה-API
 */
function checkSpecificSim(mdn) {
  const credentials = getStoredCredentials();
  if (!credentials.username || !credentials.password) return "שגיאה: חסר שם משתמש או סיסמה";
  
  try {
    const result = callSoapApi(mdn, credentials);
    const isOk = (result.status === "Available" || result.ratePlan === TARGET_PLAN);
    return {
      status: result.status,
      plan: result.ratePlan,
      success: isOk
    };
  } catch (e) {
    return "שגיאה טכנית: " + e.message;
  }
}

/**
 * בדיקה יומית לכל רשימת הסימים
 */
function dailySimCheck() {
  const credentials = getStoredCredentials();
  if (!credentials.username) return "נא להגדיר הרשאות באתר";

  let reportData = [["Timestamp", "MDN", "Store", "Status", "Plan", "Result"]];
  let failedSims = [];

  SIM_DATABASE.forEach(item => {
    Utilities.sleep(700); // השהייה קלה למניעת חסימה
    try {
      const result = callSoapApi(item.mdn, credentials);
      const isOk = (result.status === "Available" || result.ratePlan === TARGET_PLAN);
      
      reportData.push([new Date().toISOString(), item.mdn, item.store, result.status, result.ratePlan, isOk ? "PASS" : "FAIL"]);
      if (!isOk) failedSims.push({ mdn: item.mdn, store: item.store, plan: result.ratePlan });
    } catch (e) {
      reportData.push([new Date().toISOString(), item.mdn, item.store, "ERROR", e.message, "FAIL"]);
    }
  });

  saveReportToDrive(reportData);
  if (failedSims.length > 0) sendAlertEmail(failedSims);
  
  return "הבדיקה הסתיימה. " + failedSims.length + " שגיאות נמצאו.";
}

/**
 * ביצוע קריאת SOAP XML
 */
function callSoapApi(mdn, creds) {
  const xmlPayload = 
    '<?xml version="1.0" encoding="utf-8"?>' +
    '<soap:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">' +
      '<soap:Body>' +
        '<GetIVRLineInformation xmlns="urn:telispire:MdnServices">' +
          '<username>' + creds.username + '</username>' +
          '<password>' + creds.password + '</password>' +
          '<mdn>' + mdn + '</mdn>' +
        '</GetIVRLineInformation>' +
      '</soap:Body>' +
    '</soap:Envelope>';

  const options = {
    method: "post",
    contentType: "text/xml; charset=utf-8",
    headers: { "SOAPAction": "urn:telispire:MdnServices/GetIVRLineInformation" },
    payload: xmlPayload,
    muteHttpExceptions: true
  };

  const response = UrlFetchApp.fetch(SOAP_URL, options);
  const xml = response.getContentText();
  
  return {
    ratePlan: extractTag(xml, "RatePlan"),
    status: extractTag(xml, "Status")
  };
}

function extractTag(xml, tag) {
  const regex = new RegExp('<' + tag + '>(.*?)<\/' + tag + '>', 'i');
  const match = xml.match(regex);
  return match ? match[1] : "N/A";
}

function saveReportToDrive(data) {
  const csv = data.map(row => row.join(",")).join("\n");
  const name = "Report_" + Utilities.formatDate(new Date(), "GMT", "yyyy-MM-dd") + ".csv";
  const folders = DriveApp.getFoldersByName(FOLDER_NAME);
  const folder = folders.hasNext() ? folders.next() : DriveApp.createFolder(FOLDER_NAME);
  folder.createFile(name, csv, MimeType.CSV);
}

function sendAlertEmail(list) {
  let msg = "Sim Check Alert:\n\n" + list.map(s => s.store + " (" + s.mdn + "): " + s.plan).join("\n");
  MailApp.sendEmail(Session.getActiveUser().getEmail(), "SIM Status Alert", msg);
}

// ניהול הגדרות
function saveCredentials(u, p) { PropertiesService.getUserProperties().setProperty('creds', JSON.stringify({username:u, password:p})); }
function getStoredCredentials() { return JSON.parse(PropertiesService.getUserProperties().getProperty('creds') || '{}'); }
function getLastReportUrl() {
  const folders = DriveApp.getFoldersByName(FOLDER_NAME);
  if (!folders.hasNext()) return null;
  const files = folders.next().getFiles();
  let latest = null;
  while (files.hasNext()) {
    let f = files.next();
    if (!latest || f.getDateCreated() > latest.getDateCreated()) latest = f;
  }
  return latest ? latest.getDownloadUrl().replace("?e=download", "") : null;
}
