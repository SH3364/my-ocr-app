<?php
// טעינת הגדרות מקובץ הקונפיגורציה
$configFile = 'config.json';
if (!file_exists($configFile)) die("קובץ הגדרות חסר.");

$config = json_decode(file_get_contents($configFile), true);
$api_username = $config['user'] ?? '';
$api_password = $config['pass'] ?? '';

// הפונקציה לבדיקת סים
function checkSim($icc, $storeName, $user, $pass) {
    // ... (אותו קוד בדיוק כמו שכתבתי לך בתשובה הקודמת עבור ה-XML וה-CURL)
    // רק שים לב להשתמש במשתנים $user ו-$pass שהתקבלו בפונקציה
    
    $xml_post_string = '<?xml version="1.0" encoding="utf-8"?>
    <soap:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
      <soap:Body>
        <GetWirelessByICC xmlns="urn:telispire:MdnServices">
          <username>' . $user . '</username>
          <password>' . $pass . '</password>
          <icc>' . $icc . '</icc>
        </GetWirelessByICC>
      </soap:Body>
    </soap:Envelope>';
    
    // ... המשך קוד ה-CURL והבדיקה זהה לקודם ...
    // קיצור לצורך התשובה - תעתיק את הלוגיקה מהתשובה הקודמת לכאן
    
    // לצורך הדגמה, נניח שהבדיקה מחזירה:
    // return "Active" או הודעת שגיאה
    
    // כאן צריך להדביק את הקוד האמיתי של ה-CURL מהתשובה הקודמת!
}

// קוד ההרצה הראשי (Main)
$mode = $argv[1] ?? 'daily'; // 'daily' or 'single'

if ($mode === 'single') {
    $icc = $argv[2];
    echo "בודק סים בודד: $icc\n";
    // כאן תהיה קריאה לפונקציה
    // $res = checkSim($icc, "בדיקה ידנית", $api_username, $api_password);
    // echo $res;
} else {
    // בדיקה יומית (קריאת CSV)
    $csv = array_map('str_getcsv', file('sims.csv'));
    $report = "דוח בדיקה - " . date("Y-m-d H:i:s") . "\n-------------------\n";
    foreach($csv as $row) {
        if($row[0] == 'StoreName') continue;
        // לוגיקת בדיקה...
    }
    // שמירת הדוח לקובץ כדי שהאתר יוכל להציג אותו
    file_put_contents("last_report.txt", $report);
}
?>
