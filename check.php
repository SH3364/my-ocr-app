<?php
$data = json_decode(file_get_contents('data.json'), true);
$api_user = $data['user'];
$api_pass = $data['pass'];
$sim_lines = explode("\n", $data['sims']);

$failed_sims = [];

foreach ($sim_lines as $line) {
    if (trim($line) == "") continue;
    $parts = explode(",", $line);
    $iccid = trim($parts[0]);
    $store = isset($parts[1]) ? trim($parts[1]) : "Unknown";

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
    curl_setopt($ch, CURLOPT_POSTFIELDS, $xml);
    $res = curl_exec($ch);
    curl_close($ch);

    // בדיקה: אם יש קו (MDN קיים) אבל החבילה לא תואמת
    if (strpos($res, '<MDN>') !== false) {
        if (strpos($res, 'Prepaid Refills - Talk Only - 4G HD') === false) {
            $failed_sims[] = "ICCID: $iccid | Store: $store | Status: Wrong Plan/Provider";
        }
    }
}

if (!empty($failed_sims)) {
    echo "REPORT_START\n" . implode("\n", $failed_sims);
}
