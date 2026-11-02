import re, os, urllib.request, ssl

UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
ctx = ssl.create_default_context(); ctx.check_hostname = False; ctx.verify_mode = ssl.CERT_NONE

def fetch(url, ref='https://buffstreams24.org/'):
    req = urllib.request.Request(url, headers={'User-Agent': UA, 'Referer': ref,
                                               'Accept': 'text/html,*/*'})
    with urllib.request.urlopen(req, timeout=25, context=ctx) as r:
        return r.geturl(), r.read().decode('utf-8', 'replace')

# buffstreams: f1-streams4 is the "hub" (has no iframes) -> find the real per-stream page
redir, h = fetch('https://buffstreams24.org/f1-streams4')
print('hub bytes:', len(h))
# look for links with /streaming/ or /stream/ plus sky
cands = sorted(set(re.findall(r'href="(/(?:streaming|stream)/[^"]+)"', h)))
print('streaming links (%d):' % len(cands), cands[:15])
# also look for schedule/keys json or schedule links
sched = sorted(set(re.findall(r'href="([^"]*(?:schedule|keys|api)[^"]*)"', h, re.I)))
print('sched/api:', sched[:8])
m3 = re.findall(r'https?://[^"\'\s]+\.m3u8[^"\'\s]*', h)
print('literal m3u8:', m3[:5])