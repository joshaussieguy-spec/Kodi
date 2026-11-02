import zipfile, io
REPO = r'C:\Users\Josh\Kodi\repo'
for rel in [r'zips\plugin.video.f1streams\plugin.video.f1streams-2.8.19.zip',
            r'zips\plugin.video.f1streams.android\plugin.video.f1streams.android-2.8.16.zip']:
    z = zipfile.ZipFile(REPO + '\\' + rel)
    src = z.read([n for n in z.namelist() if n.endswith('main.py')][0]).decode('utf-8', 'replace')
    hits = {c: ("'%s'" % c) in src for c in ('38', '449', '424', '60', '537')}
    ax = z.read([n for n in z.namelist() if n.endswith('addon.xml')][0]).decode('utf-8', 'replace')
    ver = ax.split('version="')[1].split('"')[0]
    print(rel.split('\\')[-1], '| version:', ver, '| lanes:', hits)