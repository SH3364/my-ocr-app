<?php
$db_file = 'config.json';
$data = json_decode(file_get_contents($db_file), true);

$apiUrl = "https://wirelessprovisioning.com/desktopmodules/telispire.webservices/mdnservices.asmx";
$user = $data['auth']['user'];
$pass = $data['auth']['pass'];
$targetPlan = $data['settings']['target_plan'];
$alertEmail = $data['settings']['alert_email'];

if (empty($user) || empty($pass)) { die("אנא הגדר שם משתמש וסיסמה ב-admin.php"); }

$alerts = [];

foreach ($data['sims'] as $sim) {
    $xmlRequest = '<?xml version="1.0" encoding="utf-8"?>
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
    curl_setopt($ch, CURLOPT_POSTFIELDS, $xmlRequest);
    curl_setopt($ch, CURLOPT_HTTPHEADER, [
        'Content-Type: text/xml; charset=utf-8',
        'SOAPAction: "urn:telispire:MdnServices/GetWirelessByICC"'
    ]);

    $response = curl_exec($ch);
    curl_close($ch);

    // ניתוח התשובה
    $cleanXml = str_ireplace(['soap:', 'soapenv:'], '', $response);
    $xml = simplexml_load_string($cleanXml);
    $res = $xml->Body->GetWirelessByICCResponse->GetWirelessByICCResult;

    $status = (string)$res->Status; // Available, Active וכו'
    $plan = (string)$res->RatePlan;

    // לוגיקת התראה: אם לא פנוי (Available) וגם החבילה לא תואמת ליעד
    if ($status !== "Available" && $plan !== $targetPlan) {
        $alerts[] = "חנות: {$sim['shop']} | ICCID: {$sim['iccid']} | סטטוס: $status | חבילה שנמצאה: $plan";
    }
}

// שליחת מייל אם נמצאו חריגות
if (!empty($alerts)) {
    $subject = "התראה: נמצאו חבילות סים שגויות - " . date("d/m/Y");
    $message = "להלן רשימת הסימים שלא תואמים לחבילה $targetPlan:\n\n" . implode("\n", $alerts);
    $headers = "From: SIM-Monitor@yourdomain.com\r\nContent-Type: text/plain; charset=UTF-8";
    
    if (!empty($alertEmail)) {
        mail($alertEmail, $subject, $message, $headers);
        echo "נמצאו תקלות ומייל נשלח ל-$alertEmail.";
    }
} else {
    echo "הבדיקה הסתיימה: הכל תקין!";
}
