<?php
$db_file = 'config.json';
$data = json_decode(file_get_contents($db_file), true);

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

function checkSingleSim($iccid, $user, $pass) {
    $apiUrl = "https://wirelessprovisioning.com/desktopmodules/telispire.webservices/mdnservices.asmx";
    $xml = '<?xml version="1.0" encoding="utf-8"?><soap:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/"><soap:Body><GetWirelessByICC xmlns="urn:telispire:MdnServices"><username>'.$user.'</username><password>'.$pass.'</password><ICCID>'.$iccid.'</ICCID></GetWirelessByICC></soap:Body></soap:Envelope>';
    $ch = curl_init($apiUrl);
    curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
    curl_setopt($ch, CURLOPT_POSTFIELDS, $xml);
    curl_setopt($ch, CURLOPT_HTTPHEADER, ['Content-Type: text/xml; charset=utf-8', 'SOAPAction: "urn:telispire:MdnServices/GetWirelessByICC"']);
    $res = curl_exec($ch); curl_close($ch);
    return $res;
}
?>
<!DOCTYPE html>
<html dir="rtl" lang="he">
<head>
    <meta charset="utf-8"><title>מערכת ניהול סימים</title>
    <style>body { font-family: sans-serif; background: #f0f2f5; padding: 20px; } .card { background: white; padding: 20px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); margin-bottom: 20px; }</style>
</head>
<body>
    <div class="card">
        <h2>🔑 הגדרות API (שנה מתי שתרצה)</h2>
        <form method="post">
            <input type="text" name="user" placeholder="User" value="<?= $data['auth']['user'] ?>">
            <input type="password" name="pass" placeholder="Pass" value="<?= $data['auth']['pass'] ?>">
            <input type="email" name="email" placeholder="Email להתראות" value="<?= $data['settings']['alert_email'] ?>">
            <button type="submit" name="save_settings">שמור הגדרות</button>
        </form>
    </div>

    <div class="card">
        <h2>🔍 בדיקת סים ספציפי בזמן אמת</h2>
        <form method="get">
            <input type="text" name="check_iccid" placeholder="הכנס ICCID">
            <button type="submit">בדוק עכשיו 🚀</button>
        </form>
        <?php if(isset($_GET['check_iccid'])): 
            $raw = checkSingleSim($_GET['check_iccid'], $data['auth']['user'], $data['auth']['pass']);
            echo "<pre>תוצאה גולמית מהשרת:\n".htmlspecialchars($raw)."</pre>";
        endif; ?>
    </div>

    <div class="card">
        <h2>📋 רשימת חנויות וסימים (למעקב יומי)</h2>
        <form method="post">
            <input type="text" name="iccid" placeholder="ICCID" required>
            <input type="text" name="shop" placeholder="שם חנות" required>
            <button type="submit" name="add_sim">הוסף למעקב</button>
        </form>
        <table border="1" style="width:100%; margin-top:10px; border-collapse: collapse;">
            <tr><th>חנות</th><th>ICCID</th><th>פעולה</th></tr>
            <?php foreach ($data['sims'] as $i => $sim): ?>
            <tr><td><?= $sim['shop'] ?></td><td><?= $sim['iccid'] ?></td><td><form method="post"><input type="hidden" name="index" value="<?= $i ?>"><button type="submit" name="delete_sim">מחק</button></form></td></tr>
            <?php endforeach; ?>
        </table>
    </div>
</body>
</html>
