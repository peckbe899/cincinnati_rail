"""Shared helpers for the visual audit of the batch's block lines on cut plates (visual-cut, 21 Nov 2026).

Reads only. What Ben sees in the line editor is clean(N_edges.json) + sheet(N): both functions are copied here from
tools/sanborn/unet/edit_server.py:60-110 (unchanged), so that the audit pictures show exactly the editor's lines.
For plate 44 the batch refused the outline step, so its polygons come from this folder's out44/ (outlines_copy.py,
the outline step run on the batch's two maps 44_pred_area_ng1.png and 44_lines_lines_ng1.png).
"""
import json, os
import numpy as np
import cv2

SP = 'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn/'
U = SP + 'unet_data/'
HERE = os.path.dirname(os.path.abspath(__file__))


def load(n):
    """scan, polygons (outlines.json), exported lines (blocks_noguide step 4), editor lines, block mask, line map, alpha"""
    full = cv2.imread(SP + f'cufp/22-{n}.jpg'); H, W = full.shape[:2]
    if n == '44':
        polys = json.load(open(os.path.join(HERE, 'out44', '44_outlines_poly.json'))); bm = cv2.imread(os.path.join(HERE, 'out44', '44_blockmask.png'), 0)
    else:
        polys = json.load(open(SP + f'picks22_guided/22-{n}/outlines.json', encoding='utf8')); bm = cv2.imread(U + f'{n}_blockmask.png', 0)
    exp = [dict(src='read', name='', a=s['a'], b=s['b'], state='green' if s['state'] == 'on print' else 'orange', poly=i)
           for i, p in enumerate(polys) for s in p if s['state'] != 'short' and not s.get('paper_edge')]
    shown = clean(exp)
    sh = sheet(n, W, H)
    pl = cv2.imread(U + f'{n}_lines_lines_ng1.png', 0)
    pa = cv2.imread(U + f'{n}_pred_area_ng1.png', 0)
    alpha = cv2.resize(np.load(SP + f'cufp/{n}/png_alpha_s4.npy').astype(np.float32), (W, H)) > 0.5
    return dict(n=n, full=full, W=W, H=H, polys=polys, exp=exp, shown=shown, sheet=sh, bm=bm, pl=pl, pa=pa, alpha=alpha)


def sheet(n, W, H):
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
    """edit_server.clean, unchanged except that it also carries the set of source polygons of each joined line"""
    out = []; cosang = np.cos(np.radians(ang))
    for state in sorted({e['state'] for e in edges}):
        segs = sorted([e for e in edges if e['state'] == state], key=lambda e: -np.hypot(e['b'][0] - e['a'][0], e['b'][1] - e['a'][1])); tracks = []
        for e in segs:
            a, b = np.array(e['a'], float), np.array(e['b'], float); L = np.hypot(*(b - a))
            if L < 1: continue
            hit = None
            for t in tracks:
                d, p0 = t['d'], t['p']; nn = np.array([-d[1], d[0]])
                if abs(((b - a) / L) @ d) < cosang or abs((a - p0) @ nn) > off or abs((b - p0) @ nn) > off: continue
                lo, hi = sorted(((a - p0) @ d, (b - p0) @ d))
                if any(lo <= i1 + gap and hi >= i0 - gap for i0, i1 in t['iv']): hit = (t, lo, hi); break
            if hit: hit[0]['iv'].append((hit[1], hit[2])); hit[0]['src'].add(e['src']); hit[0]['polys'].append((hit[1], hit[2], e.get('poly')))
            else: tracks.append(dict(d=(b - a) / L, p=a, iv=[(0.0, L)], src={e['src']}, polys=[(0.0, L, e.get('poly'))]))
        for t in tracks:
            iv = sorted(t['iv']); runs = [list(iv[0])]
            for i0, i1 in iv[1:]:
                if i0 <= runs[-1][1] + gap: runs[-1][1] = max(runs[-1][1], i1)
                else: runs.append([i0, i1])
            for i0, i1 in runs:
                if i1 - i0 >= 12:
                    ps = sorted({p for lo, hi, p in t['polys'] if lo >= i0 - 1 and hi <= i1 + 1 and p is not None})
                    out.append(dict(src='read', state=state, name='', a=(t['p'] + t['d'] * i0).round(1).tolist(), b=(t['p'] + t['d'] * i1).round(1).tolist(), polys=ps))
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


def poly_rings(polys):
    """each polygon's ring of side end points (all sides, short ones included), for area and centroid"""
    out = []
    for p in polys:
        pts = []
        for s in p: pts += [s['a'], s['b']]
        out.append(np.array(pts, np.float32))
    return out


def draw(D, x0, y0, w, h, scale, grid=None, labels=True, show_mask=True, show_dropped=True, marks=(), extra=()):
    """overlay of the window (x0, y0, w, h) in full-size px, returned at `scale`"""
    full = D['full']; H, W = D['H'], D['W']
    x0, y0 = max(0, int(x0)), max(0, int(y0)); x1, y1 = min(W, int(x0 + w)), min(H, int(y0 + h))
    im = full[y0:y1, x0:x1].astype(np.float32) * 0.8 + 50
    if show_mask:
        bm = cv2.resize(D['bm'], (W, H), interpolation=cv2.INTER_NEAREST)[y0:y1, x0:x1] > 127
        tint = np.array([255, 200, 120], np.float32)   # BGR light blue over the ground called block
        im[bm] = im[bm] * 0.72 + tint * 0.28
    im = cv2.resize(im.clip(0, 255).astype(np.uint8), None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
    P = lambda q: (int(round((q[0] - x0) * scale)), int(round((q[1] - y0) * scale)))
    th = max(2, int(round(5 * scale ** 0.5)))
    if show_dropped:
        for i, p in enumerate(D['polys']):
            for s in p:
                if s['state'] == 'short': cv2.line(im, P(s['a']), P(s['b']), (90, 90, 90), max(1, th // 2), cv2.LINE_AA)
                elif s.get('paper_edge'): cv2.line(im, P(s['a']), P(s['b']), (200, 200, 0), max(1, th // 2), cv2.LINE_AA)
    for s in D['sheet']: cv2.line(im, P(s['a']), P(s['b']), (220, 220, 0), max(1, th // 2), cv2.LINE_AA)
    for a, b, col, t in extra: cv2.line(im, P(a), P(b), col, max(1, int(t)), cv2.LINE_AA)   # e.g. Ben's lines on 44, drawn under the editor lines
    ends = []
    for s in D['shown']:
        col = (0, 160, 0) if s['state'] == 'green' else (0, 140, 255)
        cv2.line(im, P(s['a']), P(s['b']), col, th, cv2.LINE_AA); ends += [s['a'], s['b']]
    # an end of an editor line with no other editor line end within 25 px: a corner left open (red dot)
    E = np.array(ends, float)
    if len(E):
        from scipy.spatial import cKDTree
        t = cKDTree(E); cnt = np.array([len(t.query_ball_point(e, 25.0)) for e in E])
        for e, c in zip(E, cnt):
            if c < 2: cv2.circle(im, P(e), max(3, th), (0, 0, 230), -1, cv2.LINE_AA)
    if labels:
        for i, r in enumerate(poly_rings(D['polys'])):
            if not len(r): continue
            c = r.mean(0)
            if x0 <= c[0] < x1 and y0 <= c[1] < y1:
                cv2.putText(im, str(i), P(c), cv2.FONT_HERSHEY_SIMPLEX, max(0.5, 1.4 * scale ** 0.5), (0, 0, 200), max(1, th // 2), cv2.LINE_AA)
    if grid:
        for gx in range((x0 // grid + 1) * grid, x1, grid):
            cv2.line(im, P((gx, y0)), P((gx, y1)), (160, 0, 160), 1)
            cv2.putText(im, str(gx), P((gx + 10, y0 + 120 / scale ** 0)), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (160, 0, 160), 2)
        for gy in range((y0 // grid + 1) * grid, y1, grid):
            cv2.line(im, P((x0, gy)), P((x1, gy)), (160, 0, 160), 1)
            cv2.putText(im, str(gy), P((x0 + 10, gy - 10)), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (160, 0, 160), 2)
    for m in marks:   # (x, y, text): an audit note, a magenta ring with its label (white halo so it reads on any ground)
        r = int(40 * scale) + 10; c = P(m[:2]); cv2.circle(im, c, r, (255, 255, 255), 6, cv2.LINE_AA); cv2.circle(im, c, r, (200, 0, 200), 3, cv2.LINE_AA)
        org = (min(im.shape[1] - 10 - 11 * len(m[2]), c[0] + r + 6), max(20, c[1] + 6))
        cv2.putText(im, m[2], org, cv2.FONT_HERSHEY_SIMPLEX, 0.62, (255, 255, 255), 5, cv2.LINE_AA); cv2.putText(im, m[2], org, cv2.FONT_HERSHEY_SIMPLEX, 0.62, (160, 0, 160), 2, cv2.LINE_AA)
    return im
