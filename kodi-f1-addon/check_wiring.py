import ast, json
import xml.dom.minidom as md

files = [
    'plugin.video.f1streams/main.py',
    'plugin.video.f1streams.android/main.py',
    'plugin.video.f1streams/fullraces_android.py',
    'plugin.video.f1streams/fullraces.py',
    'sync-flavors.py',
]
for f in files:
    ast.parse(open(f, encoding='utf-8').read())
print('AST OK ALL')

for x in ['plugin.video.f1streams/addon.xml',
          'plugin.video.f1streams.android/addon.xml']:
    md.parse(x)
print('XML OK BOTH')

# identical main.py on both flavors? (EOL-normalized: sync writes LF on the
# Android twin by design, PC stays CRLF)
pc = open('plugin.video.f1streams/main.py', 'rb').read().replace(b'\r\n', b'\n')
an = open('plugin.video.f1streams.android/main.py', 'rb').read().replace(b'\r\n', b'\n')
print('main.py content-identical (EOL-norm):', pc == an)
print('fullraces_android identical:', open(
    'plugin.video.f1streams/fullraces_android.py', 'rb').read() == open(
    'plugin.video.f1streams.android/fullraces_android.py', 'rb').read())

# replay-catalog shape
c = json.load(open('replay-catalog.json', encoding='utf-8'))
print('catalog: races=%d with_ok_ru=%d' % (
    len(c['races']), sum(1 for r in c['races'] if r.get('ok_ru'))))