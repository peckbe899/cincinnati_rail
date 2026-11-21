"""merge/v-batch: every plate where the merged step gives FEWER editor lines or blocks than the batch or B, and why.

    python -B fewer.py        (after measure104.py) -> v-batch/fewer.json, printed list

Lines. The editor lines are split into what step 4 leaves out and what the rings join:
  editor_lines / editor_len           merged as shown (edit_server.clean of N_edges.json)
  kept_all lines / len                merged, with the sides 'not on a line' and 'on rail' kept (step4 keep_unlined=True,
                                      rail_drop=False): the merged outlines before step 4's two new drops
  batch / B lines and len             as measure104.py
  If kept_all has as many lines as the other run, the loss is step 4's drops (reason: dropped, with the length of each
  kind). If kept_all has fewer lines but about the same length or more, the rings joined collinear pieces into longer
  lines (reason: joined). If the length itself is lower, the outlines lost ground (reason: lost length; the blocks are
  then looked at).
Blocks. The block polygons are drawn at 1/4 size (batch and B: their block polygons; merged: its block polygons) and
every block of the other run is matched to the merged block that overlaps it most (IoU > 0.5 = the same block). An
unmatched block of the other run is:
  joined    most of it (>= 50%) lies in one merged block that also holds >= 50% of another of its blocks
  split     >= 50% covered by merged blocks, but by several, none matching
  lost      under 50% covered by any merged block; for these the merged seed rule is checked on the block's own ground:
            the largest piece of the block seed (area P > 0.5, 14 px in from its edge, less 3 px round the detected lines)
            under MK_SEED_MIN = 2000 px means the block got no marker of its own; or the block lies off the map ground
  partial   >= 50% covered by one merged block that matches no other block, but IoU <= 0.5 (shape changed)
and a merged block matching none of the other run's is new.
"""
import json, os
import numpy as np
import cv2
import common as C
M = json.load(open(C.ME + 'measure104.json'))
BDIR = C.BENCH + 'outline-nesting/runs_plates/final/'
el = lambda r: cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * r + 1, 2 * r + 1))


def raster(polys, h, w, s=4):
    lab = np.zeros((h // s + 1, w // s + 1), np.int32); k = 0; areas = []
    for p in polys:
        if not p or p[0].get('hole') or len(p) < 3: continue
        k += 1; r = np.round(np.array([q['a'] for q in p], float) / s).astype(np.int32); m = np.zeros_like(lab, np.uint8); cv2.fillPoly(m, [r], 1)
        lab[(m > 0) & (lab == 0)] = k; areas.append(int(m.sum()))
    return lab, k


def match(other, merged, n, polys_other, H, W):
    lo, ko = raster(other, H, W); lm, km = raster(merged, H, W)
    J = np.bincount(lo.ravel().astype(np.int64) * (km + 1) + lm.ravel(), minlength=(ko + 1) * (km + 1)).reshape(ko + 1, km + 1)
    Ao, Am = J.sum(1), J.sum(0)
    iou = J[1:, 1:] / np.maximum(1, Ao[1:, None] + Am[None, 1:] - J[1:, 1:])
    best = iou.argmax(1) if km else np.zeros(ko, int); bi = iou.max(1) if km else np.zeros(ko)
    res = dict(matched=0, joined=0, split=0, lost=0, partial=0, lost_ids=[], joined_into=[])
    holder = {}
    for i in range(ko):
        if bi[i] > 0.5: res['matched'] += 1; continue
        cov = J[i + 1, 1:].sum() / max(1, Ao[i + 1]); j = int(J[i + 1, 1:].argmax()) if km else -1
        if cov < 0.5: res['lost'] += 1; res['lost_ids'].append(i); continue
        share_j = J[i + 1, j + 1] / max(1, Ao[i + 1])
        others = [k for k in range(ko) if k != i and J[k + 1, j + 1] / max(1, Ao[k + 1]) >= 0.5]
        if share_j >= 0.5 and others: res['joined'] += 1; holder.setdefault(j, set()).update([i] + others)
        elif share_j < 0.5: res['split'] += 1
        else: res['partial'] += 1
    res['joined_into'] = [sorted(v) for v in holder.values()]
    res['new'] = int(sum(1 for j in range(km) if (iou[:, j].max() if ko else 0) <= 0.5))
    res['n_other'], res['n_merged'] = ko, km
    return res, lo


def lost_reasons(n, polys_other, ids, H, W):
    """for each lost block: the largest seed piece of the merged rule on its ground, and whether it is off the map ground"""
    if not ids: return []
    pa_h = cv2.imread(C.U + f'{n}_pred_area_ng1.png', 0); pl = cv2.imread(C.U + f'{n}_lines_lines_ng1.png', 0)
    paper = cv2.resize(np.load(C.DATA + f'cufp/{n}/png_alpha_s4.npy').astype(np.float32), (W, H)) > 0.5
    mg = C.ME + f'plates/{n}/{n}_mapground.png'
    alpha = paper & (cv2.resize(cv2.imread(mg, 0), (W, H), interpolation=cv2.INTER_NEAREST) > 0) if os.path.exists(mg) else paper
    blocks = [p for p in polys_other if p and not p[0].get('hole') and len(p) >= 3]; out = []
    for i in ids:
        r = np.round(np.array([q['a'] for q in blocks[i]], float)).astype(np.int32)
        x0, y0 = np.maximum(r.min(0) - 60, 0); x1, y1 = np.minimum(r.max(0) + 60, [W - 1, H - 1])
        m = np.zeros((y1 - y0 + 1, x1 - x0 + 1), np.uint8); cv2.fillPoly(m, [r - [x0, y0]], 1)
        # the area map at full size on this crop (half-size map enlarged x2; within a pixel of outlines.py's resize)
        pa = cv2.resize(pa_h[y0 // 2:(y1 + 1) // 2 + 1, x0 // 2:(x1 + 1) // 2 + 1], None, fx=2, fy=2, interpolation=cv2.INTER_LINEAR)[:m.shape[0], :m.shape[1]]
        if pa.shape != m.shape: pa = cv2.resize(pa, (m.shape[1], m.shape[0]))
        a = alpha[y0:y1 + 1, x0:x1 + 1]; ll = pl[y0:y1 + 1, x0:x1 + 1]
        blk = (pa > 127) & a
        seed = (cv2.erode(blk.astype(np.uint8), el(14)) > 0) & (cv2.dilate((ll > 127).astype(np.uint8), el(3)) == 0) & (m > 0)
        nn, cc, st, _ = cv2.connectedComponentsWithStats(seed.astype(np.uint8), connectivity=4)
        big = int(st[1:, cv2.CC_STAT_AREA].max()) if nn > 1 else 0
        out.append(dict(block_area_px=int(m.sum()), off_map_share=round(float(1 - a[m > 0].mean()), 2), area_block_share=round(float((pa[m > 0] > 127).mean()), 2),
                        largest_seed_px=big, seed_pieces=int(nn - 1), at=[int(r[:, 0].mean()), int(r[:, 1].mean())]))
    return out


res = {}
for n, r in M.items():
    m, b, B = r['merged'], r['batch'], r['B']
    if 'failed' in m: continue
    fewer = [k for k, o in (('editor lines vs batch', m['editor_lines'] < b['editor_lines']), ('editor lines vs B', m['editor_lines'] < B['editor_lines']),
                            ('blocks vs batch', m['blocks'] < b['blocks']), ('blocks vs B', m['blocks'] < B['blocks'])) if o]
    if not fewer: continue
    x = dict(plate=n, group=r['group'], fewer=fewer,
             lines=dict(merged=[m['editor_lines'], m['editor_len']], kept_all=[m['editor_lines_kept_all'], m['editor_len_kept_all']], batch=[b['editor_lines'], b['editor_len']], B=[B['editor_lines'], B['editor_len']],
                        dropped=m['dropped'], mean_len=dict(merged=round(m['editor_len'] / max(1, m['editor_lines'])), batch=round(b['editor_len'] / max(1, b['editor_lines'])), B=round(B['editor_len'] / max(1, B['editor_lines'])))),
             blocks=dict(merged=m['blocks'], batch=b['blocks'], B=B['blocks']))
    if m['blocks'] < b['blocks'] or m['blocks'] < B['blocks']:
        im = cv2.imread(C.DATA + f'cufp/22-{n}.jpg', cv2.IMREAD_REDUCED_GRAYSCALE_2); H, W = im.shape[0] * 2, im.shape[1] * 2
        mp = json.load(open(C.ME + f'plates/{n}/outlines.json', encoding='utf8'))
        for name, path in (('batch', C.G + f'22-{n}/outlines.json'), ('B', BDIR + f'{n}/outlines.json')):
            if not (m['blocks'] < (b if name == 'batch' else B)['blocks']): continue
            op = json.load(open(path, encoding='utf8')); mt, _ = match(op, mp, n, op, H, W)
            mt['lost_why'] = lost_reasons(n, op, mt['lost_ids'], H, W); x['blocks']['vs ' + name] = mt
    res[n] = x
json.dump(res, open(C.mine(C.ME + 'fewer.json'), 'w'), indent=1)
for n, x in res.items():
    L = x['lines']; print(f"{n:4s} {x['group']:10s} {', '.join(x['fewer'])} | lines m {L['merged']} all {L['kept_all']} batch {L['batch']} B {L['B']} dropped {L['dropped']} | blocks {x['blocks']['merged']}/{x['blocks']['batch']}/{x['blocks']['B']}")
    for k in ('vs batch', 'vs B'):
        if k in x['blocks']:
            t = x['blocks'][k]; print(f"      {k}: matched {t['matched']} joined {t['joined']} split {t['split']} lost {t['lost']} partial {t['partial']} new {t['new']} | lost: {[(w['block_area_px'], w['largest_seed_px'], w['off_map_share'], w['area_block_share']) for w in t['lost_why']]}")
