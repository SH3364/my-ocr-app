<?php
$db_file = 'config.json';
$data = json_decode(file_get_contents($db_file), true);

// שמירת שינויים
if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    if (isset($_POST['save_settings'])) {
        $data['auth']['user'] = $_POST['user'];
        $data['auth']['pass'] = $_POST['pass'];
        $data['settings']['alert_email'] = $_POST['email'];
    } elseif (isset($_POST['add_sim'])) {
        $data['sims'][] = ['iccid' => $_POST['iccid'], 'shop' => $_POST['shop']];
    } elseif (isset($_POST['delete_sim'])) {
        array_splice($data['sims'], $_POST['index'], 1);
    }
    file_put_contents($db_file, json_encode($data, JSON_PRETTY_PRINT | JSON_UNESCAPED_UNICODE));
    header("Location: admin.php"); exit;
}
?>
<!DOCTYPE html>
<html dir="rtl" lang="he">
<head>
    <meta charset="utf-8">
    <title>ניהול מערכת סימים</title>
    <style>
        body { font-family: Arial; margin: 20px; background: #f4f4f4; }
        .card { background: white; padding: 20px; border-radius: 8px; margin-bottom: 20px; box-shadow: 0 2px 5px rgba(0,0,0,0.1); }
        input { padding: 8px; margin: 5px; width: 200px; }
        button { padding: 8px 15px; cursor: pointer; background: #007bff; color: white; border: none; border-radius: 4px; }
        table { width: 100%; border-collapse: collapse; margin-top: 10px; }
        th, td { border: 1px solid #ddd; padding: 10px; text-align: right; }
    </style>
</head>
<body>
    <h1>⚙️ ניהול מערכת סימים</h1>
    
    <div class="card">
        <h3>הגדרות API ומייל להתראות</h3>
        <form method="post">
            <input type="text" name="user" placeholder="שם משתמש API" value="<?= $data['auth']['user'] ?>">
            <input type="password" name="pass" placeholder="סיסמה API" value="<?= $data['auth']['pass'] ?>">
            <input type="email" name="email" placeholder="מייל לקבלת התראות" value="<?= $data['settings']['alert_email'] ?>">
            <button type="submit" name="save_settings">שמור הגדרות</button>
        </form>
    </div>

    <div class="card">
        <h3>הוספת סים חדש למעקב</h3>
        <form method="post">
            <input type="text" name="iccid" placeholder="ICCID" required>
            <input type="text" name="shop" placeholder="שם חנות" required>
            <button type="submit" name="add_sim">הוסף לרשימה</button>
        </form>
    </div>

    <div class="card">
        <h3>רשימת סימים במעקב</h3>
        <table>
            <tr><th>שם חנות</th><th>ICCID</th><th>פעולות</th></tr>
            <?php foreach ($data['sims'] as $i => $sim): ?>
            <tr>
                <td><?= $sim['shop'] ?></td>
                <td><?= $sim['iccid'] ?></td>
                <td>
                    <form method="post" style="display:inline;">
                        <input type="hidden" name="index" value="<?= $i ?>">
                        <button type="submit" name="delete_sim" style="background:red;">מחק</button>
                    </form>
                </td>
            </tr>
            <?php endforeach; ?>
        </table>
    </div>

    <p><a href="cron.php" target="_blank">לחץ כאן להרצת בדיקה ידנית עכשיו 🚀</a></p>
</body>
</html>
