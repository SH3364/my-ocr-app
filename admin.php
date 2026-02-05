<?php
$db_file = 'config.json';
$data = json_decode(file_get_contents($db_file), true);

// שמירת הגדרות וניהול סימים
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

// פונקציית בדיקה בזמן אמת
function checkLive($iccid, $u, $p) {
    $url = "https://wirelessprovisioning.com/desktopmodules/telispire.webservices/mdnservices.asmx";
    $xml = '<?xml version="1.0" encoding="utf-8"?><soap:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/"><soap:Body><GetWirelessByICC xmlns="urn:telispire:MdnServices"><username>'.$u.'</username><password>'.$p.'</password><ICCID>'.$iccid.'</ICCID></GetWirelessByICC></soap:Body></soap:Envelope>';
    $ch = curl_init($url);
    curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
    curl_setopt($ch, CURLOPT_POST, true);
    curl_setopt($ch, CURLOPT_POSTFIELDS, $xml);
    curl_setopt($ch, CURLOPT_HTTPHEADER, ['Content-Type: text/xml; charset=utf-8', 'SOAPAction: "urn:telispire:MdnServices/GetWirelessByICC"']);
    $res = curl_exec($ch); curl_close($ch);
    return $res;
}
?>
<!DOCTYPE html>
<html dir="rtl" lang="he">
<head>
    <meta charset="utf-8"><title>ניהול סימים</title>
    <style>
        body { font-family: sans-serif; background: #f4f7f6; padding: 20px; }
        .card { background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); margin-bottom: 20px; }
        input, button { padding: 10px; margin: 5px; border-radius: 4px; border: 1px solid #ddd; }
        button { background: #007bff; color: white; cursor: pointer; border: none; }
        table { width: 100%; border-collapse: collapse; background: white; }
        th, td { padding: 12px; border-bottom: 1px solid #eee; text-align: right; }
    </style>
</head>
<body>
    <h1>📱 מערכת ניהול סימים</h1>

    <div class="card">
        <h3>🔑 הגדרות API ומייל (שינוי קל בכל עת)</h3>
        <form method="post">
            <input type="text" name="user" placeholder="User" value="<?= $data['auth']['user'] ?>">
            <input type="password" name="pass" placeholder="Pass" value="<?= $data['auth']['pass'] ?>">
            <input type="email" name="email" placeholder="מייל להתראות" value="<?= $data['settings']['alert_email'] ?>">
            <button type="submit" name="save_settings">שמור הגדרות</button>
        </form>
    </div>

    <div class="card">
        <h3>🔍 בדיקה בזמן אמת (Live Check)</h3>
        <form method="get">
            <input type="text" name="live_iccid" placeholder="הכנס ICCID לבדיקה" required>
            <button type="submit">בדוק עכשיו 🚀</button>
        </form>
        <?php if(isset($_GET['live_iccid'])): 
            $raw = checkLive($_GET['live_iccid'], $data['auth']['user'], $data['auth']['pass']);
            echo "<h4>תוצאה:</h4><pre style='background:#eee;padding:10px;'>".htmlspecialchars($raw)."</pre>";
        endif; ?>
    </div>

    <div class="card">
        <h3>📋 ניהול רשימת חנויות</h3>
        <form method="post">
            <input type="text" name="iccid" placeholder="ICCID" required>
            <input type="text" name="shop" placeholder="שם חנות" required>
            <button type="submit" name="add_sim">הוסף למעקב</button>
        </form>
        <table>
            <tr><th>חנות</th><th>ICCID</th><th>פעולה</th></tr>
            <?php foreach ($data['sims'] as $i => $sim): ?>
            <tr><td><?= $sim['shop'] ?></td><td><?= $sim['iccid'] ?></td><td><form method="post"><input type="hidden" name="index" value="<?= $i ?>"><button type="submit" name="delete_sim" style="background:red;">מחק</button></form></td></tr>
            <?php endforeach; ?>
        </table>
    </div>
</body>
</html>
