<?php
// הגדרת איזור זמן
date_default_timezone_set('Asia/Jerusalem');

// טעינת קונפיגורציה
$configFile = 'config.json';
if (!file_exists($configFile)) {
    die("Error: config.json missing.");
}

$config = json_decode(file_get_contents($configFile), true);
$api_user = $config['user'] ?? '';
$api_pass = $config['pass'] ?? '';
$alert_email = $config['email'] ?? '';

// קבלת ארגומנטים (מצב ידני או אוטומטי)
$mode = $argv[1] ?? 'daily';
$manual_icc = $argv[2] ?? '';

// פונקציית הבדיקה הראשית
function checkSim($icc, $user, $pass) {
    $xml_post = '<?xml version="1.0" encoding="utf-8"?>
    <soap:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
      <soap:Body>
        <GetWirelessByICC xmlns="urn:telispire:MdnServices">
          <username>' . $user . '</username>
          <password>' . $pass . '</password>
          <icc>' . $icc . '</icc>
        </GetWirelessByICC>
      </soap:Body>
    </soap:Envelope>';

    $url = 'https://wirelessprovisioning.com/desktopmodules/telispire.webservices/mdnservices.asmx';
    
    $ch = curl_init();
    curl_setopt($ch, CURLOPT_URL, $url);
    curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
    curl_setopt($ch, CURLOPT_TIMEOUT, 45);
    curl_setopt($ch, CURLOPT_POST, true);
    curl_setopt($ch, CURLOPT_POSTFIELDS, $xml_post);
    curl_setopt($ch, CURLOPT_HTTPHEADER, [
        "Content-type: text/xml;charset=\"utf-8\"",
        "SOAPAction: urn:telispire:MdnServices/GetWirelessByICC",
        "Content-length: " . strlen($xml_post)
    ]);

    $response = curl_exec($ch);
    $err = curl_error($ch);
    curl_close($ch);

    if ($err) return ['status' => 'error', 'msg' => "Curl Error: $err"];

    // ניקוי ופיענוח XML
    $clean_xml = str_ireplace(['soap:', 'xmlns:'], '', $response);
    $xml = simplexml_load_string($clean_xml);

    if (!isset($xml->Body->GetWirelessByICCResponse->GetWirelessByICCResult)) {
        return ['status' => 'error', 'msg' => "Invalid API Response"];
    }

    $data = $xml->Body->GetWirelessByICCResponse->GetWirelessByICCResult;
    
    // שליפת נתונים קריטיים
    $planName = (string)$data->PlanName;
    $simStatus = (string)$data->WirelessStatus; // Active / Deactive / Suspended

    return [
        'status' => 'success',
        'sim_status' => $simStatus,
        'plan_name' => $planName
    ];
}

// לוגיקה עסקית
function analyzeSim($icc, $storeName, $result) {
    if ($result['status'] == 'error') {
        return "שגיאה טכנית בסים $icc בחנות $storeName: " . $result['msg'];
    }

    $status = strtolower($result['sim_status']);
    $plan = trim($result['plan_name']);
    $requiredPlan = "Prepaid Refills - Talk Only - 4G HD";

    // אם אין קו פעיל - הכל טוב
    if ($status != 'active') {
        return "OK"; // לא פעיל, אין צורך לבדוק חבילה
    }

    // יש קו פעיל - בודקים חבילה
    if ($plan == $requiredPlan) {
        return "OK"; // חבילה נכונה
    }

    // קו פעיל עם חבילה לא נכונה!
    return "חריגה! חנות: $storeName | סים: $icc | סטטוס: $status | חבילה נוכחית: $plan (נדרש: $requiredPlan)";
}

// --- ביצוע בפועל ---

if ($mode == 'single' && !empty($manual_icc)) {
    // בדיקה ידנית
    echo "מבצע בדיקה עבור סים: $manual_icc ...\n";
    $res = checkSim($manual_icc, $api_user, $api_pass);
    
    if($res['status'] == 'error') {
        echo "שגיאה: " . $res['msg'];
    } else {
        echo "תוצאות API:\n";
        echo "סטטוס קו: " . $res['sim_status'] . "\n";
        echo "שם חבילה: " . $res['plan_name'] . "\n";
        
        $analysis = analyzeSim($manual_icc, "בדיקה ידנית", $res);
        if($analysis == "OK") echo "\n>> סיכום: סים תקין (או לא פעיל).";
        else echo "\n>> " . $analysis;
    }

} else {
    // בדיקה יומית מלאה
    $csvLines = file('sims.csv', FILE_IGNORE_NEW_LINES | FILE_SKIP_EMPTY_LINES);
    $report = "דוח בדיקת סימים - " . date("d/m/Y H:i") . "\n";
    $report .= "========================================\n";
    
    $errors = [];
    $count = 0;

    foreach ($csvLines as $line) {
        $parts = str_getcsv($line);
        if (count($parts) < 2) continue;
        
        $store = $parts[0];
        $icc = $parts[1];
        
        // כותרת
        if($store == 'StoreName') continue;

        $count++;
        $res = checkSim($icc, $api_user, $api_pass);
        $analysis = analyzeSim($icc, $store, $res);

        if ($analysis != "OK") {
            $errors[] = $analysis;
            $report .= "[X] " . $analysis . "\n";
        }
        
        // השהייה קטנה למניעת עומס
        usleep(500000); 
    }

    if (empty($errors)) {
        $report .= "כל הסימים ($count) נבדקו ונמצאו תקינים.\n";
    } else {
        $report .= "\nסיכום: נמצאו " . count($errors) . " חריגות.\n";
        
        // שליחת מייל
        if (!empty($alert_email)) {
            $subject = "התראת מערכת סימים - נמצאו חריגות";
            $headers = "From: system@github-actions.local\r\n";
            $headers .= "Content-Type: text/plain; charset=UTF-8\r\n";
            
            // נסיון שליחה פשוט דרך PHP
            mail($alert_email, $subject, $report, $headers);
            $report .= "\n(נשלחה התראה למייל: $alert_email)\n";
        }
    }

    echo $report;
    // שמירה לקובץ חיצוני שהאתר יוכל לקרוא
    file_put_contents('last_report.txt', $report);
}
?>
