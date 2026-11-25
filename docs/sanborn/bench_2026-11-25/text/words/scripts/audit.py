"""A random sample of strings for checking by eye (no word truth on the plate yet): each row shows the scan around the
string with its own ink in red and its reading start marked by a blue dot, then the rectified strip, then the kinds.

    cd data/sanborn
    python -B bench_2026-11-25/text/words/scripts/audit.py N [--k 40] [--seed 11] [--tag T]

Random among the strings with at least one word not called junk (lone pieces included), outside the inventory's truth
crops. Writes out/audit_T.jpg and out/audit_T.json (the sample, row by row, for writing the verdicts beside it)."""
import json, os, sys
import numpy as np
import cv2
HERE = os.path.dirname(os.path.abspath(__file__)); OUT = os.path.join(os.path.dirname(HERE), 'out')
TR = os.path.join(os.path.dirname(os.path.dirname(HERE)), 'inventory', 'truth')
AB = dict(street_name='ST', house_number='HN', lot_dimension='LD', block_number='BN', pipe_label='PL', lot_number='LN',
          owner_or_note='ON', story_or_single='1', other='?', junk='x')
RH = 64; CW = 200; SW = 360


def main():
    N = sys.argv[1]
    k = int(sys.argv[sys.argv.index('--k') + 1]) if '--k' in sys.argv else 40
    seed = int(sys.argv[sys.argv.index('--seed') + 1]) if '--seed' in sys.argv else 11
    T = sys.argv[sys.argv.index('--tag') + 1] if '--tag' in sys.argv else N
    J = json.load(open(os.path.join(OUT, f'{T}_words.json'), encoding='utf8'))
    crops = json.load(open(os.path.join(TR, 'crops.json'), encoding='utf8'))
    wins = [c['win'] for c in crops.values() if c['plate'] == N]
    L = cv2.imread(os.path.join(OUT, f'{T}_glyphlab.png'))
    lab = L[..., 0].astype(np.int32) | (L[..., 1].astype(np.int32) << 8) | (L[..., 2].astype(np.int32) << 16)
    im = cv2.imread(f'cufp/22-{N}.jpg')
    S = []
    for s in J['strings']:
        if all(w['kind'] == 'junk' for w in s['words']): continue
        x, y = np.array(s['centre_line']).mean(0)
        if any(a <= x < c and b <= y < d for a, b, c, d in wins): continue
        S.append(s)
    rng = np.random.default_rng(seed); pick = [S[i] for i in sorted(rng.permutation(len(S))[:k])]
    canvas = np.full((len(pick) * (RH + 6) + 6, 40 + CW + SW + 260, 3), 255, np.uint8); rows = []
    for i, s in enumerate(pick):
        y0 = 6 + i * (RH + 6)
        gl = [g for w in s['words'] for g in w['glyphs']] + [m['g'] for w in s['words'] for m in w['marks']]
        P = np.array(s['centre_line']); h = s['h']; m = 2.5 * h + 10
        a0, b0 = int(max(0, P[:, 0].min() - m)), int(max(0, P[:, 1].min() - m)); a1, b1 = int(min(im.shape[1], P[:, 0].max() + m)), int(min(im.shape[0], P[:, 1].max() + m))
        c = (im[b0:b1, a0:a1] * 0.55 + 255 * 0.45).astype(np.uint8)
        own = np.isin(lab[b0:b1, a0:a1], [g + 1 for g in gl]); c[own] = (0, 0, 230)
        cv2.circle(c, (int(P[0][0] - a0), int(P[0][1] - b0)), 4, (230, 0, 0), -1)
        sc = min(RH / c.shape[0], CW / c.shape[1]); c = cv2.resize(c, (max(1, int(c.shape[1] * sc)), max(1, int(c.shape[0] * sc))), interpolation=cv2.INTER_AREA)
        canvas[y0:y0 + c.shape[0], 40:40 + c.shape[1]] = c
        if s['strip']:
            g = cv2.imread(os.path.join(OUT, s['strip']['file']), 0); mm = cv2.imread(os.path.join(OUT, s['strip']['mask']), 0)
            st = np.where(mm > 100, (g * 0.6).astype(np.uint8), (g * 0.35 + 255 * 0.65).astype(np.uint8))
            sc = min((RH - 14) / st.shape[0], SW / st.shape[1]); st = cv2.resize(st, (max(1, int(st.shape[1] * sc)), max(1, int(st.shape[0] * sc))), interpolation=cv2.INTER_AREA)
            canvas[y0 + 7:y0 + 7 + st.shape[0], 50 + CW:50 + CW + st.shape[1]] = st[..., None]
        cv2.putText(canvas, str(i + 1), (4, y0 + 30), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1, cv2.LINE_AA)
        kinds = '/'.join(AB[w['kind']] for w in s['words'])
        cv2.putText(canvas, f"{kinds}"[:30], (60 + CW + SW, y0 + 24), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 0, 0), 1, cv2.LINE_AA)
        cv2.putText(canvas, f"id {s['id']} n{s['n']} h{s['h']:.0f} {s['angle']:+.0f} {s['orient_by'][0]}", (60 + CW + SW, y0 + 44), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (90, 90, 90), 1, cv2.LINE_AA)
        rows.append(dict(row=i + 1, id=s['id'], n=s['n'], h=s['h'], angle=s['angle'], orient_by=s['orient_by'], kinds=[w['kind'] for w in s['words']], centre=[round(float(v), 1) for v in P.mean(0)]))
    cv2.imwrite(os.path.join(OUT, f'audit_{T}.jpg'), canvas, [cv2.IMWRITE_JPEG_QUALITY, 92])
    json.dump(dict(plate=N, tag=T, seed=seed, population=len(S), rows=rows), open(os.path.join(OUT, f'audit_{T}.json'), 'w'), indent=1)
    print(f'{len(pick)} of {len(S)} strings')


if __name__ == '__main__':
    main()
