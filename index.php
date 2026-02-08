<?php
$configFile = 'config.json';
$simsFile = 'sims.json';

// טעינת נתונים
$config = file_exists($configFile) ? json_decode(file_get_contents($configFile), true) : ['user' => '', 'pass' => '', 'email' => ''];
$sims = file_exists($simsFile) ? json_decode(file_get_contents($simsFile), true) : [];

// שמירת הגדרות
if (isset($_POST['save_config'])) {
    $config = ['user' => $_POST['user'], 'pass' => $_POST['pass'], 'email' => $_POST['email']];
    file_put_contents($configFile, json_encode($config));
}

// הוספת סים
if (isset($_POST['add_sim'])) {
    $sims[] = ['iccid' => $_POST['iccid'], 'shop' => $_POST['shop']];
    file_put_contents($simsFile, json_encode($sims));
}

// מחיקת סים
if (isset($_GET['delete'])) {
    unset($sims[$_GET['delete']]);
    file_put_contents($simsFile, json_encode(array_values($sims)));
    header("Location: index.php");
}
?>

<!DOCTYPE html>
<html lang="he" dir="rtl">
<head>
    <meta charset="UTF-8">
    <title>מערכת ניהול סימים</title>
    <style>
        body { font-family: system-ui; margin: 20px; background: #f4f4f9; }
        .card { background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 5px rgba(0,0,0,0.1); margin-bottom: 20px; }
        input { padding: 8px; margin: 5px; border: 1px solid #ccc; border-radius: 4px; }
        button { padding: 8px 15px; background: #007bff; color: white; border: none; cursor: pointer; border-radius: 4px; }
        table { width: 100%; border-collapse: collapse; background: white; }
        th, td { padding: 10px; border: 1px solid #ddd; text-align: right; }
    </style>
</head>
<body>

<div class="card">
    <h2>הגדרות API</h2>
    <form method="post">
        <input type="text" name="user" placeholder="שם משתמש" value="<?=$config['user']?>">
        <input type="password" name="pass" placeholder="סיסמה" value="<?=$config['pass']?>">
        <input type="email" name="email" placeholder="אימייל להתראות" value="<?=$config['email']?>">
        <button type="submit" name="save_config">שמור הגדרות</button>
    </form>
</div>

<div class="card">
    <h2>הוספת סים חדש</h2>
    <form method="post">
        <input type="text" name="iccid" placeholder="מספר סים (ICCID)" required>
        <input type="text" name="shop" placeholder="שם חנות" required>
        <button type="submit" name="add_sim">הוסף לרשימה</button>
    </form>
</div>

<div class="card">
    <h2>רשימת סימים</h2>
    <table>
        <tr>
            <th>ICCID</th>
            <th>חנות</th>
            <th>פעולות</th>
        </tr>
        <?php foreach ($sims as $id => $sim): ?>
        <tr>
            <td><?=$sim['iccid']?></td>
            <td><?=$sim['shop']?></td>
            <td>
                <a href="check_single.php?iccid=<?=$sim['iccid']?>">בדיקה בזמן אמת</a> | 
                <a href="?delete=<?=$id?>" style="color:red;">מחיקה</a>
            </td>
        </tr>
        <?php endforeach; ?>
    </table>
</div>

</body>
</html>
