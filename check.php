<?php
// טעינת הנתונים מקובץ הנתונים
$data = json_decode(file_get_contents('data.json'), true);
$api_user = $data['user'];
$api_pass = $data['pass'];
$sim_list = explode("\n", $data['sims']);

$failed_sims = [];

foreach ($sim_list as $line) {
    if (empty(trim($line))) continue;
    list($iccid, $store) = explode(",", $line);
    $iccid = trim($iccid);
    $store = trim($store);

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
    curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
    curl_setopt($ch, CURLOPT_POST, true);
    curl_setopt($ch, CURLOPT_POSTFIELDS, $xml);
    curl_setopt($ch, CURLOPT_HTTPHEADER, ['Content-Type: text/xml', 'SOAPAction: "urn:telispire:MdnServices/GetWirelessByICC"']);
    
    $response = curl_exec($ch);
    curl_close($ch);

    // בדיקה אם הקו קיים ואם החבילה תקינה
    $has_line = (strpos($response, '<MDN>') !== false);
    $has_correct_plan = (strpos($response, 'Prepaid Refills - Talk Only - 4G HD') !== false);

    if ($has_line && !$has_correct_plan) {
        $failed_sims[] = "סים: $iccid | חנות: $store | שגיאה: חבילה לא תקינה או חברה אחרת";
    }
}

// שליחת דוח במייל אם נמצאו תקלות
if (!empty($failed_sims)) {
    echo "FAILED:\n" . implode("\n", $failed_sims);
} else {
    echo "SUCCESS: All SIMs are OK.";
}
