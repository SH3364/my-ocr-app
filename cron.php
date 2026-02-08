<?php
$config = json_decode(file_get_contents('config.json'), true);
$sims = json_decode(file_get_contents('sims.json'), true);

$errors = [];
$targetPlan = "Prepaid Refills - Talk Only - 4G HD";

foreach ($sims as $sim) {
    $result = callTelispireAPI($sim['iccid'], $config['user'], $config['pass']);
    
    // ניתוח תוצאה (בהתאם למבנה ה-XML של הספק)
    if ($result) {
        $status = (string)$result->Body->GetWirelessByICCResponse->GetWirelessByICCResult->Status;
        $plan = (string)$result->Body->GetWirelessByICCResponse->GetWirelessByICCResult->PlanName;

        if ($status == "Active" && $plan != $targetPlan) {
            $errors[] = "סים: {$sim['iccid']} | חנות: {$sim['shop']} | חבילה נוכחית: $plan";
        }
    }
}

if (!empty($errors)) {
    $msg = "נמצאו סימים עם חבילה לא תקינה:\n\n" . implode("\n", $errors);
    mail($config['email'], "התראת סימים יומית", $msg);
}

function callTelispireAPI($iccid, $user, $pass) {
    $url = "https://wirelessprovisioning.com/desktopmodules/telispire.webservices/mdnservices.asmx/";
    $xml = '<?xml version="1.0" encoding="utf-8"?>
    <soap:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
      <soap:Body>
        <GetWirelessByICC xmlns="urn:telispire:MdnServices">
          <ICC>'.$iccid.'</ICC>
          <Username>'.$user.'</Username>
          <Password>'.$pass.'</Password>
        </GetWirelessByICC>
      </soap:Body>
    </soap:Envelope>';

    $ch = curl_init($url);
    curl_setopt($ch, CURLOPT_HTTPHEADER, ['Content-Type: text/xml', 'SOAPAction: "urn:telispire:MdnServices/GetWirelessByICC"']);
    curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
    curl_setopt($ch, CURLOPT_POSTFIELDS, $xml);
    $response = curl_exec($ch);
    curl_close($ch);
    
    return simplexml_load_string(str_ireplace(['soap:', 'xmlns:'], '', $response));
}
