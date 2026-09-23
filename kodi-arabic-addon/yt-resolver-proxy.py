#!/usr/bin/env python3
"""
YouTube Resolver Proxy for Kodi Arabic Shows addon.
Runs on the home server (this PC) and resolves YouTube video IDs to direct stream URLs
using yt-dlp. The Kodi addon calls this proxy since it can't run yt-dlp itself.

Usage: python3 yt-resolver-proxy.py [port]
Default port: 9999
"""

import http.server
import json
import subprocess
import sys
import urllib.parse
import re

PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 9999

class ResolverHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        params = urllib.parse.parse_qs(parsed.query)
        
        if parsed.path == '/resolve':
            video_id = params.get('v', [''])[0]
            if not video_id:
                self.send_error(400, 'Missing video ID')
                return
            
            try:
                # Use yt-dlp to get the direct stream URL
                cmd = [
                    sys.executable, '-m', 'yt_dlp',
                    '-f', 'best[ext=mp4]/best[ext=mp4]/best',
                    '-g', '--no-warnings',
                    f'https://www.youtube.com/watch?v={video_id}'
                ]
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
                
                if result.returncode != 0:
                    # Try with no format filter
                    cmd2 = [
                        sys.executable, '-m', 'yt_dlp',
                        '-g', '--no-warnings',
                        f'https://www.youtube.com/watch?v={video_id}'
                    ]
                    result = subprocess.run(cmd2, capture_output=True, text=True, timeout=30)
                
                urls = [u.strip() for u in result.stdout.strip().split('\n') if u.strip() and u.strip().startswith('http')]
                
                if urls:
                    # Return first URL (video) — if there's a second, it's audio
                    response = json.dumps({
                        'url': urls[0],
                        'audio_url': urls[1] if len(urls) > 1 else None,
                        'video_id': video_id
                    })
                    self.send_response(200)
                    self.send_header('Content-Type', 'application/json')
                    self.send_header('Access-Control-Allow-Origin', '*')
                    self.end_headers()
                    self.wfile.write(response.encode())
                else:
                    self.send_response(404)
                    self.send_header('Content-Type', 'application/json')
                    self.send_header('Access-Control-Allow-Origin', '*')
                    self.end_headers()
                    json.dumps({'error': 'No URL found', 'stderr': result.stderr[:500]}).encode()
                    self.wfile.write(json.dumps({'error': 'No URL found', 'stderr': result.stderr[:500]}).encode())
            except subprocess.TimeoutExpired:
                self.send_response(504)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(json.dumps({'error': 'Timeout'}).encode())
            except Exception as e:
                self.send_response(500)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(json.dumps({'error': str(e)}).encode())
        
        elif parsed.path == '/health':
            self.send_response(200)
            self.send_header('Content-Type', 'text/plain')
            self.end_headers()
            self.wfile.write(b'OK')
        
        elif parsed.path == '/' or parsed.path == '/index.html':
            self.send_response(200)
            self.send_header('Content-Type', 'text/html')
            self.end_headers()
            html = b'<html><body><h1>YouTube Resolver Proxy</h1><p>Use /resolve?v=VIDEO_ID to resolve</p></body></html>'
            self.wfile.write(html)
        else:
            self.send_error(404, 'Not found')
    
    def log_message(self, format, *args):
        # Suppress request logs
        pass

if __name__ == '__main__':
    server = http.server.HTTPServer(('0.0.0.0', PORT), ResolverHandler)
    print(f'YouTube Resolver Proxy running on port {PORT}')
    print(f'Resolve: http://localhost:{PORT}/resolve?v=VIDEO_ID')
    print(f'Health: http://localhost:{PORT}/health')
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print('\nShutting down...')
        server.shutdown()