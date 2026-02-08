<?php
// הגדרות API (יימשכו מתוך הגדרות המערכת של GitHub)
$api_user = getenv('API_USER');
$api_pass = getenv('API_PASS');
$email_to = getenv('EMAIL_TO');

$sims_file = 'sims.csv';
$failed_sims = [];

if (!file_exists($sims_file)) die("File not found");

$handle = fopen($sims_file, "r");
fgetcsv($handle); // דלוג על כותרת

while (($data = fgetcsv($handle)) !== FALSE) {
    $icc = $data[0];
    $shop = $data[1];
    
    $result = check_sim_status($icc, $api_user, $api_pass);
    
    // בדיקה: אם יש קו (Active/Existing) והחבילה לא תואמת
    if ($result['has_line'] && $result['plan'] !== "Prepaid Refills - Talk Only - 4G HD") {
        $failed_sims[] = "ICC: $icc | Shop: $shop | Plan: " . ($result['plan'] ?: "Unknown/Other Company");
    }
}
fclose($handle);

// שליחת מייל אם נמצאו תקלות
if (!empty($failed_sims)) {
    $message = "The following SIMs failed validation:\n\n" . implode("\n", $failed_sims);
    mail($email_to, "SIM Check Alert - Report", $message);
    echo "Report sent to $email_to";
} else {
    echo "All SIMs are OK.";
}

function check_sim_status($icc, $user, $pass) {
    $url = "https://wirelessprovisioning.com/desktopmodules/telispire.webservices/mdnservices.asmx";
    $xml_post = '<?xml version="1.0" encoding="utf-8"?>
    <soap:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
      <soap:Body>
        <GetWirelessByICC xmlns="urn:telispire:MdnServices">
          <Icc>' . $icc . '</Icc>
          <User>' . $user . '</User>
          <Password>' . $pass . '</Password>
        </GetWirelessByICC>
      </soap:Body>
    </soap:Envelope>';

    $ch = curl_init($url);
    curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
    curl_setopt($ch, CURLOPT_POST, true);
    curl_setopt($ch, CURLOPT_POSTFIELDS, $xml_post);
    curl_setopt($ch, CURLOPT_HTTPHEADER, [
        'Content-Type: text/xml; charset=utf-8',
        'SOAPAction: "urn:telispire:MdnServices/GetWirelessByICC"'
    ]);

    $response = curl_exec($ch);
    curl_close($ch);

    // ניתוח פשוט של התגובה (ניתן לשפר עם SimpleXMLElement)
    $has_line = (strpos($response, '<Mdn>') !== false); 
    preg_match('/<RatePlanName>(.*?)<\/RatePlanName>/', $response, $matches);
    $plan = $matches[1] ?? null;

    return ['has_line' => $has_line, 'plan' => $plan];
}
