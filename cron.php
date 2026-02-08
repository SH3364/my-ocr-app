<?php
include 'functions.php';

$sims = $db->query("SELECT * FROM sims")->fetchAll();
$errors = [];
$target_plan = "Prepaid Refills - Talk Only - 4G HD";

foreach ($sims as $sim) {
    $data = checkSimDetails($sim['iccid']);
    
    // שליפת הנתונים הרלוונטיים מה-XML (יש להתאים לשמות השדות המדויקים מה-API)
    $status = (string)$data->Body->GetWirelessByICCResponse->GetWirelessByICCResult->Status;
    $current_plan = (string)$data->Body->GetWirelessByICCResponse->GetWirelessByICCResult->PlanName;

    // לוגיקה: אם יש קו והחבילה לא תואמת
    if ($status == "Active" && $current_plan != $target_plan) {
        $errors[] = "סים: " . $sim['iccid'] . " | חנות: " . $sim['shop_name'] . " | חבילה נוכחית: " . $current_plan;
    }
}

if (!empty($errors)) {
    $to = getSetting('admin_email');
    $subject = "התראת סימים - חבילות לא תקינות";
    $message = "להלן רשימת הסימים שלא עברו את הבדיקה:\n\n" . implode("\n", $errors);
    mail($to, $subject, $message);
    echo "Email sent with " . count($errors) . " errors.";
} else {
    echo "All SIMs are OK.";
}
