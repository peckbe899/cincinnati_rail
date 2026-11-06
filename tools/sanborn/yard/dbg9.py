exec(open('build9.py').read().split("xl, fL, _ = through_yard")[0])
fL = CurveFrame(LOBE); sN, bN = MFAN(lat_range(-112.5,112.5), 0.0); sS, bS = MFAN([-x for x in lat_range(-112.5,112.5)], neg(LOBE_XS))
for x in lat_range(-112.5, 112.5):
    t0, t1 = bN[x], fL.L - bS[-x]
    bad = [t for t in range(int(t0), int(t1), 10) if not Point(fL.W(x, t)).within(ROOM)]
    if bad: print(x, 'body', round(t0), round(t1), 'out t', bad[0], bad[-1], [round(v) for v in fL.W(x, bad[0])], [round(v) for v in fL.W(x, bad[-1])])
