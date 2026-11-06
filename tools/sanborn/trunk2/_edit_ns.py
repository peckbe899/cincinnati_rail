p='geo4.py'; s=open(p).read()
s=s.replace("AN_R = None\ndef build():",'''_GJ = json.load(open(SP + 'trunk2/lud19_geom.json')); S_C0, S_C1 = _GJ['tangents'][3], _GJ['tangents'][4]   # straight C between curves 2 and 3
def ns_curve(o1, o2):
    """after the Northside platform end: one curve from the island offset (concentric on curve 2) onto straight C at the compact offset"""
    p1 = TR.at(S_NS1, o1)[0]; u1 = TR.tan(S_NS1); nin = np.array([u1[1], -u1[0]])
    sm = 0.5 * (S_C0 + S_C1); pc = TR.at(sm, o2)[0]; uc = TR.tan(sm); ncr = np.array([uc[1], -uc[0]])
    R = float(((p1 - pc) @ ncr) / (1 - nin @ ncr)); Oc = p1 + nin * R; tp = Oc - ncr * R
    pend = TR.at(S_C1, o2)[0]
    st = np.array([tp + uc * x for x in np.arange(2.0, float((pend - tp) @ uc), 2.0)] + [pend])
    return R, TR.proj(tp), np.vstack([_arc(Oc, R, p1, tp), st])
AN_R = None
def build():''')
s=s.replace("(S_AN1 - 1, S_AN1, W_N[k]), (S_NS1, S_NS1 + TP_N, c0),","(S_AN1 - 1, S_AN1, W_N[k]), (S_C1 - 1, S_C1, c0),")
s=s.replace("sb = None","sb = None")
s=s.replace("return lambda s: pw(s, [(S_AN1 - 1, S_AN1, B_N[0]), (S_NS1, S_NS1 + TP_N, -11.25),","return lambda s: pw(s, [(S_AN1 - 1, S_AN1, B_N[0]), (S_C1 - 1, S_C1, -11.25),")
s=s.replace("arcn, line(o_w(k), S_LB + 2, 8400)]),","arcn, line(o_w(k), S_LB + 2, S_NS1 - 2), ns_curve(W_N[k], W_C[k])[2], line(o_w(k), S_C1 + 2, 8400)]),")
s=s.replace("arcn, line(o_b(k), S_LB + 2, 8400)]), kind='rer'","arcn, line(o_b(k), S_LB + 2, S_NS1 - 2)] + ([ns_curve(B_N[0], -11.25)[2]] if k == 0 else []) + [line(o_b(k), (S_C1 + 2) if k == 0 else S_NS1, 8400)]), kind='rer'")
open(p,'w').write(s)
