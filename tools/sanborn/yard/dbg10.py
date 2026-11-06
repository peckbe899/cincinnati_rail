exec(open('build9.py').read().split("xl, fL, _ = through_yard")[0])
LOBE2 = filr([H] + LOBE_PI[:-1] + [(712610.0, 4333100.0)], LOBE_R)
f = CurveFrame(LOBE2); print('L', round(f.L), 'minR', round(radii(LOBE2)))
for t in range(0, int(f.L) + 1, 100):
    xs = [x for x in range(-260, 261, 2) if Point(f.W(x, t)).within(ROOM)]
    p = f.W(0, t)
    print(t, [round(v) for v in p], (min(xs), max(xs)) if xs else None)
print('centres')
for t in range(0, int(f.L) + 1, 100):
    xs = [x for x in range(-260, 261, 2) if Point(f.W(x, t)).within(ROOM)]
    c = (min(xs) + max(xs)) / 2; print(t, [round(v) for v in f.W(c, t)], 'half', (max(xs) - min(xs)) / 2)
