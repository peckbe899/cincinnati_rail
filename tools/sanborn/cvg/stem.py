try: import _ws  # Sanborn paths: tools/sanborn/_ws.py, configs/sanborn_paths.json (was the Topography workspace scratchpad and the chat uploads)
except ImportError: import os as _o, sys as _s; _s.path.append(_o.path.normpath(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..'))); import _ws
# Ben (18 October): shorten T1A's south stem until Pan Am (T1A + T1B) has 60 stands. Fixed terminal order with T1A last, so the stem does not change the others.
import json, sys, subprocess, os
S = _ws.DATA
sys.argv = [sys.argv[0]] + sys.argv[1:]
BASE = json.load(open(S + 'cvg/gates_params7.json'))
E0, E1 = (701384.5, 4326052), (701417.1601208459, 4324850)
W0, W1 = (701335, 4326278), (701379.0454545454, 4324850)
def xat(a, b, y): return a[0] + (b[0] - a[0]) * (y - a[1]) / (b[1] - a[1])
def params(Y):
    P = json.loads(json.dumps(BASE)); c = P['replace']['Terminal 1A']
    i = c.index([701417.1601208459, 4324850]); j = c.index([701379.0454545454, 4324850])
    c[i] = [xat(E0, E1, Y), Y]; c[j] = [xat(W0, W1, Y), Y]
    WX = float(os.environ.get('WEST', '0'))            # T1A west end carried further west (Ben, 18 October)
    for q in c:
        if q[0] < 700835: q[0] -= WX
    P['zones'] = [z for z in P.get('zones', []) if not z.get('block')] + [{'term': 'Terminal 1A', 'pref': [], 'block': True, 'poly': [[701250, 4324000], [701550, 4324000], [701550, Y], [701250, Y]], 'note': 'no stand off the stem tip'}]
    if WX: P['note9'] = f'18 October (Ben): angled stand off the T1A stem tip removed; T1A west end carried {WX:.0f} m west'
    return P
def count(Y, order, tag):
    P = params(Y); pf = f'cvg/_stem_{tag}.json'; json.dump(P, open(S + pf, 'w'))
    import importlib; sys.argv = ['gates.py', 'LS', f'cvg/_gs_{tag}.json', pf]
    g = {'__name__': 'x'}; exec(open(_ws.CODE + 'cvg/gates.py').read(), g)
    r = g['run'](order, ('L', 'S'))
    from shapely.geometry import mapping
    tab = {}
    for x in r: d_ = tab.setdefault(x['term'], {}); d_[x['cls']] = d_.get(x['cls'], 0) + 1
    json.dump(dict(order=order, params=P, by_terminal=tab, stands=[dict(term=x['term'], cls=x['cls'], env=mapping(x['env']), tail=mapping(x['tail'])) for x in r]), open(S + f'cvg/_gs_{tag}.json', 'w'), default=float)
    return tab
if __name__ == '__main__':
    order = json.loads(sys.argv[1]); 
    for Y in [float(v) for v in sys.argv[2].split(',')]:
        t = count(Y, order, str(int(Y)))
        pa = sum(t.get('Terminal 1A', {}).values()) + sum(t.get('Terminal 1B', {}).values())
        print(int(Y), 'PanAm', pa, json.dumps(t), flush=True)
