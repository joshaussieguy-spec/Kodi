import subprocess, os, re
EXE = os.path.join(r'C:\Users\Josh\Kodi\kodi-f1-addon\plugin.video.f1streams', 'bin', 'curl-impersonate.exe')
for a in (EXE, '--version'):
    pass
p = subprocess.run([EXE, '--version'], capture_output=True, text=True, timeout=15)
print(p.stdout[:200] or p.stderr[:200])