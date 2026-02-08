<?php
// קריאת הנתונים שהזנת באתר
$config = json_decode(file_get_contents('config.json'), true);
$api_user = $config['user'];
$api_pass = $config['pass'];
$sims = $config['sims'];

$failed_report = [];

foreach ($sims as $sim) {
    $iccid = $sim['iccid'];
    $store = $sim['store'];

    $xml = '<?xml version="1.0" encoding="utf-8"?>
    <soap:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
      <soap:Body>
        <GetWirelessByICC xmlns="urn:telispire:MdnServices">
          <userName>'.$api_user.'</userName>
          <password>'.$api_pass.'</password>
          <ICCID>'.$iccid.'</ICCID>
        </GetWirelessByICC>
      </soap:Body>
    </soap:Envelope>';

    $ch = curl_init('https://wirelessprovisioning.com/desktopmodules/telispire.webservices/mdnservices.asmx');
    curl_setopt($ch, CURLOPT_HTTPHEADER, ['Content-Type: text/xml', 'SOAPAction: "urn:telispire:MdnServices/GetWirelessByICC"']);
    curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
    curl_setopt($ch, CURLOPT_POST, true);
    curl_setopt($ch, CURLOPT_POSTFIELDS, $xml);
    
    $response = curl_exec($ch);
    curl_close($ch);

    // בדיקה: האם הסים פעיל עם החבילה הספציפית
    if (strpos($response, 'Prepaid Refills - Talk Only - 4G HD') === false) {
        $failed_report[] = "חנות: $store | מספר סים: $iccid (חבילה לא תקינה או חברה אחרת)";
    }
}

// יצירת קובץ דוח יומי
$report_content = "דוח בדיקה לתאריך: " . date('Y-m-d H:i') . "\n";
$report_content .= empty($failed_report) ? "הכל תקין!" : implode("\n", $failed_report);
file_put_contents('daily_report.txt', $report_content);

// אם יש תקלות - נדפיס אותן כדי ש-GitHub Action יוכל לשלוח מייל
if (!empty($failed_report)) {
    echo "FAILED_SIMS_FOUND\n";
    echo $report_content;
}
