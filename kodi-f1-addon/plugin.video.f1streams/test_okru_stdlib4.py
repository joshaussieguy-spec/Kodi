import http.client, ssl

ctx = ssl.create_default_context()
conn = http.client.HTTPSConnection('ok.ru', timeout=30, context=ctx)
conn.request('GET', '/video/16714114796204', headers={
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36',
    'Accept': 'text/html,*/*',
    'Accept-Encoding': 'identity',
    'Connection': 'close',
})
resp = conn.getresponse()
chunks = []
total = 0
while True:
    try:
        c = resp.read(65536)
    except Exception as e:
        print('read err mid-stream (tolerated):', type(e).__name__)
        break
    if not c:
        break
    chunks.append(c)
    total += len(c)
    if total > 3000000:
        break
body = b''.join(chunks)
print('status:', resp.status, 'bytes:', len(body), 'data-options:', b'data-options' in body)
conn.close()