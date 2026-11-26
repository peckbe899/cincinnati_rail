"""Training and dev sets for the character-or-not classifier (classifier step, 26 Nov 2026).

    cd data/sanborn
    python -B bench_2026-11-25/text_v1/classifier/scripts/build_train.py [--exclude WINDOWS.json] [--out NAME]

Units are finder v2's PIECES (data/pieces/N.npz from dump_pieces.py: 8-connected ink less the line ink grown 1 px), seen
as they lie on the plate. Sources:
  cluster  Claude's cluster labels (text/shapes/labels/claude_round1.json and claude_round2.json, NOT Ben's), through the
           shapes prototype's training glyphs (text/shapes/pred.npz train_*: the members of each labelled cluster less the
           20% furthest from its mean) on plates 44, 1A, 5, 3, 90, 94. A glyph's label goes to the finder piece whose
           box matches it (box IoU 0.7 or more, area within 0.7-1.43 x).
  finder5  junk from finder v2's own 'other ink' (code 5): pieces of kind tick, bar (streetcar dash), ring, box, bldg,
           long; and strokes, blobs and jogs with no text (code 2/3) within 25 px. At most 1,500 per plate and kind.
  rail     ticks and dashes on Ben's tracks (picks22_guided/22-N/rail_ben.json on 44 and 5, used as LABELS for training
           only, never at run time): pieces 40 px or smaller crossing the 3 px band round a track's centre line.
  synth    synthetic glyphs (data/synth.npz from synth.py).
Pieces inside the truth crops T1-T7 (text_v1/truth/crops.json, the dev set) are never used for training; neither are
pieces in any window of --exclude (JSON {plate: [[x0, y0, x1, y1], ...]}), e.g. so the gate scorer can refit without its
held-out windows. The dev set is every piece inside T1-T7 with its truth make-up (pixels of truth 2 and truth 1).
Writes data/NAME.npz (default train): img (n,32,32) uint8, scal (n,10), label, source, plate, bbox, kind; and
data/dev.npz the same for the dev pieces plus t2, t1, code (finder2's pre-shared code of most of its pixels)."""
import json, os, sys, time
sys.dont_write_bytecode = True
import numpy as np, cv2
from scipy.spatial import cKDTree
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from dump_pieces import load, mask  # noqa
from common import piece_features, tight  # noqa
SHAPES = os.path.join('bench_2026-11-25', 'text', 'shapes')
TRUTH = os.path.join('bench_2026-11-25', 'text_v1', 'truth')
DATA = os.path.join(HERE, '..', 'data')
PLATES = ['44', '1A', '5', '3', '90', '94']
CAP_KIND = 1500


def inside_any(bb, wins):
    """bool per piece: its box overlaps any window"""
    out = np.zeros(len(bb), bool)
    for x0, y0, x1, y1 in wins:
        out |= (bb[:, 0] < x1) & (bb[:, 1] < y1) & (bb[:, 0] + bb[:, 2] > x0) & (bb[:, 1] + bb[:, 3] > y0)
    return out


def match_glyphs(D, gb, garea):
    """finder piece index for each shapes glyph box (x, y, w, h), or -1"""
    pb = D['bbox'].astype(float); pc = pb[:, :2] + pb[:, 2:] / 2; T = cKDTree(pc)
    gc = gb[:, :2] + gb[:, 2:] / 2; out = np.full(len(gb), -1)
    pa = D['f_A']
    for j, (c, b) in enumerate(zip(gc, gb)):
        best, bi = 0, -1
        for i in T.query_ball_point(c, max(b[2], b[3]) / 2 + 6):
            x0, y0 = max(b[0], pb[i, 0]), max(b[1], pb[i, 1]); x1, y1 = min(b[0] + b[2], pb[i, 0] + pb[i, 2]), min(b[1] + b[3], pb[i, 1] + pb[i, 3])
            inter = max(0, x1 - x0) * max(0, y1 - y0); iou = inter / (b[2] * b[3] + pb[i, 2] * pb[i, 3] - inter)
            if iou > best: best, bi = iou, i
        if bi >= 0 and best >= 0.7 and 0.7 <= pa[bi] / max(1, garea[j]) <= 1.43: out[j] = bi
    return out


def text_near(D, r=25):
    """bool per piece: some text (pre-shared code 2 or 3) within r px of its box"""
    t = np.isin(D['pre'], (2, 3)).astype(np.uint8); ii = cv2.integral(t)
    bb = D['bbox']; H, W = t.shape
    x0 = np.clip(bb[:, 0] - r, 0, W); y0 = np.clip(bb[:, 1] - r, 0, H); x1 = np.clip(bb[:, 0] + bb[:, 2] + r, 0, W); y1 = np.clip(bb[:, 1] + bb[:, 3] + r, 0, H)
    s = ii[y1, x1] - ii[y0, x1] - ii[y1, x0] + ii[y0, x0]
    own = D['codes'][:, 2] + D['codes'][:, 3]
    return (s - own) > 0


def rail_pieces(D, N):
    p = f'picks22_guided/22-{N}/rail_ben.json'
    if N not in ('44', '5') or not os.path.exists(p): return np.zeros(len(D['bbox']), bool)   # Ben's rail is complete on 44 and 5 only
    B = json.load(open(p, encoding='utf8')); H, W = D['pre'].shape; m = np.zeros((H, W), np.uint8)
    for t in B['tracks']:
        if len(t['pts']) > 1: cv2.polylines(m, [np.round(np.array(t['pts'])).astype(np.int32)], False, 1, 3)
    ii = cv2.integral(m); bb = D['bbox']
    s = ii[bb[:, 1] + bb[:, 3], bb[:, 0] + bb[:, 2]] - ii[bb[:, 1], bb[:, 0] + bb[:, 2]] - ii[bb[:, 1] + bb[:, 3], bb[:, 0]] + ii[bb[:, 1], bb[:, 0]]
    hit = np.zeros(len(bb), bool)
    for i in np.nonzero((s > 0) & (np.maximum(bb[:, 2], bb[:, 3]) <= 40))[0]:
        x, y, w, h = bb[i]; hit[i] = bool((m[y:y + h, x:x + w] & (mask(D, i) > 0)).any())
    return hit


def main():
    a = sys.argv; t0 = time.time()
    excl = json.load(open(a[a.index('--exclude') + 1])) if '--exclude' in a else {}
    name = a[a.index('--out') + 1] if '--out' in a else 'train'
    crops = json.load(open(os.path.join(TRUTH, 'crops.json')))
    devwin = {}
    for tid in ('T1', 'T2', 'T3', 'T4', 'T6', 'T7'): devwin.setdefault(crops[tid]['plate'], []).append((tid, crops[tid]['win']))
    pred = np.load(os.path.join(SHAPES, 'pred.npz'), allow_pickle=True)
    rng = np.random.default_rng(0)
    rows = []   # (plate, piece index, label, source)
    dev = []
    for N in PLATES:
        D = load(N); bb = D['bbox']; n = len(bb)
        bad = inside_any(bb, [w for _, w in devwin.get(N, [])]) | inside_any(bb, excl.get(N, []))
        # cluster labels
        G = np.load(os.path.join(SHAPES, 'glyphs', f'{N}.npz'))
        sel = pred['train_plate'] == N; gi = pred['train_idx'][sel]; gy = pred['train_y'][sel]
        mt = match_glyphs(D, G['bbox'][gi].astype(float), G['area'][gi])
        ok = (mt >= 0); ok[ok] &= ~bad[mt[ok]]
        lab = {}
        for i, y in zip(mt[ok], gy[ok]): lab[int(i)] = str(y)
        for i, y in lab.items(): rows.append((N, i, y, 'cluster'))
        nc = len(lab)
        # finder2's own other ink (code 5 for most of the piece)
        k = D['kind']; c5 = D['codes'][:, 5] >= 0.8 * np.maximum(D['codes'].sum(1), 1); tn = text_near(D)
        used = set(lab)
        nf = 0
        for kd in ('tick', 'bar', 'ring', 'box', 'bldg', 'long', 'stroke', 'blob', 'jog'):
            s = np.nonzero((k == kd) & c5 & ~bad & (np.maximum(bb[:, 2], bb[:, 3]) >= 6))[0]
            if kd in ('stroke', 'blob', 'jog'): s = s[~tn[s]]
            s = [i for i in s if int(i) not in used]
            if len(s) > CAP_KIND: s = rng.choice(s, CAP_KIND, replace=False)
            for i in s: rows.append((N, int(i), 'junk', 'finder5')); used.add(int(i)); nf += 1
        # rail ticks and dashes (Ben's tracks, as training labels only)
        rp = np.nonzero(rail_pieces(D, N) & ~bad)[0]; nr = 0; drop = set()
        for i in rp:
            if int(i) in used:
                if lab.get(int(i), 'junk') != 'junk': continue
                drop.add(int(i))
            rows.append((N, int(i), 'junk', 'rail')); used.add(int(i)); nr += 1
        if drop: rows[:] = [r for r in rows if not (r[0] == N and r[1] in drop and r[3] != 'rail')]
        # dev pieces: inside T1-T7, with their truth make-up
        for tid, (x0, y0, x1, y1) in devwin.get(N, []):
            tr = cv2.imread(os.path.join(TRUTH, f'{tid}_mask.png'), 0)
            s = np.nonzero((bb[:, 0] >= x0) & (bb[:, 1] >= y0) & (bb[:, 0] + bb[:, 2] <= x1) & (bb[:, 1] + bb[:, 3] <= y1))[0]
            for i in s:
                x, y, w, h = bb[i]; m = mask(D, i) > 0; t = tr[y - y0:y - y0 + h, x - x0:x - x0 + w][m]
                dev.append((N, int(i), tid, int((t == 2).sum()), int((t == 1).sum())))
        print(f'plate {N}: cluster {nc} (of {int(sel.sum())} glyphs), finder5 {nf}, rail {nr}; dev so far {len(dev)} | {time.time() - t0:.0f} s', flush=True)
    # features
    def feats(items):
        out_m = []; meta = []
        byp = {}
        for it in items: byp.setdefault(it[0], []).append(it)
        for N, its in byp.items():
            D = load(N)
            for it in its:
                out_m.append(mask(D, it[1])); meta.append((it, D['bbox'][it[1]], D['kind'][it[1]], D['codes'][it[1]]))
        img, sc = piece_features(out_m)
        return img, sc, meta
    img, sc, meta = feats(rows)
    S = dict(np.load(os.path.join(DATA, 'synth.npz')))   # read once (an open npz decompresses on every access)
    sb, so = S['bits'], S['off']
    sm = [np.unpackbits(sb[so[j]:so[j + 1]])[:h * w].reshape(h, w) for j, (h, w) in enumerate(S['hw'])]
    simg, ssc = piece_features(sm)
    lab = np.r_[np.array([m[0][2] for m in meta]), S['label']]
    src = np.r_[np.array([m[0][3] for m in meta]), np.array(['synth'] * len(sm))]
    plate = np.r_[np.array([m[0][0] for m in meta]), np.array([''] * len(sm))]
    bbox = np.r_[np.array([m[1] for m in meta]).reshape(-1, 4), np.zeros((len(sm), 4), int)]
    kind = np.r_[np.array([m[2] for m in meta]), np.array(['synth'] * len(sm))]
    np.savez_compressed(os.path.join(DATA, f'{name}.npz'), img=(np.r_[img, simg] * 255).round().astype(np.uint8), scal=np.r_[sc, ssc],
                        label=lab, source=src, plate=plate, bbox=bbox, kind=kind, font=np.r_[np.array([''] * len(meta)), S['font']],
                        exclude=json.dumps(excl))
    from collections import Counter
    print('training rows by source:', dict(Counter(src)), '| by label (top):', Counter(lab).most_common(20))
    dimg, dsc, dmeta = feats(dev)
    np.savez_compressed(os.path.join(DATA, 'dev.npz'), img=(dimg * 255).round().astype(np.uint8), scal=dsc,
                        plate=np.array([m[0][0] for m in dmeta]), idx=np.array([m[0][1] for m in dmeta]), crop=np.array([m[0][2] for m in dmeta]),
                        t2=np.array([m[0][3] for m in dmeta]), t1=np.array([m[0][4] for m in dmeta]), bbox=np.array([m[1] for m in dmeta]),
                        kind=np.array([m[2] for m in dmeta]), codes=np.array([m[3] for m in dmeta]))
    print('dev pieces:', len(dmeta), f'| {time.time() - t0:.0f} s')


if __name__ == '__main__':
    main()
