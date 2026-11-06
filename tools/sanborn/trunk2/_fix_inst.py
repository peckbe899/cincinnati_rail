p='install.py'; s=open(p).read()
s=s.replace("""    if j <= 2: north = new[np.array([S(q) for q in new]) > 1100] if False else new[1:] if S(new[0]) <= 1100 else new""",
"""    if j <= 2:
        north = new[1:].copy(); cs = np.asarray(F[byname('APEx Cardinal, Floridian (%d of 2)' % j)[0]]['geometry']['coordinates'][0][:2])
        jn = int(np.argmin(np.hypot(*(north - cs).T))); north = np.vstack([north[:jn], cs])""")
s=s.replace("""def half(x):                                                     # half spacing at chainage x (from the north end of south_e)
    dd = max(sW - L_PL / 2 - x, x - (sW + L_PL / 2), 0.0)
    return 7.2 if dd <= 0 else (2.25 + (7.2 - 2.25) * max(0.0, 1 - dd / TAPER))""",
"""def half(x):                                                     # half spacing x m south of the bores' start (the island spacing there), 40 m taper to the 4.5 m pair
    return 2.25 + (7.2 - 2.25) * max(0.0, 1 - x / TAPER)""")
a=s.index("def b_piece("); b=s.index("# north tie: B from s 8,100")
s=s[:a]+'''def side_sort(tt):
    def o(t):
        q = np.asarray(t['c'])[len(t['c']) // 2]; sq = S(q); p = Q.TR.at(sq)[0]; e = Q.TR.at(sq, 1.0)[0] - p; return float((q - p) @ e)
    return sorted(tt, key=o)                                    # west (southbound) first
def b_piece(pid, s0, s1, sub=None):
    sb = bsb[(np.array([S(q) for q in bsb]) >= s0) & (np.array([S(q) for q in bsb]) <= s1)]
    nb = bnb[(np.array([S(q) for q in bnb]) >= s0) & (np.array([S(q) for q in bnb]) <= s1)]
    cen = mid(sb, nb)
    r = RER[pid]; r['c'] = r1(simp(cen[::-1], 0.05)); r['k'] = {}; r.pop('curves', None)
    if sub: r['sub'] = sub
    tt = side_sort(trk(pid)); tt[0]['c'] = r1(simp(sb[::-1], 0.02)); tt[1]['c'] = r1(simp(nb[::-1], 0.02))
'''+s[b:]
s=s.replace("tt = trk('R-B-715612-4338596'); tt[0]['c']","tt = side_sort(trk('R-B-715612-4338596')); tt[0]['c']")
open(p,'w').write(s)
