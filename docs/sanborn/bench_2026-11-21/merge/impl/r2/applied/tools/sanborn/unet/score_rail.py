"""Score the rules' two rail bins against the tracks Ben drew in the line editor (18 November 2026).

    cd data/sanborn
    python ../../tools/sanborn/unet/ink_bins.py N --no-ben --save RULE.png      (the rules alone, without his tracks)
    python ../../tools/sanborn/unet/score_rail.py N RULE.png OUT.jpg

Ben, 18 November 2026: "i need to tell you where they are, you're missing a lot". His tracks
(picks22_guided/22-N/rail_ben.json) are the truth. For each track: its length, how much of it the rules had found
(rule ink of that kind within 10 px for a railroad, 30 px for a streetcar, whose dashes have gaps), and how far the
print's ink lies from his line. Then what the rules call rail more than 25 px from every track of his, by place.
OUT.jpg is the plate at quarter size: railroad found green, missed red; streetcar found blue, missed magenta; the
rules' rail away from his tracks orange (railroad) and purple (streetcar). Track numbers are their order in the file.
"""
import sys, json, numpy as np, cv2
N, rule_png, out = sys.argv[1:4]
R = cv2.imread(rule_png, 0); H, W = R.shape
im = cv2.imread(f'cufp/22-{N}.jpg'); ink = cv2.cvtColor(im, cv2.COLOR_BGR2LAB)[..., 0] < 140
T = json.load(open(f'picks22_guided/22-{N}/rail_ben.json'))['tracks']
dist = lambda m: cv2.distanceTransform((~m).astype(np.uint8), cv2.DIST_L2, 5)
D = {'railroad': dist(R == 4), 'streetcar': dist(R == 5)}; Dink = dist(ink); TOL = {'railroad': 10, 'streetcar': 30}   # a streetcar is dashes with gaps between them
c = (im * 0.3 + 255 * 0.7).astype(np.uint8); tot = {k: [0, 0, 0] for k in D}; rows = []
band = {k: np.zeros((H, W), np.uint8) for k in D}
for ti, t in enumerate(T):
    p = np.array(t['pts'], float); k = t['kind']; S = []
    for q0, q1 in zip(p[:-1], p[1:]):
        L = np.hypot(*(q1 - q0)); S.append(q0[None] + np.linspace(0, 1, max(2, int(L / 4) + 1))[:, None] * (q1 - q0)[None])
    S = np.vstack(S); L = sum(np.hypot(*(p[i + 1] - p[i])) for i in range(len(p) - 1))
    q = S.round().astype(int); ok = (q[:, 0] >= 0) & (q[:, 0] < W) & (q[:, 1] >= 0) & (q[:, 1] < H); q = q[ok]
    found = D[k][q[:, 1], q[:, 0]] <= TOL[k]; offink = Dink[q[:, 1], q[:, 0]]
    tot[k][0] += L; tot[k][1] += L * found.mean(); tot[k][2] += 1
    rows.append((k, ti, L, found.mean(), np.median(offink), np.percentile(offink, 90), p[0], p[-1]))
    cv2.polylines(band[k], [p.round().astype(np.int32)], False, 1, 51)
    for (x, y), f in zip(q, found): cv2.circle(c, (int(x), int(y)), 9, ((0, 160, 0) if f else (0, 0, 255)) if k == 'railroad' else ((200, 120, 0) if f else (255, 0, 255)), -1)
    cv2.putText(c, str(ti), (int(p[0][0]) + 20, int(p[0][1]) - 20), cv2.FONT_HERSHEY_SIMPLEX, 3, (0, 0, 0), 8)
for k, ti, L, f, mo, p90, a, b in sorted(rows, key=lambda r: (r[0], -r[2])):
    print(f'{k:9s} #{ti:2d} {L:6.0f} px  found {100 * f:5.1f}%  missed {L * (1 - f):6.0f} px   ink off the line: median {mo:4.1f} px, 90% within {p90:4.1f}   ({a[0]:.0f},{a[1]:.0f}) to ({b[0]:.0f},{b[1]:.0f})')
for k in D:
    print(f'{k}: {tot[k][2]} tracks, {tot[k][0]:.0f} px drawn, rule found {tot[k][1]:.0f} px = {100 * tot[k][1] / max(1, tot[k][0]):.1f}%')
    far = (R == (4 if k == 'railroad' else 5)) & (band[k] == 0); n, lb, st, ce = cv2.connectedComponentsWithStats(cv2.dilate(far.astype(np.uint8), np.ones((41, 41), np.uint8)))
    print(f"  rule's {k} ink in all {(R == (4 if k == 'railroad' else 5)).sum()} px; more than 25 px from every {k} track of Ben's: {far.sum()} px in {n - 1} places")
    other = band['streetcar' if k == 'railroad' else 'railroad'] > 0; print(f"    of that, on a track Ben drew as the other kind: {(far & other).sum()} px")
    c[far] = (0, 140, 255) if k == 'railroad' else (150, 0, 150)
    for i in np.argsort(-st[1:, 4])[:12] + 1: print(f'    place at ({ce[i][0]:.0f},{ce[i][1]:.0f}) {int((far & (lb == i)).sum())} px')
cv2.imwrite(out, cv2.resize(c, None, fx=0.25, fy=0.25, interpolation=cv2.INTER_AREA), [cv2.IMWRITE_JPEG_QUALITY, 88])
