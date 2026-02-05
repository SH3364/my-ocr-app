<?php
// קריאת רשימת הסימים
$data = json_decode(file_get_contents('sims.json'), true);
$apiUrl = "https://wirelessprovisioning.com/desktopmodules/telispire.webservices/mdnservices.asmx";

// קבלת פרטי התחברות מהסביבה (GitHub Secrets)
$user = getenv('TELISPIRE_USER');
$pass = getenv('TELISPIRE_PASS');
$targetPlan = "Prepaid Refills - Talk Only - 4G HD";

$alerts = [];

foreach ($data['sims'] as $sim) {
    $xmlPost = '<?xml version="1.0" encoding="utf-8"?>
    <soap:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
      <soap:Body>
        <GetWirelessByICC xmlns="urn:telispire:MdnServices">
          <username>'.$user.'</username>
          <password>'.$pass.'</password>
          <ICCID>'.$sim['iccid'].'</ICCID>
        </GetWirelessByICC>
      </soap:Body>
    </soap:Envelope>';

    $ch = curl_init($apiUrl);
    curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
    curl_setopt($ch, CURLOPT_POST, true);
    curl_setopt($ch, CURLOPT_POSTFIELDS, $xmlPost);
    curl_setopt($ch, CURLOPT_HTTPHEADER, [
        'Content-Type: text/xml; charset=utf-8',
        'SOAPAction: "urn:telispire:MdnServices/GetWirelessByICC"'
    ]);

    $response = curl_exec($ch);
    curl_close($ch);

    // ניתוח ה-XML שמתקבל לפי התיעוד שסיפקת
    $cleanXml = str_ireplace(['soap:', 'soapenv:'], '', $response);
    $xml = simplexml_load_string($cleanXml);
    $res = $xml->Body->GetWirelessByICCResponse->GetWirelessByICCResult;

    $status = (string)$res->Status; // מתוך התיעוד שסיפקת
    $plan = (string)$res->RatePlan; // מתוך התיעוד שסיפקת

    // בדיקה: אם לא פנוי (Available) והחבילה לא תואמת - התראה
    if ($status !== "Available" && $plan !== $targetPlan) {
        $alerts[] = "תקלה בחנות: {$sim['shop']} | ICCID: {$sim['iccid']} | נמצאה חבילה: $plan (צריך להיות: $targetPlan)";
    }
}

// הדפסת תוצאות (יופיע בלוג של GitHub)
if (!empty($alerts)) {
    echo "ALERT_FOUND\n";
    echo implode("\n", $alerts);
    // GitHub Actions יטפל בשליחת המייל בשלב הבא
} else {
    echo "All SIMs are correct.";
}
