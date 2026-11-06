p='install.py'; s=open(p).read()
old="""R5R = 212.0; i0 = None
for i in range(10, len(cen5) - 10):
    p = cen5[i]; t = cen5[i + 3] - cen5[i - 3]; t /= np.hypot(*t); nr = np.array([t[1], -t[0]]); O = p + nr * R5R
    if abs((O - E5) @ nE - R5R) < 0.3 and ((O - nE * R5R) - E5) @ u2 <= 0: i0 = i; O5 = O; break"""
new="""R5R = 212.0; i0 = None; bestf = 1e9
for i in range(10, len(cen5) - 10):
    p = cen5[i]; t = cen5[i + 3] - cen5[i - 3]; t /= np.hypot(*t); nr = np.array([t[1], -t[0]]); O = p + nr * R5R
    f = abs((O - E5) @ nE - R5R)
    if f < 1.0 and ((O - nE * R5R) - E5) @ u2 <= 0 and f < bestf: bestf = f; i0 = i; O5 = O
rep_r5f = bestf"""
assert old in s; s=s.replace(old,new); open(p,'w').write(s)
