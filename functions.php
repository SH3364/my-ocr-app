<?php
// יצירת חיבור למסד הנתונים
$db = new PDO('sqlite:database.db');
$db->exec("CREATE TABLE IF NOT EXISTS sims (id INTEGER PRIMARY KEY, iccid TEXT, shop_name TEXT)");
$db->exec("CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT)");

// פונקציה לשליפת הגדרות (שם משתמש/סיסמה)
function getSetting($key) {
    global $db;
    $stmt = $db->prepare("SELECT value FROM settings WHERE key = ?");
    $stmt->execute([$key]);
    return $stmt->fetchColumn();
}

// פונקציית ה-API המרכזית
function checkSimDetails($iccid) {
    $username = getSetting('api_user');
    $password = getSetting('api_pass');
    
    $url = "https://wirelessprovisioning.com/desktopmodules/telispire.webservices/mdnservices.asmx";
    
    $xml = '<?xml version="1.0" encoding="utf-8"?>
    <soap:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
      <soap:Body>
        <GetWirelessByICC xmlns="urn:telispire:MdnServices">
          <ICC>'.$iccid.'</ICC>
          <Username>'.$username.'</Username>
          <Password>'.$password.'</Password>
        </GetWirelessByICC>
      </soap:Body>
    </soap:Envelope>';

    $ch = curl_init($url);
    curl_setopt($ch, CURLOPT_HTTPHEADER, ['Content-Type: text/xml', 'SOAPAction: "urn:telispire:MdnServices/GetWirelessByICC"']);
    curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
    curl_setopt($ch, CURLOPT_POST, true);
    curl_setopt($ch, CURLOPT_POSTFIELDS, $xml);
    
    $response = curl_exec($ch);
    curl_close($ch);

    // עיבוד התוצאה
    $clean_xml = str_ireplace(['soap:', 'xmlns:'], '', $response);
    return simplexml_load_string($clean_xml);
}
?>
