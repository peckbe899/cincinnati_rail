"""apply_fixes.py - apply truth-check/fixes.txt to copies of the held-out crops H1-H4 and of truth v2 T1-T7.
Reads text_v1/heldout/H#_mask.png, H#_words.json and text_v1/truth/T#_* (never writes there) and writes
text_v1/truth-check/heldout_fixed/ (H1-H4) and text_v1/truth-check/truth_v2_fixed/ (T1-T7): #_mask.png, #_words.json
(with a `truth_check` list of the fixes and new counts), crops.json (for score_text.py --truth), and fixes_log.txt
(pixels changed by each op, measured). Run from truth-check/scripts: python -B apply_fixes.py"""
import os, sys, json, math, shutil, copy
import numpy as np, cv2
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import tc

IDS = ['H1', 'H2', 'H3', 'H4', 'T1', 'T2', 'T3', 'T4', 'T6', 'T7']
FIXV2 = os.path.join(tc.KEY, 'truth_v2_fixed')                    # my fixed copy of truth v2 (text_v1/truth is not touched)


def outdir(c): return tc.FIXED if c.startswith('H') else FIXV2


def strip_mask(shape, off, pts, w):
    m = np.zeros(shape, np.uint8)
    q = np.round(np.array(pts, float).reshape(-1, 2) - off).astype(np.int32)
    for i in range(len(q) - 1): cv2.line(m, tuple(map(int, q[i])), tuple(map(int, q[i + 1])), 1, int(w))
    return m > 0


def straight_runs(ink, length, nang=72):
    """ink pixels on a straight run of at least `length` px in one of nang directions (opening with a 1 px line
    kernel after a 3x3 closing), cut back to the ink: the same idea as the truth builders' line rule"""
    u = cv2.morphologyEx(ink.astype(np.uint8), cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3)))
    out = np.zeros(ink.shape, bool); c = length // 2
    for i in range(nang):
        a = math.pi * i / nang; k = np.zeros((length, length), np.uint8)
        d = np.array([math.cos(a), math.sin(a)]) * (length - 1) / 2
        cv2.line(k, (int(round(c - d[0])), int(round(c - d[1]))), (int(round(c + d[0])), int(round(c + d[1]))), 1, 1)
        out |= cv2.morphologyEx(u, cv2.MORPH_OPEN, k) > 0
    return out & ink


def word_poly(x1, y1, x2, y2, h, pad=2):
    L = math.hypot(x2 - x1, y2 - y1)
    if L < 1e-6: u = np.array([1.0, 0.0])
    else: u = np.array([x2 - x1, y2 - y1]) / L
    v = np.array([-u[1], u[0]]); a = np.array([x1, y1], float) - u * pad; b = np.array([x2, y2], float) + u * pad
    hh = h / 2 + pad
    return [list(map(float, np.round(p, 1))) for p in (a - v * hh, b - v * hh, b + v * hh, a + v * hh)], math.degrees(math.atan2(y2 - y1, x2 - x1)), L


def main():
    os.makedirs(tc.FIXED, exist_ok=True); os.makedirs(FIXV2, exist_ok=True)
    crops = tc.crops_all()
    masks = {c: tc.truth(c) for c in IDS}; W = {c: tc.words(c) for c in IDS}
    for c in IDS: W[c]['truth_check'] = []
    log = []; nword = {c: 0 for c in IDS}
    for ln, line in enumerate(open(os.path.join(tc.KEY, 'fixes.txt'), encoding='utf8'), 1):
        line = line.rstrip('\n')
        if not line.strip() or line.startswith('#'): continue
        head, _, rest = line.partition('|'); f = head.split(); op, cid = f[0], f[1]
        x0, y0 = crops[cid]['win'][:2]; m = masks[cid]; off = np.array([x0, y0])
        rec = dict(op=op, line=ln, text=line)
        if op in ('STRIP', 'BOX', 'POLY'):
            if op == 'POLY':
                fr = [int(v) for v in f[2].split(',')]; to = int(f[3])
                pts = np.array([float(v) for v in f[4:]]).reshape(-1, 2) - off
                sel = np.zeros(m.shape, np.uint8); cv2.fillPoly(sel, [np.round(pts).astype(np.int32)], 1); sel = sel > 0
            elif op == 'STRIP':
                w = float(f[2]); fr = [int(v) for v in f[3].split(',')]; to = int(f[4]); pts = [float(v) for v in f[5:]]
                sel = strip_mask(m.shape, off, pts, w)
            else:
                fr = [int(v) for v in f[2].split(',')]; to = int(f[3]); a, b, cc, d = [int(v) for v in f[4:8]]
                sel = np.zeros(m.shape, bool); sel[max(0, b - y0):max(0, d - y0 + 1), max(0, a - x0):max(0, cc - x0 + 1)] = True
            ch = sel & np.isin(m, fr); n = int(ch.sum()); m[ch] = to
            rec.update(px=n, frm=fr, to=to, note=rest.strip())
            log.append(f'{cid} line {ln:3d}  {op:5s} {",".join(map(str, fr))}->{to}  {n:5d} px   {rest.strip()}')
        elif op == 'INK':
            # INK crop x y from to | note : in the 8-connected ink piece (any value > 0) whose bounding box starts at (x, y),
            # pixels of value `from` become `to` (for glyphs wholly inside a word box, touching no line, that were split)
            px, py = int(f[2]) - x0, int(f[3]) - y0; fr = [int(v) for v in f[4].split(',')]; to = int(f[5])
            n_, lab_, st_, _ = cv2.connectedComponentsWithStats((m > 0).astype(np.uint8), connectivity=8)
            hit = [i for i in range(1, n_) if st_[i][0] == px and st_[i][1] == py]
            if len(hit) != 1: raise SystemExit(f'line {ln}: INK {cid} {f[2]},{f[3]}: {len(hit)} pieces start there')
            ch = (lab_ == hit[0]) & np.isin(m, fr); n = int(ch.sum()); m[ch] = to
            rec.update(px=n, frm=fr, to=to, note=rest.strip())
            log.append(f'{cid} line {ln:3d}  INK   {",".join(map(str, fr))}->{to}  {n:5d} px   {rest.strip()}')
        elif op == 'PIECE':
            # PIECE crop x y to | note : the 8-connected piece of not-text ink (1) whose bounding box starts at (x, y)
            px, py, to = int(f[2]) - x0, int(f[3]) - y0, int(f[4])
            n_, lab_, st_, _ = cv2.connectedComponentsWithStats((m == 1).astype(np.uint8), connectivity=8)
            hit = [i for i in range(1, n_) if st_[i][0] == px and st_[i][1] == py]
            if len(hit) != 1: raise SystemExit(f'line {ln}: PIECE {cid} {f[2]},{f[3]}: {len(hit)} pieces start there')
            ch = lab_ == hit[0]; n = int(ch.sum()); m[ch] = to
            rec.update(px=n, frm=[1], to=to, note=rest.strip())
            log.append(f'{cid} line {ln:3d}  PIECE 1->{to}  {n:5d} px   {rest.strip()}')
        elif op == 'RELABEL':
            # RELABEL crop L x1 y1 x2 y2 x3 y3 ... | note : inside the polygon, ink on a straight run of L px or more is
            # not text (1), the rest of the ink is text (2), and run ink within 2 px of that text is don't care (3)
            L = int(f[2]); pts = np.array([float(v) for v in f[3:]]).reshape(-1, 2) - off
            poly = np.zeros(m.shape, np.uint8); cv2.fillPoly(poly, [np.round(pts).astype(np.int32)], 1); poly = poly > 0
            ink = m > 0; run = straight_runs(ink, L)
            txt = poly & ink & ~run; ln_ = poly & run
            near = cv2.dilate(txt.astype(np.uint8), np.ones((5, 5), np.uint8)) > 0
            new = m.copy(); new[txt] = 2; new[ln_] = 1; new[ln_ & near] = 3
            n = int((new != m).sum()); d = {f'{a}->{b}': int(((m == a) & (new == b)).sum()) for a in range(4) for b in range(4) if a != b and ((m == a) & (new == b)).any()}
            m[:] = new; rec.update(px=n, detail=d, note=rest.strip())
            log.append(f'{cid} line {ln:3d}  RELABEL L={L}  {n:5d} px {d}   {rest.strip()}')
        elif op == 'READ':
            wid = f[2]; new, note = [s.strip() for s in rest.split('|', 1)] if '|' in rest else (rest.strip(), '')
            for w in W[cid]['words']:
                if w['id'] == wid: rec.update(old=w['reading'], new=new, note=note); w['reading'] = new
            log.append(f'{cid} line {ln:3d}  READ  {wid}: {rec.get("old")!r} -> {new!r}   {note}')
        elif op == 'REBOX':
            # REBOX crop word_id x1 y1 x2 y2 h | note : replace a word's box by the typed centre line and height
            wid = f[2]; x1, y1, x2, y2, h = [float(v) for v in f[3:8]]
            poly, ang, L = word_poly(x1, y1, x2, y2, h); P = np.array(poly)
            for w in W[cid]['words']:
                if w['id'] == wid:
                    rec.update(word=wid, old_poly=w['poly'], note=rest.strip())
                    w.update(poly=poly, angle=round(ang, 1), height=h, length=round(L, 1),
                             aabb=[int(P[:, 0].min()), int(P[:, 1].min()), int(math.ceil(P[:, 0].max())), int(math.ceil(P[:, 1].max()))])
            log.append(f'{cid} line {ln:3d}  REBOX {wid}   {rest.strip()}')
        elif op == 'FLAG':
            wid, fl = f[2], f[3]
            for w in W[cid]['words']:
                if w['id'] == wid:
                    if fl[0] == '+' and fl[1:] not in w['flags']: w['flags'].append(fl[1:])
                    if fl[0] == '-' and fl[1:] in w['flags']: w['flags'].remove(fl[1:])
            rec.update(word=wid, flag=fl, note=rest.strip()); log.append(f'{cid} line {ln:3d}  FLAG  {wid} {fl}   {rest.strip()}')
        elif op == 'WORD':
            x1, y1, x2, y2, h = [float(v) for v in f[2:7]]
            parts = [s.strip() for s in rest.split('|')]; reading, kind = parts[0], parts[1]
            flags = parts[2].split() if len(parts) > 2 else []; note = parts[3] if len(parts) > 3 else ''
            poly, ang, L = word_poly(x1, y1, x2, y2, h); nword[cid] += 1
            P = np.array(poly)
            w = dict(id=f'{cid}-TC{nword[cid]:02d}', reading=reading, kind=kind, flags=flags, angle=round(ang, 1), height=h,
                     length=round(L, 1), poly=poly, aabb=[int(P[:, 0].min()), int(P[:, 1].min()), int(math.ceil(P[:, 0].max())), int(math.ceil(P[:, 1].max()))],
                     snapped=False, touches_line=False, text_px=0, annot_line=None, truth_check_line=ln)
            W[cid]['words'].append(w); rec.update(word=w['id'], reading=reading, kind=kind, note=note)
            log.append(f'{cid} line {ln:3d}  WORD  {w["id"]} {reading!r} {kind} {flags}   {note}')
        else: raise SystemExit(f'line {ln}: unknown op {op}')
        W[cid]['truth_check'].append(rec)
    for c in IDS:
        m = masks[c]; x0, y0 = crops[c]['win'][:2]
        for w in W[c]['words']:
            pm = np.zeros(m.shape, np.uint8)
            cv2.fillPoly(pm, [np.round(np.array(w['poly'], float) - [x0, y0]).astype(np.int32)], 1)
            w['text_px'] = int(((pm > 0) & (m == 2)).sum())
        W[c]['counts_before_truth_check'] = W[c].get('counts')
        if '0' in (W[c].get('counts') or {}): W[c]['counts'] = {str(v): int((m == v).sum()) for v in range(4)}
        else: W[c]['counts'] = {'paper': int((m == 0).sum()), 'ink_not_text': int((m == 1).sum()), 'text': int((m == 2).sum()), 'dont_care': int((m == 3).sum())}
        W[c]['n_words'] = len(W[c]['words'])
        cv2.imwrite(os.path.join(outdir(c), f'{c}_mask.png'), m)
        with open(os.path.join(outdir(c), f'{c}_words.json'), 'w', encoding='utf8', newline='\n') as fo: json.dump(W[c], fo, indent=1, ensure_ascii=False)
    for d in (tc.FIXED, FIXV2):
        with open(os.path.join(d, 'crops.json'), 'w', encoding='utf8', newline='\n') as fo:
            json.dump({c: crops[c] for c in IDS if outdir(c) == d}, fo, indent=1)
    # pixel totals per crop, measured
    tot = []
    for c in IDS:
        o = tc.truth(c); n = masks[c]
        d = {f'{a}->{b}': int(((o == a) & (n == b)).sum()) for a in range(4) for b in range(4) if a != b and ((o == a) & (n == b)).any()}
        tot.append(f'{c}: changed {int((o != n).sum())} px  {d}   text px {int((o == 2).sum())} -> {int((n == 2).sum())}')
    for d, pre in ((tc.FIXED, 'H'), (FIXV2, 'T')):
        with open(os.path.join(d, 'fixes_log.txt'), 'w', encoding='utf8', newline='\n') as fo:
            fo.write('\n'.join([l for l in log if l.startswith(pre)] + [''] + [t for t in tot if t.startswith(pre)]) + '\n')
    print('\n'.join(log[-12:] + [''] + tot))


if __name__ == '__main__':
    main()
