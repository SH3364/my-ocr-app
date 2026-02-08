<?php 
include 'functions.php';

// שמירת הגדרות חדשות
if (isset($_POST['save_settings'])) {
    $stmt = $db->prepare("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)");
    $stmt->execute(['api_user', $_POST['api_user']]);
    $stmt->execute(['api_pass', $_POST['api_pass']]);
    $stmt->execute(['admin_email', $_POST['admin_email']]);
}

// הוספת סים חדש
if (isset($_POST['add_sim'])) {
    $stmt = $db->prepare("INSERT INTO sims (iccid, shop_name) VALUES (?, ?)");
    $stmt->execute([$_POST['iccid'], $_POST['shop_name']]);
}
?>

<!DOCTYPE html>
<html lang="he" dir="rtl">
<head>
    <meta charset="UTF-8">
    <title>ניהול סימים - Telispire</title>
    <link rel="stylesheet" href="style.css">
</head>
<body>
    <h1>ניהול מערכת סימים</h1>
    
    <section>
        <h2>הגדרות מערכת</h2>
        <form method="post">
            <input type="text" name="api_user" placeholder="שם משתמש API" value="<?=getSetting('api_user')?>">
            <input type="password" name="api_pass" placeholder="סיסמה" value="<?=getSetting('api_pass')?>">
            <input type="email" name="admin_email" placeholder="אימייל להתראות" value="<?=getSetting('admin_email')?>">
            <button type="submit" name="save_settings">שמור הגדרות</button>
        </form>
    </section>

    <hr>

    <section>
        <h2>הוספת סים לרשימה</h2>
        <form method="post">
            <input type="text" name="iccid" placeholder="מספר ICCID" required>
            <input type="text" name="shop_name" placeholder="שם חנות" required>
            <button type="submit" name="add_sim">הוסף סים</button>
        </form>
    </section>

    <hr>

    <h2>רשימת סימים קיימת</h2>
    <table border="1">
        <tr>
            <th>ICCID</th>
            <th>חנות</th>
            <th>בדיקה מהירה</th>
        </tr>
        <?php
        $sims = $db->query("SELECT * FROM sims")->fetchAll();
        foreach ($sims as $sim): ?>
        <tr>
            <td><?=$sim['iccid']?></td>
            <td><?=$sim['shop_name']?></td>
            <td><a href="?check=<?=$sim['iccid']?>">בדוק עכשיו</a></td>
        </tr>
        <?php endforeach; ?>
    </table>

    <?php if(isset($_GET['check'])): 
        $res = checkSimDetails($_GET['check']);
        echo "<h3>תוצאת בדיקה ל-".$_GET['check'].":</h3>";
        echo "<pre>"; print_r($res); echo "</pre>";
    endif; ?>
</body>
</html>
