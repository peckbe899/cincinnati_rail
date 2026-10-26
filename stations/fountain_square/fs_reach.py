"""Reachability: floors merged per level (all classes together, as people walk), joined by flights and elevators;
every platform and island must be reachable from the street."""
import numpy as np, networkx as nx
from shapely.geometry import Point
from shapely.ops import unary_union
from fs_model import *
G = nx.Graph(); comps = {}
for lv in (-1, -1.5, -2, -3, -4):
    u = unary_union([p['geom'].buffer(0.3, join_style=2) for p in PARTS if p['level'] == lv])
    comps[lv] = list(u.geoms) if hasattr(u, 'geoms') else [u]
    for i, _ in enumerate(comps[lv]): G.add_node((lv, i))
G.add_node('street')
def find(lv, xy):
    if lv == 0: return 'street'
    for i, q in enumerate(comps[lv]):
        if q.distance(Point(xy)) < 0.5: return (lv, i)
for k, f in enumerate(FLIGHTS):
    a, b = find(f['top'], f['start']), find(f['bot'], f['end'])
    if a is None or b is None: print('flight not landing', k, f['kind'], f['top'], f['bot'], f['start'], f['end'])
    else: G.add_edge(a, b)
for l in LIFTS:
    ns = [find(lv, l['xy']) for lv in l['levels']]
    for a, b in zip(ns[:-1], ns[1:]):
        if a is None or b is None: print('lift not standing', l)
        else: G.add_edge(a, b)
reach = nx.node_connected_component(G, 'street')
bad = 0
for p in PARTS:
    n = find(p['level'], p['geom'].representative_point().coords[0])
    if n not in reach: bad += 1; print('UNREACHABLE:', p['name'], p['level'])
print('components per level:', {lv: len(c) for lv, c in comps.items()}, ' unreachable parts:', bad)
# transfers without leaving the station: drop the street and check every platform shares one component
H = G.copy(); H.remove_node('street')
plat = {p['name']: find(p['level'], p['geom'].representative_point().coords[0]) for p in PARTS if p['kind'] in ('plat', 'island')}
cc = {n: i for i, c in enumerate(nx.connected_components(H)) for n in c}
groups = {}
for nm, n in plat.items(): groups.setdefault(cc[n], []).append(nm)
print('platform groups without the street:', list(groups.values()))
