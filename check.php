<?php
// טעינת הנתונים שהאתר שמר
$data = json_decode(file_get_contents('data.json'), true);
$api_user = $data['user'];
$api_pass = $data['pass'];
$lines = explode("\n", $data['sims']);

$failed_report = [];

foreach ($lines as $line) {
    if (trim($line) == "") continue;
    $parts = explode(",", $line);
    $iccid = trim($parts[0]);
    $store = isset($parts[1]) ? trim($parts[1]) : "Unknown";

    // קריאת ה-API
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

    // לוגיקה: אם יש קו (MDN קיים) אבל החבילה לא תואמת
    if (strpos($response, '<MDN>') !== false) {
        if (strpos($response, 'Prepaid Refills - Talk Only - 4G HD') === false) {
            $failed_report[] = "- סים: $iccid (חנות: $store): חבילה לא תקינה או מופעל בחברה אחרת.";
        }
    }
}

if (!empty($failed_report)) {
    $msg = "נמצאו סימים הדורשים טיפול:\n\n" . implode("\n", $failed_report);
    file_put_contents('report.txt', $msg);
    echo "FAIL";
} else {
    echo "SUCCESS";
}
