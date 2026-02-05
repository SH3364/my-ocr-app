<?php
$data = json_decode(file_get_contents('config.json'), true);
$apiUrl = "https://wirelessprovisioning.com/desktopmodules/telispire.webservices/mdnservices.asmx";
$targetPlan = $data['settings']['target_plan'];

$alerts = [];
foreach ($data['sims'] as $sim) {
    $xml = '<?xml version="1.0" encoding="utf-8"?><soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/"><soap:Body><GetWirelessByICC xmlns="urn:telispire:MdnServices"><username>'.$data['auth']['user'].'</username><password>'.$data['auth']['pass'].'</password><ICCID>'.$sim['iccid'].'</ICCID></GetWirelessByICC></soap:Body></soap:Envelope>';
    
    $ch = curl_init($apiUrl);
    curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
    curl_setopt($ch, CURLOPT_POSTFIELDS, $xml);
    curl_setopt($ch, CURLOPT_HTTPHEADER, ['Content-Type: text/xml', 'SOAPAction: "urn:telispire:MdnServices/GetWirelessByICC"']);
    $response = curl_exec($ch); curl_close($ch);

    $xmlObj = simplexml_load_string(str_ireplace(['soap:', 'soapenv:'], '', $response));
    $res = $xmlObj->Body->GetWirelessByICCResponse->GetWirelessByICCResult;
    
    $status = (string)$res->Status;
    $plan = (string)$res->RatePlan;

    // לוגיקה: אם לא Available והחבילה לא תואמת - התראה!
    if ($status !== "Available" && $plan !== $targetPlan) {
        $alerts[] = "חנות: {$sim['shop']} | ICCID: {$sim['iccid']} | חבילה: $plan";
    }
}

if (!empty($alerts)) {
    mail($data['settings']['alert_email'], "התראת סימים: חבילה שגויה!", "נמצאו חריגות:\n\n" . implode("\n", $alerts));
}
