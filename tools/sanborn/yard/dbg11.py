src = open('build10b.py').read().split("xb_ = through_yard('Sorting yard (hump)'")[0]
exec(src)
print('L', round(fL.L))
for t in range(0, int(fL.L) + 1, 100):
    xs = [x for x in range(-260, 261, 2) if Point(fL.W(x, t)).within(ROOM)]
    runs = []
    for x in xs:
        if runs and x == runs[-1][1] + 2: runs[-1][1] = x
        else: runs.append([x, x])
    print(t, [round(v) for v in fL.W(0, t)], runs)
