"""The line editor: Ben marks up a plate's street edges himself (15 November 2026).

    python tools/sanborn/unet/edit_server.py [PORT]          (default 8770; then open http://localhost:8770)

Ben, 15 November 2026: "you need to invent a way for me to edit these lines, because some are correct and some are not
and I cannot markup your current versions." And: "the edges of the sheets themselves are almost always streets."
The page (edit_page.html) shows a plate's scan at full size (tiles cut here on demand) with every edge of its label
(unet_data/N_edges.json, edges.py) and the outline of the sheet itself. Each line can be marked correct, wrong, or
"street side with no printed line" (the sheet's edge); its ends can be dragged; new lines can be drawn. Every change is
saved at once to picks22_guided/22-N/edges_ben.json (only the lines Ben touched, each with its original position), which
make_labels.py reads.
  GET  /                    the page
  GET  /plates              the plates that have an edges file
  GET  /data/N              size, edges, sheet outline, and what Ben has saved
  GET  /tile/N/Z/X/Y.jpg    a 512 px tile of the scan at 1 / 2^Z
  POST /save/N              write edges_ben.json
"""
import json, os, re, sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import numpy as np
import cv2
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(HERE, '..'))
import _ws  # noqa: E402
SP = _ws.DATA; U = SP + 'unet_data/'; T = 512; CACHE = {}

def scan(n, z):
    if CACHE.get('n') != n:
        CACHE.clear(); CACHE['n'] = n; CACHE[0] = cv2.imread(SP + f'cufp/22-{n}.jpg')
    if z not in CACHE:
        prev = scan(n, z - 1); CACHE[z] = cv2.resize(prev, (max(1, prev.shape[1] // 2), max(1, prev.shape[0] // 2)), interpolation=cv2.INTER_AREA)
    return CACHE[z]

def sheet(n, W, H):
    """the sheet's own outline as straight pieces (full-size px): the trimmed paper edge, almost always a street side"""
    a = np.load(SP + f'cufp/{n}/png_alpha_s4.npy').astype(np.float32); m = (a > 0.5).astype(np.uint8)
    sx, sy = W / m.shape[1], H / m.shape[0]; out = []
    for c in cv2.findContours(m, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)[0]:
        if cv2.contourArea(c) < 500: continue
        p = cv2.approxPolyDP(c, 2.0, True)[:, 0, :].astype(float) * [sx, sy]
        for k in range(len(p)):
            q0, q1 = p[k], p[(k + 1) % len(p)]
            if np.hypot(*(q1 - q0)) >= 40: out.append(dict(src='sheet', state='sheet', a=q0.round(1).tolist(), b=q1.round(1).tolist()))
    return out

class Hd(BaseHTTPRequestHandler):
    def log_message(self, *a): pass
    def send(self, body, ctype, code=200):
        self.send_response(code); self.send_header('Content-Type', ctype); self.send_header('Content-Length', str(len(body))); self.send_header('Cache-Control', 'no-store' if 'json' in ctype or 'html' in ctype else 'max-age=3600'); self.end_headers(); self.wfile.write(body)
    def do_GET(self):
        p = self.path.split('?')[0]
        if p == '/': return self.send(open(os.path.join(HERE, 'edit_page.html'), 'rb').read(), 'text/html; charset=utf-8')
        if p == '/plates':
            pl = sorted(f[:-len('_edges.json')] for f in os.listdir(U) if f.endswith('_edges.json'))
            return self.send(json.dumps(pl).encode(), 'application/json')
        m = re.fullmatch(r'/data/([0-9A-Za-z]+)', p)
        if m:
            n = m.group(1); im = scan(n, 0); H, W = im.shape[:2]; bf = SP + f'picks22_guided/22-{n}/edges_ben.json'
            d = dict(plate=n, W=W, H=H, edges=json.load(open(U + f'{n}_edges.json', encoding='utf8')) + sheet(n, W, H), saved=json.load(open(bf, encoding='utf8')) if os.path.exists(bf) else None)
            return self.send(json.dumps(d).encode(), 'application/json')
        m = re.fullmatch(r'/tile/([0-9A-Za-z]+)/(\d)/(\d+)/(\d+)\.jpg', p)
        if m:
            n, z, x, y = m.group(1), *map(int, m.groups()[1:]); im = scan(n, z); t = im[y * T:(y + 1) * T, x * T:(x + 1) * T]
            if t.size == 0: return self.send(b'', 'text/plain', 404)
            return self.send(cv2.imencode('.jpg', t, [cv2.IMWRITE_JPEG_QUALITY, 88])[1].tobytes(), 'image/jpeg')
        self.send(b'not found', 'text/plain', 404)
    def do_POST(self):
        m = re.fullmatch(r'/save/([0-9A-Za-z]+)', self.path)
        if not m: return self.send(b'not found', 'text/plain', 404)
        d = json.loads(self.rfile.read(int(self.headers['Content-Length'])).decode('utf8')); n = m.group(1)
        os.makedirs(SP + f'picks22_guided/22-{n}', exist_ok=True); f = SP + f'picks22_guided/22-{n}/edges_ben.json'
        json.dump(d, open(f + '.tmp', 'w', encoding='utf8', newline='\n'), indent=1); os.replace(f + '.tmp', f)
        self.send(json.dumps(dict(ok=True, lines=len(d.get('lines', [])))).encode(), 'application/json')

if __name__ == '__main__':
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8770
    print(f'line editor on http://localhost:{port}', flush=True); ThreadingHTTPServer(('127.0.0.1', port), Hd).serve_forever()
