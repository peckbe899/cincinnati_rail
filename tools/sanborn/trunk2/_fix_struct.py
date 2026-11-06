try: import _ws  # Sanborn paths: tools/sanborn/_ws.py, configs/sanborn_paths.json (was the Topography workspace scratchpad and the chat uploads)
except ImportError: import os as _o, sys as _s; _s.path.append(_o.path.normpath(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..'))); import _ws
p=(_ws.CODE + 'cut/structures.py'); s=open(p).read()
old_a=s[s.index("S_FILL1 = next(float(x)"):s.index("_B22 = json.load(")]
new_a='''_sys.path.insert(0, S + 'trunk2'); import geo4 as _Q          # push of 26 October 2026: the new trunk frame north of Arlington
_FR = LineString(_Q.TR.P)
S_FILL1 = next(float(x) for x in np.arange(G27.S_NSP1, 7200, 5.0) if G27.north_z(x) <= (ground(_Q.TR.at(x)[0]) or 0))
def _cs(l, a, b):                                       # the part of a track between frame chainages a and b
    pts = [q for q in l.coords if a <= _Q.TR.proj(q) <= b and _FR.distance(Point(q)) < 60]
    return LineString(pts) if len(pts) >= 2 else None
fl = [_cs(l, G27.S_NSP1, S_FILL1) for l in lines(lambda p: nm(p).startswith(('APEx Dayton (Southwest Chief)', 'APEx Norwood (Transcontinental)')) or (p.get('layer') == 'lower' and nm(p).endswith('on the fill')))]
fl += [_cs(LineString(t['c']), G27.S_NSP1, S_FILL1) for t in C['tracks'] if t.get('pid') == 'R-B-715612-4338596']
fl = [l for l in fl if l is not None and l.length > 20]
g_fill = deck(fl)
_gd = LineString([_Q.TR.at(x)[0] for x in np.arange(G27.S_NSP1, S_FILL1, 5.0)])
emit(g_fill, 'North trunk fill (Northside / Spring Grove to ground)', 'embankment',
     f'the ORR / Transvalley pairs, RER B and the APEx Dayton and Norwood pairs on fill from the end of the north viaduct at the Northside / Spring Grove (B) platform end (s {G27.S_NSP1:,.0f}, {G27.Z_LUD:.1f} m), '
     f'{100 * G27.G_NFILL:.1f}% down to ground at about s {S_FILL1:,.0f}. Retaining walls or slopes not drawn',
     guide=_gd, tracks='ORR/TV 4, RER B 2, APEx 4')
'''
s=s.replace(old_a,new_a)
s=s.replace("emit(g3, 'North arch viaduct', 'viaduct', 'APEx (6, then 4), the lower-level pairs and the freight passing track from the platform ends to Ludlow, with the RER lines where they run on it (from the RER structure list) and their stations on it',\n     guide=guide3, tracks='APEx 6, lower pairs 4, RER on the viaduct', rer_platforms=len(on))",
"emit(g3, 'North arch viaduct', 'viaduct', 'One level from the CUT platform ends to the Northside / Spring Grove (B) platform end: ORR / Transvalley 2, RER B/D 2, APEx 6 (then 4), ORR / Transvalley 2; the Indianapolis + D upper level west of it with R5 under it; RER stations on it (push of 26 October 2026)',\n     guide=guide3, tracks='ORR/TV 4, RER B 2, APEx 6 then 4; Indianapolis + D upper level, R5 lower', rer_platforms=len(on))")
open(p,'w').write(s)
