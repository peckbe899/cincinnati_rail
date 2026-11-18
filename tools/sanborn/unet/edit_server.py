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
  GET  /bins/N              the ink bins of the plate (unet_data/N_bins.json, ink_bins.py), or {} if there are none
  GET  /bintile/N/Z/X/Y.png?on=1,4,5   a 512 px see-through tile of the ink in those bins, each in its colour
"""
import json, os, re, sys, threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import numpy as np
import cv2
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(HERE, '..'))
import _ws  # noqa: E402
SP = _ws.DATA; U = SP + 'unet_data/'; T = 512; CACHE = {}; LOCK = threading.RLock()

def scan(n, z):
    """one plate's scan is held at a time; the lock stops two requests (a tile of the last plate, the data of the next)
    from clearing it under each other, which dropped the connection and left the page blank"""
    with LOCK: return _scan(n, z)

def _scan(n, z):
    if CACHE.get('n') != n:
        CACHE.clear(); CACHE['n'] = n; CACHE[0] = cv2.imread(SP + f'cufp/22-{n}.jpg')
    if z not in CACHE:
        prev = _scan(n, z - 1); CACHE[z] = cv2.resize(prev, (max(1, prev.shape[1] // 2), max(1, prev.shape[0] // 2)), interpolation=cv2.INTER_AREA)
    return CACHE[z]

BINS = {}

def bins(n, z):
    """the bin of every pixel (ink_bins.py) at 1 / 2^Z; a smaller level keeps a pixel if any of the four under it is ink"""
    with LOCK:
        key = (n, os.path.getmtime(U + f'{n}_bins.png'))   # a new run of ink_bins.py is picked up without a restart
        if BINS.get('n') != key:
            BINS.clear(); BINS['n'] = key; BINS[0] = cv2.imread(U + f'{n}_bins.png', 0)
            BINS['pal'] = np.zeros((256, 4), np.uint8)
            for k, v in json.load(open(U + f'{n}_bins.json', encoding='utf8'))['bins'].items(): BINS['pal'][int(k)] = [v['rgb'][2], v['rgb'][1], v['rgb'][0], 255]
        if z not in BINS:
            q = bins(n, z - 1)[0]; q = np.pad(q, ((0, q.shape[0] % 2), (0, q.shape[1] % 2)))
            BINS[z] = q.reshape(q.shape[0] // 2, 2, q.shape[1] // 2, 2).max(axis=(1, 3))
        return BINS[z], BINS['pal']

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

def clean(edges, ang=2.5, off=5.0, gap=25.0):
    """Ben, 15 November 2026: "why are there so many overlapping and broken lines? it's impossible to build like this."
    The label's edges are stored as working pieces: every street side cut into 120 px pieces, and the same side twice
    where today's block side and a reading both lie on it. Here they become one line per straight run: pieces of the
    same state that lie on one straight line (within `ang` degrees and `off` px) and touch, overlap or are within `gap`
    px of each other are joined into a single line from the first end to the last."""
    out = []; cosang = np.cos(np.radians(ang))
    for state in sorted({e['state'] for e in edges}):
        segs = sorted([e for e in edges if e['state'] == state], key=lambda e: -np.hypot(e['b'][0] - e['a'][0], e['b'][1] - e['a'][1])); tracks = []
        for e in segs:
            a, b = np.array(e['a'], float), np.array(e['b'], float); L = np.hypot(*(b - a))
            if L < 1: continue
            hit = None
            for t in tracks:
                d, p0 = t['d'], t['p']; n = np.array([-d[1], d[0]])
                if abs(((b - a) / L) @ d) < cosang or abs((a - p0) @ n) > off or abs((b - p0) @ n) > off: continue
                lo, hi = sorted(((a - p0) @ d, (b - p0) @ d))
                if any(lo <= i1 + gap and hi >= i0 - gap for i0, i1 in t['iv']): hit = (t, lo, hi); break
            if hit: hit[0]['iv'].append((hit[1], hit[2])); hit[0]['names'].add(e.get('name', '')); hit[0]['src'].add(e['src'])
            else: tracks.append(dict(d=(b - a) / L, p=a, iv=[(0.0, L)], names={e.get('name', '')}, src={e['src']}))
        for t in tracks:
            iv = sorted(t['iv']); runs = [list(iv[0])]
            for i0, i1 in iv[1:]:
                if i0 <= runs[-1][1] + gap: runs[-1][1] = max(runs[-1][1], i1)
                else: runs.append([i0, i1])
            nm = sorted(x for x in t['names'] if x and not x.startswith(('Junction', 'Street between')))
            for i0, i1 in runs:
                if i1 - i0 >= 12: out.append(dict(src='read' if 'read' in t['src'] else sorted(t['src'])[0], state=state, name=nm[0] if nm else '', a=(t['p'] + t['d'] * i0).round(1).tolist(), b=(t['p'] + t['d'] * i1).round(1).tolist()))
    # a line with no printed line under it (blue) or not settled (orange) that lies along a green one says nothing more: drop it
    G = [(np.array(o['a']), np.array(o['b'])) for o in out if o['state'] == 'green']; keep = []
    for o in out:
        if o['state'] in ('blue', 'orange', 'grey'):
            m = (np.array(o['a']) + np.array(o['b'])) / 2; dup = False
            for p0, p1 in G:
                d = p1 - p0; L = np.hypot(*d); t_ = ((m - p0) @ d) / L ** 2
                if 0 <= t_ <= 1 and abs((m - p0) @ np.array([-d[1], d[0]])) / L < off + 2 and abs((np.array(o['b']) - np.array(o['a'])) @ d) / (L * np.hypot(*(np.array(o['b']) - np.array(o['a'])))) > cosang: dup = True; break
            if dup: continue
        keep.append(o)
    return keep

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
            d = dict(plate=n, W=W, H=H, edges=clean(json.load(open(U + f'{n}_edges.json', encoding='utf8'))) + sheet(n, W, H), saved=json.load(open(bf, encoding='utf8')) if os.path.exists(bf) else None)
            return self.send(json.dumps(d).encode(), 'application/json')
        m = re.fullmatch(r'/bins/([0-9A-Za-z]+)', p)
        if m:
            bf = U + f'{m.group(1)}_bins.json'
            return self.send(open(bf, 'rb').read() if os.path.exists(bf) and os.path.exists(bf[:-4] + 'png') else b'{}', 'application/json')
        m = re.fullmatch(r'/bintile/([0-9A-Za-z]+)/(\d)/(\d+)/(\d+)\.png', p)
        if m:
            n, z, x, y = m.group(1), *map(int, m.groups()[1:]); cm, pal = bins(n, z); t = cm[y * T:(y + 1) * T, x * T:(x + 1) * T]
            if t.size == 0: return self.send(b'', 'text/plain', 404)
            q = self.path.split('on=')[1].split('&')[0] if 'on=' in self.path else ''; on = np.zeros(256, bool); on[[int(v) for v in q.split(',') if v.isdigit()]] = True; on[0] = False
            return self.send(cv2.imencode('.png', (pal * on[:, None])[t])[1].tobytes(), 'image/png')
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
