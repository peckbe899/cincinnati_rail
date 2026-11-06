src = open('build10.py').read().split("xw = through_yard('Receiving yard'")[0]
exec(src)
for t in (1650, 1690, 1700, 1720, 1750):
    for x in (-70, -76, -81, -86, -90):
        P = Point(fL.W(x, t)); print(t, x, [round(v) for v in fL.W(x, t)], P.within(ROOM), P.within(ROOM0))
fS = CurveFrame(LOBE[::-1])
pl = fS.poly([(81, 600), (81, 620)], 4); print([tuple(round(v) for v in q) for q in pl]); print(LineString(pl).within(ROOM.buffer(0.5)))
print(fL.L, fS.L)
for q in pl: print(q, Point(q).within(ROOM), Point(q).distance(ROOM.boundary))
g = LineString(pl).difference(ROOM); print(g)
Q = Point(712491.55, 4333715.8)
print('block', Q.distance(BLOCK), 'room0', Q.within(ROOM0))
for y, k, l in SEG:
    if l.distance(Q) < 8: print(y, k, round(l.distance(Q), 2), [tuple(round(v) for v in l.coords[0]), tuple(round(v) for v in l.coords[-1])])
hole = box(712300, 4333450, 712620, 4334000).difference(ROOM0)
for g in getattr(hole, 'geoms', [hole]): print('hole', round(g.area), [round(v) for v in g.bounds])
for t in range(1560, 1900, 20):
    xs = [x for x in range(-200, 0, 1) if Point(fL.W(x, t)).within(ROOM0)]
    runs = []; 
    for x in xs:
        if runs and x == runs[-1][1] + 1: runs[-1][1] = x
        else: runs.append([x, x])
    print(t, runs)
