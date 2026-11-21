"""Map ground of an uncut 1922 Sanborn sheet (Atlas of Cincinnati, vols. 1-2, sheets taken whole from the PDFs).

    import map_area
    mask = map_area.map_mask(scan_bgr)                       # full-size bool (H, W): True = map ground
    info = map_area.map_area(scan_bgr, alpha_s4=None)        # everything: masks, polygons, excluded boxes, frames, regions

    python map_area.py N [N ...] [--out DIR]                 # writes DIR/N_map_area.json and DIR/N_map_area.jpg (default DIR:
                                                             # this file's folder/maparea_out); never writes anywhere else

What it finds, all on the CPU in about 5-8 s per sheet:
- paper: the cream sheet against the dark scanner bed (or the given cufp/N/png_alpha_s4.npy, quarter size);
- the printed furniture, by template matching on the quarter-size scan (templates/, cut by make_templates.py):
  KEY box, title line 'ATLAS OF CINCINNATI, O.' (with the plate number under it), the hand-lettered 'SCALE n FT. TO AN
  INCH' notes, the scale bars with their copyright line, and the compass rose (24 rotations) with its long arrow;
- heavy frame lines: the thick black rules that box an inset or split a sheet into panels (long, 3-9 quarter px thick);
- map ground: the 1922 sheets have NO neat line (checked on all 32 PDF sheets): the drawing simply stops and blank paper
  runs to the edge. So the map is taken as the ground enclosed by the printed ink: ink at 1/8 size (furniture removed),
  closed with a disk of R_CLOSE, holes filled, eroded back. Blank paper that reaches the sheet edge through a gap wider than
  2 * R_CLOSE (margin, river beyond the shore, open land the surveyor left unbounded) is off-map.
The returned 'mask' is map ground minus the furniture boxes and minus the frame lines (so an inset is its own island).

Not ground truth. Every sheet's result was checked by eye on an overlay (test_map_area.py, maparea_check/). Written for the
bench of 21 Nov 2026 (bench_2026-11-21/visual-pdf); outlines.py is not changed here.
"""
import json, os, sys, time
import numpy as np
import cv2

HERE = os.path.dirname(os.path.abspath(__file__))
TDIR = os.path.join(HERE, 'templates')
R_CLOSE = 30          # closing radius at 1/8 size (= 240 full px; at 200 ft/in about 160 ft, at 400 ft/in about 320 ft)
EDGE_BAND = 10        # ink within this many 1/8 px of the paper edge is ignored (paper edge shadow, page tab), = 80 full px
BLUR = 1.0            # Gaussian sigma applied to image and templates before matching (quarter px)
ROSE_THR = 0.65       # a second compass rose (an inset's own) must score this much
_T = {}


def _tpl():
    if not _T:
        for k in ('key', 'title', 'bar200', 'bar400', 'bar400b', 'note200a', 'note200b', 'note400a', 'rose'):
            p = os.path.join(TDIR, f'{k}.png')
            if os.path.exists(p):
                _T[k] = cv2.GaussianBlur(cv2.imread(p, 0), (0, 0), BLUR).astype(np.float32)
    return _T


def _paper(q):
    """quarter-size BGR -> paper mask (bool): the bright sheet against the dark scanner bed"""
    v = cv2.GaussianBlur(cv2.cvtColor(q, cv2.COLOR_BGR2HSV)[:, :, 2], (0, 0), 2)
    b = (v > 130).astype(np.uint8)
    b = cv2.morphologyEx(b, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (15, 15)))
    n, cc, st, _ = cv2.connectedComponentsWithStats(b, connectivity=4)
    if n < 2: return b > 0
    k = 1 + int(np.argmax(st[1:, cv2.CC_STAT_AREA])); p = (cc == k).astype(np.uint8)
    ff = p.copy(); h, w = p.shape; m = np.zeros((h + 2, w + 2), np.uint8)
    cv2.floodFill(ff, m, (0, 0), 1)                     # fill holes (dark ink inside the paper)
    return (p | (1 - ff)) > 0


def _peaks(g, t, thr, k, scales=(0.98, 1.0, 1.02), region=None):
    """template peaks: list of (score, x0, y0, x1, y1) at quarter px; up to k per scale above thr, region=(x0,y0,x1,y1)"""
    out = []; ox = oy = 0
    if region is not None:
        x0, y0, x1, y1 = [int(round(v)) for v in region]; g = g[y0:y1, x0:x1]; ox, oy = x0, y0
    for s in scales:
        ts = cv2.resize(t, None, fx=s, fy=s, interpolation=cv2.INTER_AREA) if s != 1.0 else t
        if ts.shape[0] >= g.shape[0] or ts.shape[1] >= g.shape[1]: continue
        r = _ncc(g, ts); th, tw = ts.shape
        for _ in range(k):
            _, mx, _, (x, y) = cv2.minMaxLoc(r)
            if mx < thr: break
            out.append((float(mx), x + ox, y + oy, x + ox + tw, y + oy + th))
            r[max(0, y - th // 2):y + th // 2 + 1, max(0, x - tw // 2):x + tw // 2 + 1] = -1
    return _nms(out)


_SD = {}


def _ncc(g, t, min_std=4.0):
    """normalised cross-correlation, set to -1 where the image patch is nearly flat (NCC is unstable there) or where the
    template window leaves the paper's interior (the paper's edge shadow matched the notes' underline: false 'scale notes'
    along the top edge). _SD caches the per-window std and inside test by image and template size."""
    r = cv2.matchTemplate(g, t, cv2.TM_CCOEFF_NORMED); th, tw = t.shape
    key = (id(g), th, tw)
    if key not in _SD:
        if len(_SD) > 64: _SD.clear()
        m1 = cv2.boxFilter(g, -1, (tw, th), normalize=True, borderType=cv2.BORDER_REPLICATE)
        m2 = cv2.boxFilter(g * g, -1, (tw, th), normalize=True, borderType=cv2.BORDER_REPLICATE)
        sd = np.sqrt(np.maximum(m2 - m1 * m1, 0))[th // 2:th // 2 + r.shape[0], tw // 2:tw // 2 + r.shape[1]]
        bad = sd < min_std
        if _INNER.get(id(g)) is not None:
            cov = cv2.boxFilter(_INNER[id(g)], -1, (tw, th), normalize=True, borderType=cv2.BORDER_CONSTANT)[th // 2:th // 2 + r.shape[0], tw // 2:tw // 2 + r.shape[1]]
            bad |= cov < 0.999
        _SD[key] = bad
    r[_SD[key]] = -1
    return r


_INNER = {}


def _nms(c, iou=0.2):
    c = sorted(c, key=lambda z: -z[0]); keep = []
    for z in c:
        ok = True
        for y in keep:
            ix = max(0, min(z[3], y[3]) - max(z[1], y[1])); iy = max(0, min(z[4], y[4]) - max(z[2], y[2])); inter = ix * iy
            a = (z[3] - z[1]) * (z[4] - z[2]); b = (y[3] - y[1]) * (y[4] - y[2])
            if inter > iou * min(a, b): ok = False; break
        if ok: keep.append(z)
    return keep


def _roses(g, dark):
    """compass roses: max over 24 rotations of the rose core's match; every peak >= ROSE_THR (some sheets have one for the
    main map and one for an inset), the best one always if >= 0.5. True roses scored 0.74-1.0 on 19, 30, 46, 48 and 92,
    the best non-rose 0.59."""
    t = _tpl().get('rose')
    if t is None: return []
    c = (t.shape[1] / 2, t.shape[0] / 2); R = None
    for a in range(0, 360, 15):
        M = cv2.getRotationMatrix2D(c, a, 1.0); tr = cv2.warpAffine(t, M, (t.shape[1], t.shape[0]), borderMode=cv2.BORDER_REPLICATE)[15:-15, 15:-15]
        r = _ncc(g, tr); R = r if R is None else np.maximum(R, r)
    out = []; off = (t.shape[1] - 30) / 2
    for k in range(4):
        _, mx, _, (x, y) = cv2.minMaxLoc(R)
        if mx < (0.5 if k == 0 else ROSE_THR): break
        out.append(_arrow(float(mx), x + off, y + off, dark)); R[max(0, y - 60):y + 60, max(0, x - 60):x + 60] = -1
    if not out: out.append(dict(score=round(float(R.max()), 3), found=False))
    return out


def _arrow(sc, cx, cy, dark):
    """the rose's long arrow: the darkest straight line through its centre"""
    h, w = dark.shape; bestd = (-1, 0)
    for ang in np.arange(0, 180, 2.0):
        d = np.array([np.cos(np.radians(ang)), np.sin(np.radians(ang))]); tot = 0.0
        for sgn in (-1, 1):
            rr = np.arange(40, 125); xs = np.clip((cx + sgn * rr * d[0]).astype(int), 0, w - 1); ys = np.clip((cy + sgn * rr * d[1]).astype(int), 0, h - 1)
            tot += dark[ys, xs].mean()
        if tot > bestd[0]: bestd = (tot, ang)
    ang = bestd[1]; d = np.array([np.cos(np.radians(ang)), np.sin(np.radians(ang))]); nrm = np.array([-d[1], d[0]])
    L, Wd = 135, 12                                   # arrow half length and half width, quarter px
    poly = np.array([[cx, cy] + sgn_l * L * d + sgn_w * Wd * nrm for sgn_l, sgn_w in ((-1, -1), (1, -1), (1, 1), (-1, 1))])
    return dict(score=round(sc, 3), found=True, centre=(cx, cy), radius=48, arrow_angle_deg=float(ang), arrow_strength=round(bestd[0] / 2, 3), arrow_poly=poly)


def _frames(dark, paper):
    """heavy frame lines (inset boxes, panel splits): dark strokes 3-9.5 quarter px thick and >= 200 quarter px long"""
    d = (dark & paper).astype(np.uint8)
    thick = cv2.morphologyEx(d, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
    n, cc, st, _ = cv2.connectedComponentsWithStats(thick, connectivity=8); out = np.zeros_like(d); segs = []
    for i in range(1, n):
        x, y, w, h, a = st[i]
        if max(w, h) < 150 or a < 300: continue
        comp = (cc[y:y + h, x:x + w] == i).astype(np.uint8)
        dt = cv2.distanceTransform(cv2.copyMakeBorder(comp, 1, 1, 1, 1, cv2.BORDER_CONSTANT, value=0), cv2.DIST_L2, 3)[1:-1, 1:-1]
        th = 2 * float(np.percentile(dt[comp > 0], 90)); length = a / max(th, 1.0)
        fill = a / float(w * h)
        if th <= 9.5 and length >= 200 and fill < 0.35:
            out[y:y + h, x:x + w][comp > 0] = 1; segs.append(dict(bbox=[int(x), int(y), int(x + w), int(y + h)], thick=round(th, 1), length=round(length)))
    return out > 0, segs


def map_area(scan, alpha_s4=None, r_close=R_CLOSE):
    """scan: full-size BGR uint8 (cufp/22-N.jpg). alpha_s4: optional quarter-size paper mask (cufp/N/png_alpha_s4.npy).
    Returns dict: mask (full-size bool), mask8 (1/8 bool), polygons (full px rings), excluded (furniture boxes, full px),
    frames (list), regions (map islands after cutting frames), shares and flags."""
    t0 = time.time(); H, W = scan.shape[:2]; qs = (W // 4, H // 4)
    q = cv2.resize(scan, qs, interpolation=cv2.INTER_AREA)
    hsv = cv2.cvtColor(q, cv2.COLOR_BGR2HSV); hh, ss, vv = hsv[:, :, 0].astype(int), hsv[:, :, 1].astype(int), hsv[:, :, 2].astype(int)
    paper = (cv2.resize(alpha_s4.astype(np.uint8), qs, interpolation=cv2.INTER_NEAREST) > 0) if alpha_s4 is not None else _paper(q)
    gray = cv2.cvtColor(q, cv2.COLOR_BGR2GRAY)
    g = cv2.GaussianBlur(np.where(paper, gray, 215).astype(np.uint8), (0, 0), BLUR).astype(np.float32)
    dark = (vv < 150) & paper
    _SD.clear(); _INNER.clear()
    _INNER[id(g)] = cv2.erode(paper.astype(np.uint8), np.ones((9, 9), np.uint8)).astype(np.float32)   # 4 quarter px in from the paper edge (19: its scale note ends 10 px from it)
    colour = (((hh < 10) | (hh > 35)) & (ss > 60) & (vv < 235)) | (ss > 115)
    ink = (dark | colour) & paper
    T = _tpl(); excl = []; flags = []
    py, px = np.nonzero(paper); bx0, bx1, by0, by1 = px.min(), px.max(), py.min(), py.max(); pw, ph = bx1 - bx0, by1 - by0
    # KEY: the best peak anywhere (one per sheet)
    k = _peaks(g, T['key'], 0.28, 1)
    if k: excl.append(dict(kind='key', score=round(k[0][0], 3), box=list(k[0][1:]), pad=12))
    else: flags.append('no KEY found')
    # title line 'ATLAS OF CINCINNATI, O.' in the top right; the box takes in 'VOL. n' and the plate number below it
    k = _peaks(g, T['title'], 0.35, 1, region=(bx0 + 0.65 * pw, by0, bx1, by0 + 0.15 * ph))
    if k:
        s_, x0, y0, x1, y1 = k[0]; excl.append(dict(kind='title', score=round(s_, 3), box=[x0 - 15, y0 - 15, min(bx1, x1 + 65), y1 + 70], pad=6))
    else: flags.append('no title found')
    # scale notes: best of the three lettering templates, then any further peak >= 0.62 (an inset's own note; lot text scored 0.55)
    notes = []
    for name in ('note200a', 'note200b', 'note400a'):
        if name in T: notes += [z + (name,) for z in _peaks(g, T[name], 0.40, 3)]
    notes = sorted(notes, key=lambda z: -z[0]); kept = []
    for z in notes:
        if any(min(z[3], y[3]) - max(z[1], y[1]) > 0 and min(z[4], y[4]) - max(z[2], y[2]) > 0 for y in kept): continue
        if not kept or z[0] >= 0.62: kept.append(z)
    for z in kept: excl.append(dict(kind='scale_note', score=round(z[0], 3), box=list(z[1:5]), template=z[5], pad=6))
    # scale bars with the copyright line: best peak, then any further peak >= 0.7 (an inset's own bar; a heavy frame line scored 0.6)
    bars = []
    for name in ('bar200', 'bar400', 'bar400b'):
        if name in T: bars += [z + (name,) for z in _peaks(g, T[name], 0.40, 3)]
    bars = sorted(bars, key=lambda z: -z[0]); kept = []
    for z in bars:
        if any(min(z[3], y[3]) - max(z[1], y[1]) > 0 and min(z[4], y[4]) - max(z[2], y[2]) > 0 for y in kept): continue
        if not kept or z[0] >= 0.7: kept.append(z)
    for z in kept: excl.append(dict(kind='scale_bar', score=round(z[0], 3), box=list(z[1:5]), template=z[5], pad=10))
    if not kept: flags.append('no scale bar found')
    roses = _roses(g, dark.astype(np.float32))
    # furniture mask at quarter size
    fm = np.zeros(paper.shape, np.uint8)
    for e in excl:
        x0, y0, x1, y1 = [int(round(v)) for v in e['box']]; p = e['pad']
        cv2.rectangle(fm, (x0 - p, y0 - p), (x1 + p, y1 + p), 1, -1)
    for rose in roses:
        if not rose.get('found'): flags.append(f"no compass rose (best {rose['score']})"); continue
        cx, cy = rose['centre']; cv2.circle(fm, (int(cx), int(cy)), rose['radius'], 1, -1)
        cv2.fillPoly(fm, [rose['arrow_poly'].round().astype(np.int32)], 1)
        x0, y0 = rose['arrow_poly'].min(0); x1, y1 = rose['arrow_poly'].max(0)
        excl.append(dict(kind='compass_rose', score=rose['score'], box=[float(min(x0, cx - 48)), float(min(y0, cy - 48)), float(max(x1, cx + 48)), float(max(y1, cy + 48))],
                         poly=(rose['arrow_poly'] * 4).round(1).tolist(), arrow_angle_deg=rose['arrow_angle_deg'], pad=0))
    # frames from all dark ink except the furniture boxes (a frame often runs through a rose's arrow, so roses stay in)
    kb = np.zeros(paper.shape, bool)
    for e in excl:
        if e['kind'] != 'compass_rose':
            x0, y0, x1, y1 = [int(round(v)) for v in e['box']]; kb[max(0, y0 - 8):y1 + 8, max(0, x0 - 8):x1 + 8] = True
    fr, segs = _frames(dark & ~kb, paper)
    # map ground at 1/8: ink (minus furniture, minus the paper's edge band) closed, holes filled, eroded back
    e8 = (qs[0] // 2, qs[1] // 2)
    ink8 = cv2.resize((ink & (fm == 0)).astype(np.uint8) * 255, e8, interpolation=cv2.INTER_AREA) > 20
    paper8 = cv2.resize(paper.astype(np.uint8), e8, interpolation=cv2.INTER_NEAREST) > 0
    inner8 = cv2.erode(paper8.astype(np.uint8), cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * EDGE_BAND + 1, 2 * EDGE_BAND + 1))) > 0
    ink8 &= inner8
    # small specks (stains, stray dots) do not anchor the map
    n, cc, st, _ = cv2.connectedComponentsWithStats(ink8.astype(np.uint8), connectivity=8)
    big = np.zeros(n, bool); big[1:] = (st[1:, cv2.CC_STAT_WIDTH] + st[1:, cv2.CC_STAT_HEIGHT]) >= 12; ink8 = big[cc]
    R = r_close; se = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * R + 1, 2 * R + 1))
    pad = R + 2; d = cv2.dilate(cv2.copyMakeBorder(ink8.astype(np.uint8), pad, pad, pad, pad, cv2.BORDER_CONSTANT, value=0), se)
    ff = d.copy(); m = np.zeros((ff.shape[0] + 2, ff.shape[1] + 2), np.uint8); cv2.floodFill(ff, m, (0, 0), 1)
    filled = d | (1 - ff)
    closed = cv2.erode(filled, se)[pad:-pad, pad:-pad] > 0
    mg = closed & paper8
    n, cc, st, _ = cv2.connectedComponentsWithStats(mg.astype(np.uint8), connectivity=4)
    keep = np.zeros(n, bool); keep[1:] = st[1:, cv2.CC_STAT_AREA] >= 0.01 * paper8.sum(); mg = keep[cc]
    # subtract furniture and frames (at 1/8: furniture as is, frames slightly widened)
    fm8 = cv2.resize(fm, e8, interpolation=cv2.INTER_NEAREST) > 0
    fr8 = cv2.dilate((cv2.resize(fr.astype(np.uint8) * 255, e8, interpolation=cv2.INTER_AREA) > 40).astype(np.uint8), np.ones((3, 3), np.uint8)) > 0
    mask8 = mg & ~fm8 & ~fr8
    # regions: islands of map ground after the frames are cut (main map, insets, panels)
    n, cc, st, cen = cv2.connectedComponentsWithStats(mask8.astype(np.uint8), connectivity=4); regions = []
    for i in range(1, n):
        if st[i, cv2.CC_STAT_AREA] < 0.002 * paper8.sum(): continue
        x, y, w, h, a = st[i]; regions.append(dict(id=len(regions), bbox=[int(x * 8), int(y * 8), int((x + w) * 8), int((y + h) * 8)], centroid=[round(float(cen[i][0] * 8)), round(float(cen[i][1] * 8))],
                                                   share_of_map=round(a / max(1, mask8.sum()), 3)))
    cs, hier = cv2.findContours(mask8.astype(np.uint8), cv2.RETR_CCOMP, cv2.CHAIN_APPROX_SIMPLE); polys = []
    if hier is not None:
        for c, hr in zip(cs, hier[0]):
            if cv2.contourArea(c) < 50: continue
            ap = cv2.approxPolyDP(c, 1.5, True)[:, 0, :] * 8 + 4
            polys.append(dict(hole=bool(hr[3] >= 0), ring=ap.tolist()))
    mask = cv2.resize(mask8.astype(np.uint8), (W, H), interpolation=cv2.INTER_NEAREST) > 0
    for e in excl: e['box'] = [round(float(v) * 4, 1) for v in e['box']]; e['pad'] = e['pad'] * 4
    for s_ in segs: s_['bbox'] = [v * 4 for v in s_['bbox']]; s_['thick'] = s_['thick'] * 4; s_['length'] = s_['length'] * 4
    share = float(mask8.sum() / max(1, paper8.sum()))
    if share < 0.45: flags.append(f'map ground only {share:.2f} of the paper')
    if share > 0.97: flags.append(f'map ground {share:.2f} of the paper: margin not found')
    return dict(mask=mask, mask8=mask8, frames8=fr8, furniture8=fm8, paper8=paper8, polygons=polys, excluded=excl, frames=segs, regions=regions,
                paper_share_of_scan=round(float(paper.mean()), 3), map_share_of_paper=round(share, 3), flags=flags, seconds=round(time.time() - t0, 1))


def map_mask(scan, alpha_s4=None):
    """full-size bool mask of map ground (True) for a full-size BGR scan; off-map = margin, KEY, title, scale note/bar,
    compass rose, heavy inset frame lines"""
    return map_area(scan, alpha_s4)['mask']


def overlay(scan_or_q, r, scale=8):
    """1/scale picture: off-map greyed, map boundary green, furniture boxes magenta, frames red, region ids"""
    q = scan_or_q if scan_or_q.shape[1] < 4000 else cv2.resize(scan_or_q, None, fx=1 / scale, fy=1 / scale, interpolation=cv2.INTER_AREA)
    h, w = q.shape[:2]; m = cv2.resize(r['mask8'].astype(np.uint8), (w, h), interpolation=cv2.INTER_NEAREST) > 0
    v = q.astype(np.float32); v[~m] = v[~m] * 0.35 + 110
    v = v.clip(0, 255).astype(np.uint8)
    cs = cv2.findContours(m.astype(np.uint8), cv2.RETR_CCOMP, cv2.CHAIN_APPROX_SIMPLE)[0]
    cv2.drawContours(v, cs, -1, (0, 170, 0), 2)
    fr = cv2.resize(r['frames8'].astype(np.uint8), (w, h), interpolation=cv2.INTER_NEAREST) > 0; v[fr] = (0, 0, 230)
    for e in r['excluded']:
        x0, y0, x1, y1 = [int(round(c / scale)) for c in e['box']]
        col = dict(key=(200, 0, 200), title=(200, 0, 200), scale_note=(255, 120, 0), scale_bar=(255, 120, 0), compass_rose=(0, 140, 255))[e['kind']]
        cv2.rectangle(v, (x0, y0), (x1, y1), col, 2)
        if 'poly' in e: cv2.polylines(v, [(np.array(e['poly']) / scale).round().astype(np.int32)], True, col, 1)
    for g in r['regions']:
        cx, cy = [int(c / scale) for c in g['centroid']]
        cv2.putText(v, f"r{g['id']} {g['share_of_map']:.2f}", (cx - 30, cy), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 110, 0), 2)
    return v


if __name__ == '__main__':
    D = 'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn/'
    args = sys.argv[1:]; out = os.path.join(HERE, 'maparea_out')
    if '--out' in args: i = args.index('--out'); out = args[i + 1]; del args[i:i + 2]
    os.makedirs(out, exist_ok=True)
    for n in args:
        scan = cv2.imread(D + f'cufp/22-{n}.jpg'); ap = D + f'cufp/{n}/png_alpha_s4.npy'
        r = map_area(scan, np.load(ap) if os.path.exists(ap) else None)
        rec = {k: v for k, v in r.items() if k not in ('mask', 'mask8', 'frames8', 'furniture8', 'paper8')}
        rec.update(plate=n, size=[scan.shape[1], scan.shape[0]])
        json.dump(rec, open(os.path.join(out, f'{n}_map_area.json'), 'w'), indent=1, default=float)
        cv2.imwrite(os.path.join(out, f'{n}_map_area.jpg'), overlay(scan, r), [cv2.IMWRITE_JPEG_QUALITY, 80])
        print(n, r['map_share_of_paper'], r['flags'], f"{r['seconds']} s", flush=True)
