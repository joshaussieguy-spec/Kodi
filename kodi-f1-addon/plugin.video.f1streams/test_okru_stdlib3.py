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
body = resp.read()
print('status:', resp.status, 'CE:', resp.headers.get('Content-Encoding'), 'len:', len(body))
print('data-options present:', b'data-options' in body)
conn.close()