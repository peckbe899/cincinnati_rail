"""Census step 1b (second pass): inset scale notes, lettered smaller than the sheet's own note (21 Nov 2026).

Same templates as scale_find.py at 0.45-0.75 of their size; keeps hits >= 0.6 away from the main note found before.
    python scale_insets.py   -> scale/insets.json, scale/insets_*.jpg (crops to read by eye)
"""
import json, os, re
import numpy as np, cv2
from scale_find import pdf_of, sheet, TPL, OUT, state

if __name__ == '__main__':
    find = json.load(open(OUT + '/find.json')); res = {}; crops = []
    seen = {}
    for n in sorted(state, key=lambda n: (int(re.match(r'\d+', n).group()), n)):
        pdf = pdf_of(n)
        if pdf in seen: res[n] = dict(same_sheet_as=seen[pdf], hits=res[seen[pdf]]['hits']); continue
        seen[pdf] = n
        a, fs, _, _ = sheet(pdf); g = cv2.cvtColor(cv2.resize(a, None, fx=0.5, fy=0.5, interpolation=cv2.INTER_AREA), cv2.COLOR_BGR2GRAY)
        main = find[n]['hits'][0] if find.get(n, {}).get('hits') else None
        hits = []
        for name, t in TPL.items():
            for s in (0.45, 0.52, 0.6, 0.68, 0.75):
                tt = cv2.resize(t, None, fx=s, fy=s, interpolation=cv2.INTER_AREA); r = cv2.matchTemplate(g, tt, cv2.TM_CCOEFF_NORMED)
                for _ in range(4):
                    _, v, _, p = cv2.minMaxLoc(r)
                    if v < 0.6: break
                    hits.append((float(v), name, s, p[0] * 4, p[1] * 4)); cv2.rectangle(r, (p[0] - tt.shape[1], p[1] - tt.shape[0]), (p[0] + tt.shape[1], p[1] + tt.shape[0]), -1, -1)
        hits.sort(reverse=True); keep = []
        for h in hits:
            if main and abs(h[3] - main['x']) < 1600 and abs(h[4] - main['y']) < 300: continue
            if all(abs(h[3] - k[3]) > 1200 or abs(h[4] - k[4]) > 250 for k in keep): keep.append(h)
        res[n] = dict(hits=[dict(score=round(h[0], 3), word=h[1], scale=h[2], x=h[3], y=h[4]) for h in keep[:4]])
        for k, h in enumerate(keep[:4]):
            x, y = h[3], h[4]; x0 = x - (150 if h[1] == 'SCALE' else 900); x1 = x + (1100 if h[1] == 'SCALE' else 450)
            c = a[max(0, (y - 90) // 2):(y + 180) // 2, max(0, x0 // 2):max(0, x1 // 2)]
            if c.size == 0: continue
            c = cv2.resize(c, (700, int(700 * c.shape[0] / c.shape[1])), interpolation=cv2.INTER_AREA); c = cv2.copyMakeBorder(c, 0, 0, 150, 0, cv2.BORDER_CONSTANT, value=(255, 255, 255))
            cv2.putText(c, n, (4, 40), cv2.FONT_HERSHEY_SIMPLEX, 1.1, (0, 0, 255), 3); cv2.putText(c, f'{k}:{h[0]:.2f}', (4, 85), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 0, 0), 2); crops.append(c)
        print(n, [(round(h[0], 2), h[1], h[2], h[3], h[4]) for h in keep[:4]], flush=True)
    json.dump(res, open(OUT + '/insets.json', 'w'), indent=1)
    if crops:
        W = max(c.shape[1] for c in crops); crops = [cv2.copyMakeBorder(c, 0, 4, 0, W - c.shape[1], cv2.BORDER_CONSTANT, value=(0, 0, 0)) for c in crops]
        for k in range(0, len(crops), 16): cv2.imwrite(OUT + f'/insets_{k // 16:02d}.jpg', np.vstack(crops[k:k + 16]), [cv2.IMWRITE_JPEG_QUALITY, 85])
