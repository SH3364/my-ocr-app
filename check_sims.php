<?php
// קריאת הנתונים מהקובץ המעודכן
$config = json_decode(file_get_contents('config.json'), true);

$api_user = $config['api_user'];
$api_pass = $config['api_pass'];
$sims = $config['sims'];

$failures = [];

foreach ($sims as $sim) {
    // ... (אותו קוד מהתשובה הקודמת שמבצע את ה-CURL)
    // הבדיקה תתבצע לפי הנתונים ששמרת באתר
}

// בסיום, שליחת המייל כרגיל
