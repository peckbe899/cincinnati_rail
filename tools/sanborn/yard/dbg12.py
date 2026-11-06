import sys; sys.argv = ['x', '150']
src = open('build12.py').read().split("xw = through_yard('Receiving yard'")[0]
exec(src)
pl = LineString(fL.poly([(126, 1850), (126, 1870)], 4))
print('t_s1', t_s1, 'in room', pl.within(ROOM.buffer(0.5)), 'in ROOM0', pl.within(ROOM0))
bad = pl.difference(ROOM.buffer(0.5)); print(bad)
q = bad.centroid
for y, k, l in SEG:
    if l.distance(q) < 10: print(y, k, round(l.distance(q), 1))
print('leadE dist', leadE.distance(q), 'hump', hump.distance(q), 'P_PATH', LineString(P_PATH).distance(q))
for t in (1840, 1850, 1860, 1870): print(t, [x for x in range(100, 160, 2) if Point(fL.W(x, t)).within(ROOM)][:3], [x for x in range(100, 200, 2) if Point(fL.W(x, t)).within(ROOM)][-3:])
