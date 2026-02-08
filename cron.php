<?php
// קריאת רשימת הסימים מהקובץ
$sims = json_decode(file_get_contents('sims.json'), true);
$api_user = getenv('API_USER');
$api_pass = getenv('API_PASS');
$to_email = getenv('ADMIN_EMAIL');

$errors = [];
$target_plan = "Prepaid Refills - Talk Only - 4G HD";

foreach ($sims as $sim) {
    $iccid = $sim['iccid'];
    
    // פנייה ל-API
    $url = "https://wirelessprovisioning.com/desktopmodules/telispire.webservices/mdnservices.asmx";
    $xml = "<?xml version='1.0' encoding='utf-8'?>
    <soap:Envelope xmlns:xsi='http://www.w3.org/2001/XMLSchema-instance' xmlns:xsd='http://www.w3.org/2001/XMLSchema' xmlns:soap='http://schemas.xmlsoap.org/soap/envelope/'>
      <soap:Body>
        <GetWirelessByICC xmlns='urn:telispire:MdnServices'>
          <ICC>$iccid</ICC>
          <Username>$api_user</Username>
          <Password>$api_pass</Password>
        </GetWirelessByICC>
      </soap:Body>
    </soap:Envelope>";

    $ch = curl_init($url);
    curl_setopt($ch, CURLOPT_HTTPHEADER, ['Content-Type: text/xml', 'SOAPAction: "urn:telispire:MdnServices/GetWirelessByICC"']);
    curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
    curl_setopt($ch, CURLOPT_POST, true);
    curl_setopt($ch, CURLOPT_POSTFIELDS, $xml);
    $response = curl_exec($ch);
    curl_close($ch);

    $xml_res = simplexml_load_string(str_ireplace(['soap:', 'xmlns:'], '', $response));
    
    // שליפת הנתונים (יש לוודא נתיב מדויק לפי ה-Response שקיבלת)
    $res_path = $xml_res->Body->GetWirelessByICCResponse->GetWirelessByICCResult;
    $status = (string)$res_path->Status; 
    $plan = (string)$res_path->PlanName;

    // בדיקת התנאים
    if ($status == "Active" && $plan != $target_plan) {
        $errors[] = "ICCID: $iccid | Shop: {$sim['shop_name']} | Current Plan: $plan";
    }
}

// שליחת מייל במידה ויש שגיאות
if (!empty($errors)) {
    $subject = "SIM Alerts - Action Required";
    $body = "The following SIMs have incorrect plans:\n\n" . implode("\n", $errors);
    
    // ב-GitHub Actions שליחת מייל פשוט דרך PHP לעיתים נחסמת, 
    // מומלץ להשתמש ב-Action ייעודי לשליחת מייל או ב-API כמו SendGrid.
    // כרגע נשתמש בפונקציית המייל הבסיסית:
    mail($to_email, $subject, $body);
    echo "Errors found and email sent.";
} else {
    echo "Everything is perfect!";
}
