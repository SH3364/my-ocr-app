<?php
$config = json_decode(file_get_contents('config.json'), true);
$failed_sims = [];

foreach ($config['sims'] as $sim) {
    $icc = $sim['icc'];
    $shop = $sim['shop'];

    $xml = '<?xml version="1.0" encoding="utf-8"?>
    <soap:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
      <soap:Body>
        <GetWirelessByICC xmlns="urn:telispire:MdnServices">
          <userName>' . $config['api_user'] . '</userName>
          <password>' . $config['api_pass'] . '</password>
          <ICC>' . $icc . '</ICC>
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

    // בדיקה אם הסים פעיל ובחבילה הנכונה
    $has_line = (strpos($response, '<Status>Active</Status>') !== false);
    $has_package = (strpos($response, 'Prepaid Refills - Talk Only - 4G HD') !== false);

    if ($has_line && !$has_package) {
        $failed_sims[] = "סים: $icc | חנות: $shop | חבילה לא תקינה או חברה אחרת.";
    }
}

if (!empty($failed_sims)) {
    $to = $config['target_email'];
    $subject = "דיווח סימים שלא עברו בדיקה";
    $body = "נמצאו סימים עם חבילה לא תקינה:\n\n" . implode("\n", $failed_sims);
    
    // שליחה דרך PHP (ב-GitHub נדרש שרת SMTP)
    echo $body;
    // כאן מומלץ להשתמש ב-sendgrid או שירות דומה לשליחה פשוטה ב-curl
} else {
    echo "כל הסימים תקינים.";
}
