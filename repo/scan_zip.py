import zipfile, os, re
REPO = r'C:\Users\Josh\Kodi\repo'
targets = [
    r'zips\plugin.video.f1streams\plugin.video.f1streams-2.8.18.zip',
    r'zips\plugin.video.f1streams.android\plugin.video.f1streams.android-2.8.15.zip',
]
pat = re.compile(rb'dailymotion|dai\.ly|dailym', re.I)
guard = re.compile(rb'removed 2026-11-02|stripped 2026-11-02', re.I)
for rel in targets:
    p = os.path.join(REPO, rel)
    z = zipfile.ZipFile(p)
    names = z.namelist()
    bad = [n for n in names
           if os.path.basename(n).startswith(('test_', 'probe_', 'check_', 'live_fire'))]
    dm = []
    for n in names:
        if n.endswith(('.py', '.json', '.xml', '.txt')):
            data = z.read(n)
            for m in pat.finditer(data):
                ctx = data[max(0, m.start()-40):m.end()+40]
                if not guard.search(ctx):
                    dm.append(n)
                    break
    print(os.path.basename(rel), '| files:', len(names),
          '| dev-scripts:', bad, '| live-dm-files:', dm)