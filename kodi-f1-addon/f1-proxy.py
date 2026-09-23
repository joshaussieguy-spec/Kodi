"""
F1 Stream Proxy Server v2
FIXED: Properly rewrites all playlist URLs to go through the proxy.
Runs on port 8888. All HTTP requests get the Referer header added automatically.

Usage:
  python3 f1-proxy.py

On your phone, open in VLC:
  http://YOUR_PC_IP:8888/q3zz9ru56f.m3u8

The proxy:
  1. Fetches the master m3u8 from obstreamx.click with Referer header
  2. Rewrites the sub-playlist URL (live/xxx.m3u8?hls=yyy) to /xxx.m3u8 (stripping /live/)
  3. When VLC requests /xxx.m3u8, the proxy fetches the sub-playlist with Referer
  4. Rewrites ALL .ts URLs to be absolute paths through the proxy
  5. When VLC requests a .ts, the proxy fetches it with Referer and streams it back
"""

import http.server
import urllib.parse
import socket
import requests
import re
import time

PORT = 8888
STREAM_BASE = 'https://obstreamx.click/live/'
REFERER = 'https://getembed.live/'
USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
UPSTREAM_HEADERS = {'User-Agent': USER_AGENT, 'Referer': REFERER}

# --- Stream key cache (hls_ctx tokens) ---
stream_cache = {}
stream_cache_time = {}

def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return "127.0.0.1"

def fetch_master_m3u8(stream_key):
    """Fetch master m3u8 and return the sub-playlist path (e.g. live/xxx.m3u8?hls_ctx=xxx)."""
    url = f"{STREAM_BASE}{stream_key}.m3u8"
    resp = requests.get(url, headers=UPSTREAM_HEADERS, timeout=15)
    lines = [l.strip() for l in resp.text.split('\n') if l.strip() and not l.startswith('#')]
    return lines[0] if lines else None

def fetch_sub_m3u8(sub_path):
    """Fetch sub-playlist and rewrite all .ts URLs to absolute paths through proxy."""
    url = f"https://obstreamx.click/{sub_path}"
    resp = requests.get(url, headers=UPSTREAM_HEADERS, timeout=15, stream=True)
    content = b''
    for chunk in resp.iter_content(chunk_size=65536):
        content += chunk
    
    text = content.decode('utf-8', errors='replace')
    lines = text.split('\n')
    rewritten = []
    
    for line in lines:
        stripped = line.strip()
        if stripped and not stripped.startswith('#'):
            # This is a URL — rewrite to go through proxy
            # The sub-playlist URL path is: live/xxx.ts?hls_ctx=yyy
            # We strip the /live/ prefix so it goes through proxy as: xxx.ts?hls_ctx=yyy
            # The proxy then strips xxx.ts? -> fetches from obstreamx.click/live/xxx.ts? with Referer
            new_path = stripped.lstrip('/')  # remove leading /
            # But strip 'live/' since the proxy adds it back
            if new_path.startswith('live/'):
                new_path = new_path[5:]
            rewritten.append(new_path)
        else:
            rewritten.append(line)
    
    return '\n'.join(rewritten)

def fetch_ts_segment(ts_path):
    """Fetch a .ts segment and return the bytes."""
    # ts_path is like: q3zz9ru56f-540.ts?hls_ctx=xxx
    # We need to fetch: https://obstreamx.click/live/q3zz9ru56f-540.ts?hls_ctx=xxx
    url = f"{STREAM_BASE}{ts_path}"
    resp = requests.get(url, headers=UPSTREAM_HEADERS, timeout=15, stream=True)
    if resp.status_code != 200:
        return None
    content = b''
    for chunk in resp.iter_content(chunk_size=65536):
        content += chunk
    return content

class ProxyHandler(http.server.BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        print(f"[proxy] {args[0]}")

    def do_GET(self):
        path = self.path
        local_ip = get_local_ip()

        # Landing page
        if path == '/' or path == '/index.html':
            self.send_response(200)
            self.send_header('Content-Type', 'text/html')
            self.end_headers()
            html = """<html><body style='background:#111;color:#fff;font-family:sans-serif;padding:20px'>
            <h1>🏎️ F1 Streams (LIVE)</h1>
            <p style='color:#0f0'>Tap a link below to open in VLC:</p>
            <ul>
            <li><a style='color:#0f0;font-size:20px' href='http://{}:{}//q3zz9ru56f.m3u8'>🏁 Austrian GP - Friday To Sunday</a></li>
            <li><a style='color:#0f0;font-size:20px' href='http://{}:{}//20iyfxolfv.m3u8'>🏁 Austrian GP - IT Channel F1</a></li>
            <li><a style='color:#0f0;font-size:20px' href='http://{}:{}//4f7xb2otg5.m3u8'>🏁 Dutch GP</a></li>
            </ul>
            <p style='color:#888;font-size:14px'>Or copy the URL and paste into VLC as network stream</p>
            </body></html>""".format(local_ip, PORT, local_ip, PORT, local_ip, PORT)
            self.wfile.write(html.encode())
            return

        # Strip leading /
        clean = path.lstrip('/')
        
        # Detect master m3u8 (stream keys only, like q3zz9ru56f.m3u8)
        # vs sub-playlist (.m3u8 with hls_ctx but no /live/) vs .ts segments
        if clean.endswith('.m3u8'):
            # Check if it has hls_ctx (it's a sub-playlist) or not (it's a master key)
            is_master = 'hls_ctx' not in clean
            
            if is_master:
                # Master playlist — rewrite sub-playlist path to strip /live/
                # e.g. /live/xxx.m3u8?hls_ctx=yyy -> xxx.m3u8?hls_ctx=yyy
                stream_key = clean.replace('.m3u8', '')
                try:
                    sub_path = fetch_master_m3u8(stream_key)
                    if not sub_path:
                        raise Exception("No sub playlist found")
                    
                    # Rewrite: strip /live/ prefix so proxy can handle it
                    rewritten_sub = sub_path.lstrip('/')
                    if rewritten_sub.startswith('live/'):
                        rewritten_sub = rewritten_sub[5:]
                    
                    # Return rewritten master playlist
                    content = f"#EXTM3U\n#EXT-X-STREAM-INF:BANDWIDTH=1\n{rewritten_sub}\n"
                    
                    self.send_response(200)
                    self.send_header('Content-Type', 'application/vnd.apple.mpegurl')
                    self.send_header('Content-Length', str(len(content)))
                    self.end_headers()
                    self.wfile.write(content.encode())
                    return
                    
                except Exception as e:
                    print(f"Master fetch error: {e}")
                    self.send_response(502)
                    self.end_headers()
                    self.wfile.write(f"Error: {e}".encode())
                    return
            else:
                # Sub-playlist — fetch from upstream with Referer and rewrite .ts URLs
                try:
                    # Reconstruct the full upstream path
                    upstream_sub_path = f"live/{clean}"
                    rewritten = fetch_sub_m3u8(upstream_sub_path)
                    
                    self.send_response(200)
                    self.send_header('Content-Type', 'application/vnd.apple.mpegurl')
                    self.send_header('Content-Length', str(len(rewritten)))
                    self.end_headers()
                    self.wfile.write(rewritten.encode())
                    return
                except Exception as e:
                    print(f"Sub playlist error: {e}")
                    self.send_response(502)
                    self.end_headers()
                    self.wfile.write(f"Error: {e}".encode())
                    return
        
        elif clean.endswith('.ts') or 'hls_ctx' in clean:
            # .ts segment
            ts_content = fetch_ts_segment(clean)
            if ts_content is None:
                self.send_response(404)
                self.end_headers()
                self.wfile.write(b'Not found')
                return
            
            self.send_response(200)
            self.send_header('Content-Type', 'video/mp2t')
            self.send_header('Content-Length', str(len(ts_content)))
            self.end_headers()
            self.wfile.write(ts_content)
            return
        
        else:
            # Fallback — try as-is with /live/ prefix
            upstream_url = f"{STREAM_BASE}{clean}"
            try:
                resp = requests.get(upstream_url, headers=UPSTREAM_HEADERS, timeout=15, stream=True)
                self.send_response(resp.status_code)
                self.send_header('Content-Type', resp.headers.get('Content-Type', 'application/octet-stream'))
                self.end_headers()
                for chunk in resp.iter_content(chunk_size=65536):
                    self.wfile.write(chunk)
            except Exception as e:
                self.send_response(502)
                self.end_headers()
                self.wfile.write(str(e).encode())

def main():
    local_ip = get_local_ip()
    server = http.server.HTTPServer(('0.0.0.0', PORT), ProxyHandler)
    print()
    print("=" * 55)
    print("  🏎️ F1 Stream Proxy — READY")
    print("=" * 55)
    print()
    print(f"  Your PC IP: {local_ip}")
    print(f"  Port: {PORT}")
    print()
    print("  On your Android phone, open VLC and enter:")
    print(f"  http://{local_ip}:{PORT}/q3zz9ru56f.m3u8")
    print()
    print("  Press Ctrl+C to stop")
    print()
    server.serve_forever()

if __name__ == '__main__':
    main()