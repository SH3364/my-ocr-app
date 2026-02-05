<?php
$data = json_decode(file_get_contents('config.json'), true);
$apiUrl = "https://wirelessprovisioning.com/desktopmodules/telispire.webservices/mdnservices.asmx";
$targetPlan = "Prepaid Refills - Talk Only - 4G HD";

$alerts = [];
foreach ($data['sims'] as $sim) {
    $xml = '<?xml version="1.0" encoding="utf-8"?><soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/"><soap:Body><GetWirelessByICC xmlns="urn:telispire:MdnServices"><username>'.$data['auth']['user'].'</username><password>'.$data['auth']['pass'].'</password><ICCID>'.$sim['iccid'].'</ICCID></GetWirelessByICC></soap:Body></soap:Envelope>';
    
    $ch = curl_init($apiUrl);
    curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
    curl_setopt($ch, CURLOPT_POSTFIELDS, $xml);
    curl_setopt($ch, CURLOPT_HTTPHEADER, ['Content-Type: text/xml', 'SOAPAction: "urn:telispire:MdnServices/GetWirelessByICC"']);
    $res = curl_exec($ch); curl_close($ch);

    $clean = str_ireplace(['soap:', 'soapenv:'], '', $res);
    $xmlObj = simplexml_load_string($clean);
    $info = $xmlObj->Body->GetWirelessByICCResponse->GetWirelessByICCResult;
    
    $status = (string)$info->Status;
    $plan = (string)$info->RatePlan;

    // התראה אם הסים תפוס עם חבילה לא נכונה
    if ($status !== "Available" && $plan !== $targetPlan) {
        $alerts[] = "חנות: {$sim['shop']} | ICCID: {$sim['iccid']} | חבילה שנמצאה: $plan";
    }
}

if (!empty($alerts) && !empty($data['settings']['alert_email'])) {
    mail($data['settings']['alert_email'], "התראת חבילה שגויה!", "נמצאו חריגות:\n\n" . implode("\n", $alerts));
}
