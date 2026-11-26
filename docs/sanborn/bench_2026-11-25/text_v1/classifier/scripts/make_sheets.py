"""Ben's labelling sheets (classifier step, 26 Nov 2026).

    cd data/sanborn; python -B bench_2026-11-25/text_v1/classifier/scripts/make_sheets.py

Glyphs: the shapes prototype's glyph candidates (text/shapes/glyphs/N.npz, plates 44, 1A, 5, 3, 90, 94), each cut out after
thin lines were taken out and TURNED UPRIGHT by the direction of its word, at full size ('raw', glyphs of 12 px or more).
Each is read by the shape classifier (out/model_cnn2.npz). Three sheets, about 150 rows each; one row = one cluster:
  A  digits at lot-number size: glyphs 24-48 px tall whose best class is a figure (P 0.5 or more)
  B  capitals: glyphs 20-130 px whose summed capital-letter probability is 0.5 or more; K O B U S D H G get extra rows
  C  marks and junk: glyphs 6-24 px whose best class is ' " . - & or , (P 0.4 or more), and glyphs of any size the
     classifier calls junk (P 0.6 or more): hooks, ticks, hydrant dots, dashes, line stubs, lot-line corners, symbols
Inside each sheet the glyphs are grouped by the classifier's best class, and each group is split by k-means (blurred
pixels 16x16 + HOG + log size, as shapes/scripts/cluster.py) into a number of rows that grows with the square root of
its size. Rows are drawn 25 to a page: the row number, Claude's guess (the classifier's majority class in the row, with
its mean probability p), the row's mean glyph and 26 random members with their height in px. Writes for_ben/:
  sheet_A_digits_pNN.png, sheet_B_capitals_pNN.png, sheet_C_marks_junk_pNN.png   the pictures
  labels_A_digits.csv, labels_B_capitals.csv, labels_C_marks_junk.csv            one row per cluster, 'label' pre-filled
            with Claude's guess: the classifier's majority class, corrected by eye on the pages Claude looked at
            (scripts/claude_eye.json; '' = mixed)
  members.npz   every member of every row (plate, glyph index), so Ben's labels can be applied to all of them
No truth is used. Random seed 0."""
import csv, json, os, sys
sys.dont_write_bytecode = True
import numpy as np, cv2
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from common import piece_features, hog_batch  # noqa
from model_np import load_model, predict  # noqa
SH = os.path.join('bench_2026-11-25', 'text', 'shapes')
OUT = os.path.join(HERE, '..', 'for_ben'); MODEL = os.path.join(HERE, '..', 'out', 'model_cnn2.npz')
CLS = []
EYE = json.load(open(os.path.join(HERE, 'claude_eye.json'), encoding='utf8'))
PLATES = ['44', '1A', '5', '3', '90', '94']; ROWS_PAGE = 25; PER_ROW = 26; T = 40
MARKS = ('\'', '"', '.', '-', '&', ',')


def load_glyphs():
    G = []
    for N in PLATES:
        D = dict(np.load(os.path.join(SH, 'glyphs', f'{N}.npz')))
        hw = D['hw'].astype(int); ro = D['raw_off']; raw = D['raw']
        for k in range(len(hw)):
            h, w = hw[k]
            if max(h, w) < 6: continue
            m = raw[ro[k]:ro[k + 1]].reshape(h, w) if ro[k + 1] > ro[k] else None
            G.append((N, k, h, w, m, D['imgs'][k]))
    return G


def cluster_feats(imgs, hw):
    x = imgs.astype(np.float32) / 255
    pix = np.stack([cv2.resize(cv2.GaussianBlur(g, (0, 0), 1.0), (16, 16), interpolation=cv2.INTER_AREA).ravel() for g in x])
    pix /= np.linalg.norm(pix, axis=1, keepdims=True) + 1e-6
    H = hog_batch(x); H /= np.linalg.norm(H, axis=1, keepdims=True) + 1e-6
    return np.hstack([pix, H, np.log(np.maximum(hw, 1)) * 0.6]).astype(np.float32)


def kmeans(X, k, seed=0):
    if len(X) <= k: return np.arange(len(X))
    cv2.setRNGSeed(seed)
    _, lab, _ = cv2.kmeans(X, k, None, (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 50, 1e-4), 3, cv2.KMEANS_PP_CENTERS)
    return lab.ravel()


def tile(g, px):
    t = np.full((T, T), 255, np.uint8); t[1:33, 4:36] = 255 - g
    cv2.putText(t, str(px), (2, 39), cv2.FONT_HERSHEY_PLAIN, 0.6, 120, 1); return t


def make(name, title, sel, top, P, G, nrows, boost, rng, members, rows_out):
    """sel: indices into G; top: best class per glyph (all G)"""
    groups = {}
    for i in sel: groups.setdefault(top[i], []).append(i)
    tot = sum(np.sqrt(len(v)) * boost.get(c, 1.0) for c, v in groups.items())
    alloc = {c: max(1, int(round(nrows * np.sqrt(len(v)) * boost.get(c, 1.0) / tot))) for c, v in groups.items()}
    rows = []
    for c in sorted(groups, key=lambda c: (-len(groups[c]), c)):
        idx = np.array(groups[c]); k = min(alloc[c], max(1, len(idx) // 8))
        X = cluster_feats(np.stack([G[i][5] for i in idx]), np.array([[G[i][2], G[i][3]] for i in idx]))
        lab = kmeans(X, k)
        for j in range(lab.max() + 1):
            mem = idx[lab == j]
            if len(mem) < 4: continue
            tc = [top[i] for i in mem]; vals, cnt = np.unique(tc, return_counts=True); g = vals[cnt.argmax()]
            gc = 'junk' if str(g).startswith('junk') else str(g); conf = float(np.nanmean(P[mem, CLS.index(gc)])) if gc in CLS else float('nan')
            rows.append(dict(mem=mem, guess=str(g), share=conf, px=int(np.median([max(G[i][2], G[i][3]) for i in mem]))))
    rows.sort(key=lambda r: (r['guess'], -r['share']))
    eye = EYE.get(name, {}); looked = EYE.get('pages_looked', {}).get(name, [])
    for r_i, r in enumerate(rows, 1):
        g = 'junk' if r['guess'].startswith('junk') else r['guess']; r['model'] = g
        r['label'] = eye.get(str(r_i), g); r['checked'] = 'eye' if ((r_i - 1) // ROWS_PAGE + 1) in looked else 'no'
    pages = []
    for r0 in range(0, len(rows), ROWS_PAGE):
        strips = []
        hdr = np.full((30, 240 + PER_ROW * T), 255, np.uint8)
        cv2.putText(hdr, f'{title}  page {r0 // ROWS_PAGE + 1}  rows {r0 + 1}-{min(len(rows), r0 + ROWS_PAGE)}  (guess by Claude; cl: = classifier guess where Claude changed it; p = classifier mean probability)', (4, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, 0, 1)
        strips.append(hdr)
        for r_i, r in enumerate(rows[r0:r0 + ROWS_PAGE], r0 + 1):
            row = np.full((T + 4, 240 + PER_ROW * T), 255, np.uint8)
            cv2.putText(row, f'{r_i}', (4, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.8, 0, 2)
            g = r['label'] if r['label'] != '' else 'mixed'
            cv2.putText(row, f'{g}', (62, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.9 if len(g) < 3 else 0.55, 0, 2)
            if r['label'] != r['model']: cv2.putText(row, f"cl:{r['model']}", (62, 42), cv2.FONT_HERSHEY_PLAIN, 0.7, 100, 1)
            cv2.putText(row, f"p{r['share']:.2f}", (128, 12), cv2.FONT_HERSHEY_PLAIN, 0.8, 80, 1)
            cv2.putText(row, f"n{len(r['mem'])}", (128, 26), cv2.FONT_HERSHEY_PLAIN, 0.8, 80, 1)
            cv2.putText(row, f"{r['px']}px", (128, 40), cv2.FONT_HERSHEY_PLAIN, 0.8, 80, 1)
            mean = np.mean([G[i][5] for i in r['mem']], 0).astype(np.uint8); row[2:2 + T, 195:195 + T] = tile(mean, '')
            pick = r['mem'] if len(r['mem']) <= PER_ROW else rng.choice(r['mem'], PER_ROW, replace=False)
            for j, i in enumerate(pick): row[2:2 + T, 240 + j * T:240 + (j + 1) * T] = tile(G[i][5], max(G[i][2], G[i][3]))
            strips.append(row); strips.append(np.full((1, row.shape[1]), 170, np.uint8))
        fn = f'sheet_{name}_p{r0 // ROWS_PAGE + 1:02d}.png'; cv2.imwrite(os.path.join(OUT, fn), np.vstack(strips)); pages.append(fn)
    with open(os.path.join(OUT, f'labels_{name}.csv'), 'w', newline='', encoding='utf8') as f:
        w = csv.writer(f); w.writerow(['row', 'page', 'label', 'classifier_guess', 'classifier_p', 'claude_looked', 'n_glyphs', 'median_px', 'row_key'])
        for r_i, r in enumerate(rows, 1):
            key = f'{name}:{r_i}'; members[key] = np.array([[PLATES.index(G[i][0]), G[i][1]] for i in r['mem']], np.int32)
            w.writerow([r_i, (r_i - 1) // ROWS_PAGE + 1, r['label'], r['model'], round(r['share'], 2), r['checked'], len(r['mem']), r['px'], key])
    rows_out[name] = dict(rows=len(rows), pages=pages, glyphs=int(sum(len(r['mem']) for r in rows)))
    print(name, len(rows), 'rows,', len(pages), 'pages', flush=True)


def main():
    os.makedirs(OUT, exist_ok=True); rng = np.random.default_rng(0)
    G = load_glyphs(); print(len(G), 'glyphs', flush=True)
    M = load_model(MODEL); cls = M['classes']; global CLS; CLS = cls
    ok = [i for i, g in enumerate(G) if g[4] is not None]
    img, sc = piece_features([G[i][4] for i in ok]); pr = predict(M, img, sc)
    P = np.zeros((len(G), len(cls)), np.float32); P[ok] = pr; P[[i for i, g in enumerate(G) if g[4] is None], cls.index('junk')] = np.nan
    top = np.array(cls)[np.nan_to_num(P, nan=0).argmax(1)]; pmax = np.nan_to_num(P, nan=0).max(1)
    h = np.array([g[2] for g in G]); e = np.array([max(g[2], g[3]) for g in G]); has = np.array([g[4] is not None for g in G])
    cap = np.array([len(c) == 1 and c.isalpha() and c.isupper() for c in cls]); pcap = np.nan_to_num(P[:, cap], nan=0).sum(1)
    members = {}; rows_out = {}
    selA = np.nonzero(has & (h >= 24) & (h <= 48) & np.array([t.isdigit() for t in top]) & (pmax >= 0.5))[0]
    make('A_digits', 'SHEET A: digits at lot-number size (24-48 px tall)', selA, top, P, G, 150, {}, rng, members, rows_out)
    capc = np.array(cls)[cap]; topcap = np.where(cap[None, :], np.nan_to_num(P, nan=0), -1).argmax(1); topc = np.array(cls)[topcap]
    selB = np.nonzero(has & (e >= 20) & (pcap >= 0.5))[0]
    make('B_capitals', 'SHEET B: capitals (K O B U S D H G wanted most)', selB, topc, P, G, 150, {c: 2.5 for c in 'KOBUSDHG'}, rng, members, rows_out)
    marks = np.isin(top, MARKS) & (pmax >= 0.4) & (e >= 6) & (e <= 24)
    junk = (np.nan_to_num(P[:, cls.index('junk')], nan=0) >= 0.6)
    selC = np.nonzero(has & (marks | junk))[0]
    # junk rows split by size so ticks, dots, stubs and corners fall apart
    topC = top.copy().astype(object)
    for lo, hi, nm in ((0, 16, 'junk_small'), (16, 32, 'junk_mid'), (32, 200, 'junk_big')):
        topC[junk & (e >= lo) & (e < hi)] = nm
    make('C_marks_junk', "SHEET C: marks ' \" . - & , and junk (hooks, ticks, hydrant dots, dashes, line stubs, corners, symbols)", selC, topC, P, G, 150,
         {m: 1.8 for m in MARKS}, rng, members, rows_out)
    np.savez_compressed(os.path.join(OUT, 'members.npz'), plates=np.array(PLATES), **{k.replace(':', '__'): v for k, v in members.items()})
    json.dump(rows_out, open(os.path.join(OUT, 'sheets.json'), 'w'), indent=1)


if __name__ == '__main__':
    main()
