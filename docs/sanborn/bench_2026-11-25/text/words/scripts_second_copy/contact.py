"""Contact sheets of rectified strips, for the shapes agent and for Ben.

    cd data/sanborn
    python -B bench_2026-11-25/text/words/scripts/contact.py [TAG ...] [--n 200] [--seed 7] [--prefix contact]

Picks N strings (default 200) from the given plates' out/P_words.json (strings of 2+ pieces, or one piece of several
touching characters, not junk), spread over the plates and the kinds (each kind gets an equal share of a plate's
quota where it has enough strings; the rest is random), and draws each strip scaled to 40 px high, its own ink dark
and other ink faded, with a label: plate, phrase id, kinds of its words, reading angle (degrees anticlockwise from
east), how the way-up was decided (S shapes, R rule) and whether the centre line is curved (C).
Writes out/contact_K.jpg (50 strips each) and out/contact_index.json (which strip is where)."""
import json, os, sys
import numpy as np
import cv2
HERE = os.path.dirname(os.path.abspath(__file__)); OUT = os.path.join(os.path.dirname(HERE), 'out')
AB = dict(street_name='ST', house_number='HN', lot_dimension='LD', block_number='BN', pipe_label='PL', lot_number='LN',
          owner_or_note='ON', story_or_single='1', other='?', junk='x')
SH = 40; MAXW = 470; LW = 175; ROWS = 25; COLS = 2


def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    n = int(sys.argv[sys.argv.index('--n') + 1]) if '--n' in sys.argv else 200
    seed = int(sys.argv[sys.argv.index('--seed') + 1]) if '--seed' in sys.argv else 7
    if '--n' in sys.argv: args = [a for a in args if a != str(n)]
    if '--seed' in sys.argv: args = [a for a in args if a != str(seed)]
    pre = sys.argv[sys.argv.index('--prefix') + 1] if '--prefix' in sys.argv else 'contact'
    if '--prefix' in sys.argv: args = [a for a in args if a != pre]
    plates = args or ['44', '5', '1A', '90']
    rng = np.random.default_rng(seed)
    pick = []
    per = n // len(plates)
    for i, N in enumerate(plates):
        J = json.load(open(os.path.join(OUT, f'{N}_words.json'), encoding='utf8'))
        S = [s for s in J['strings'] if s['strip'] and any(w['kind'] != 'junk' for w in s['words'])]
        q = per + (n - per * len(plates) if i == len(plates) - 1 else 0)
        by = {}
        for s in S:
            k = max(set(w['kind'] for w in s['words']), key=lambda k: sum(w['kind'] == k for w in s['words']))
            by.setdefault(k, []).append(s)
        kinds = sorted(by); share = max(1, q // (len(kinds) + 2)); got = []
        curved = [s for s in S if s['kind_line'] == 'curve']
        for s in rng.permutation(len(curved))[:3]: got.append(curved[s])      # a few curved centre lines on each plate
        for k in kinds:
            L = by[k]; ids = rng.permutation(len(L))[:share]; got += [L[j] for j in ids]
        rest = [s for s in S if s not in got]
        for j in rng.permutation(len(rest))[:max(0, q - len(got))]: got.append(rest[j])
        uniq = []; seen = set()
        for s in got:
            if s['id'] not in seen: seen.add(s['id']); uniq.append(s)
        pick += [(N, s) for s in uniq[:q]]
    index = []
    sheets = [pick[i:i + ROWS * COLS] for i in range(0, len(pick), ROWS * COLS)]
    for si, sh in enumerate(sheets):
        H = ROWS * (SH + 10) + 10; Wd = COLS * (LW + MAXW + 10) + 10
        canvas = np.full((H, Wd, 3), 255, np.uint8)
        for k, (N, s) in enumerate(sh):
            r, c = k % ROWS, k // ROWS
            y = 10 + r * (SH + 10); x = 10 + c * (LW + MAXW + 10)
            g = cv2.imread(os.path.join(OUT, s['strip']['file']), 0); m = cv2.imread(os.path.join(OUT, s['strip']['mask']), 0)
            if g is None or m is None: continue
            img = np.where(m > 100, (g * 0.6).astype(np.uint8), (g * 0.35 + 255 * 0.65).astype(np.uint8))
            sc = SH / img.shape[0]; w = int(round(img.shape[1] * sc))
            img = cv2.resize(img, (max(1, w), SH), interpolation=cv2.INTER_AREA)
            if img.shape[1] > MAXW: img = img[:, :MAXW]
            canvas[y:y + SH, x + LW:x + LW + img.shape[1]] = img[..., None]
            cv2.rectangle(canvas, (x + LW - 1, y - 1), (x + LW + img.shape[1], y + SH), (200, 200, 200), 1)
            kinds = '/'.join(AB[w['kind']] for w in s['words'])
            lab1 = f"{N}:{s['id']} {kinds}"[:24]
            lab2 = f"{s['angle']:+.0f} {'S' if s['orient_by'] == 'shapes' else 'R'}{' C' if s['kind_line'] == 'curve' else ''} h{s['h']:.0f}"
            cv2.putText(canvas, lab1, (x, y + 15), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (0, 0, 0), 1, cv2.LINE_AA)
            cv2.putText(canvas, lab2, (x, y + 33), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (90, 90, 90), 1, cv2.LINE_AA)
            index.append(dict(sheet=si, row=r, col=c, plate=N, id=s['id'], kinds=[w['kind'] for w in s['words']], angle=s['angle'],
                              orient_by=s['orient_by'], curve=s['kind_line'] == 'curve', h=s['h'], strip=s['strip']['file']))
        cv2.imwrite(os.path.join(OUT, f'{pre}_{si + 1}.jpg'), canvas, [cv2.IMWRITE_JPEG_QUALITY, 92])
    json.dump(dict(seed=seed, plates=plates, n=len(index), strips=index), open(os.path.join(OUT, f'{pre}_index.json'), 'w', encoding='utf8'), indent=1)
    print(f'{len(index)} strips on {len(sheets)} sheets')


if __name__ == '__main__':
    main()
