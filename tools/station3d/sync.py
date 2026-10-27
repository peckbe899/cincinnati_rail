"""Station 3D sync: one snapshot of the region from the Rail Profiles editor and the Mill Creek Deck.

The editors' published files and saved records are fetched first by a Claude session (Artifact read, ArtifactData
with out_dir) into CACHE (see README.md). This script runs both editors headless (harness.js) so the levels,
structure types, tracks and platforms come from the editors' own code, and writes snapshot.json and the page's
database documents (cache/db_out/). Coordinates are metres, x east and y north (true) from the origin (the Fountain
Square model's reference point); z is the elevation in metres (NAVD88, as the editors). Point lists are stored as
integer deltas (see enc) to keep the documents small.

Usage: python3 sync.py [--cache DIR] [--out snapshot.json]
"""
import argparse
import json
import math
import os
import subprocess
import sys
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))

# The region the Mill Creek Deck draws its lines over (its Region button: "RER and APEx are drawn out to Erlanger, CVG,
# Eastgate and Aviation", E 699,000-736,900, N 4,320,800-4,347,000, UTM 16N). Origin: the Fountain Square model's
# reference point (stations/fountain_square/README.md), whose frame is turned 11 degrees with the street grid.
AREA = dict(id='region', name='Cincinnati region', lon=-84.5125, lat=39.1018, frame_turn=-11.0,
            box_utm=(699000.0, 4320800.0, 736900.0, 4347000.0), default_station='Fountain Square')
STEP = 5.0             # Profiles sampling along each line, m
TRACK_STEP = 10.0      # Deck tracks resampled to this spacing, m
MATCH_M = 30.0         # a Deck track point takes a Profiles line's level within this distance
SNAP_SMOOTH_M = 40.0   # the centre's shift is averaged over this distance either side
SNAP_TAPER_M = 150.0   # past its Deck tracks a line's centre returns to the Profiles path over this distance
TRACK_MATCH_M = 120.0  # a Deck track takes its own line's level within this distance (the Deck and the Profiles paths differ)
INTERLINE_M = 60.0     # an interlined line (D on the A/D pair) is drawn by the pair within this distance of it
STRIPE_M = 30.0        # interlined pairs: stripe length in each line's colour, m
GRID = 200.0           # ground grid spacing, m

# Platform lengths (Ben, 2026-10-26): Metro 400 ft, TRI 670 ft. The Profiles editor's RER default is 200 m.
PLATFORM_M = {'metro': 121.92, 'rer': 204.216}
PLATFORM_ABOVE_RAIL = {'metro': 1.0, 'rer': 1.0}   # platform top above the rail: assumption, not in the editors

# Structure sizes measured from the rail (Rail Profiles editor: METRO_ST, RER_DEFAULTS). Track positions come from the
# Mill Creek Deck (its trackPair: Metro bored tubes 8.0 m apart, box 3.9 m, islands spread; TRI 4.5 m). Neither editor
# sets a box's width or a TRI tube's diameter: those are assumptions, marked in the snapshot. Tube spacing below is only
# used where a line has no Deck tracks.
METRO_ST = {
    'box': dict(k='box', below=1.0, top=4.6, cover=0.6, width=8.5),
    'tube': dict(k='tube', below=0.68, top=4.08, od=4.76, spacing=8.0),
    'bore': dict(k='bore', below=3.2, top=5.8, od=9.0),
}
RER_ST = {
    'box': dict(k='box', below=1.0, top=6.6, width=11.0),
    'bore': dict(k='tube', below=1.0, top=7.5, od=8.5, spacing=4.5),
}
OPEN_ST = dict(k='open', below=0.8, top=0.0, width=9.0)
ERA_SHIELD = {**{f'Line_{k}': 'tube' for k in ['1', '2', '2b', '3', '4', '5', '6', '7']},
              **{f'Line_{k}': 'bore' for k in ['8', '9', '10', '11', '12', '13', '14']}, 'CVG_Express': 'bore'}
BOX_MARGIN = {'metro': 2.3, 'rer': 3.25}   # box wall outside the outer track centre (8.5 m at 3.9 m centres; 11 m at 4.5 m)
ASSUMED = ['box walls 2.3 m (Metro) and 3.25 m (TRI) outside the outer track centre: 8.5 m and 11 m wide boxes between stations',
           'TRI bored tubes 8.5 m outside diameter, one per track', 'platform tops 1.0 m above the rail',
           'ground: a 200 m grid averaged from the Profiles ground along every line, filled out to 1.6 km from the lines']
# RER line to TRI letter (rer/canon.json: RER-n is TRI by KMZ colour, 1 A ... 5 E)
RER_LETTER = {'RER_1': 'A', 'RER_2': 'B', 'RER_3': 'C', 'RER_4': 'D', 'RER_5': 'E'}
LETTER_RER = {v: k for k, v in RER_LETTER.items()}


def structure(line_id, t):
    """the structure a line has for a Profiles type (the editor's structFor, river crossings aside)"""
    if t in ('elevated', 'atgrade', 'trough'):
        return dict(OPEN_ST, t=t)
    if line_id.startswith('RER_'):
        return dict(RER_ST['box' if t == 'cutcover' else 'bore'])
    if t == 'cutcover':
        return dict(METRO_ST['box'])
    if t == 'deep':
        return dict(METRO_ST['tube'])
    return dict(METRO_ST[ERA_SHIELD.get(line_id, 'tube')])


# ---- UTM zone 16N (EPSG:32616), Krueger series ----
_A, _F = 6378137.0, 1 / 298.257223563
_N = _F / (2 - _F)
_AA = _A / (1 + _N) * (1 + _N ** 2 / 4 + _N ** 4 / 64)
_ALPHA = [_N / 2 - 2 * _N ** 2 / 3 + 5 * _N ** 3 / 16, 13 * _N ** 2 / 48 - 3 * _N ** 3 / 5, 61 * _N ** 3 / 240]
_BETA = [_N / 2 - 2 * _N ** 2 / 3 + 37 * _N ** 3 / 96, _N ** 2 / 48 + _N ** 3 / 15, 17 * _N ** 3 / 480]
_DELTA = [2 * _N - 2 * _N ** 2 / 3 - 2 * _N ** 3, 7 * _N ** 2 / 3 - 8 * _N ** 3 / 5, 56 * _N ** 3 / 15]
_K0, _E0, _LON0 = 0.9996, 500000.0, math.radians(-87.0)


def ll_to_utm(lon, lat):
    lon, lat = np.radians(np.asarray(lon, float)), np.radians(np.asarray(lat, float))
    e = 2 * math.sqrt(_N) / (1 + _N)
    t = np.sinh(np.arctanh(np.sin(lat)) - e * np.arctanh(e * np.sin(lat)))
    dl = lon - _LON0
    xi, eta = np.arctan(t / np.cos(dl)), np.arctanh(np.sin(dl) / np.sqrt(1 + t * t))
    E = eta + sum(a * np.cos(2 * j * xi) * np.sinh(2 * j * eta) for j, a in enumerate(_ALPHA, 1))
    N = xi + sum(a * np.sin(2 * j * xi) * np.cosh(2 * j * eta) for j, a in enumerate(_ALPHA, 1))
    return _E0 + _K0 * _AA * E, _K0 * _AA * N


def utm_to_ll(E, N):
    xi, eta = np.asarray(N, float) / (_K0 * _AA), (np.asarray(E, float) - _E0) / (_K0 * _AA)
    xp = xi - sum(b * np.sin(2 * j * xi) * np.cosh(2 * j * eta) for j, b in enumerate(_BETA, 1))
    ep = eta - sum(b * np.cos(2 * j * xi) * np.sinh(2 * j * eta) for j, b in enumerate(_BETA, 1))
    chi = np.arcsin(np.sin(xp) / np.cosh(ep))
    lat = chi + sum(d * np.sin(2 * j * chi) for j, d in enumerate(_DELTA, 1))
    return np.degrees(_LON0 + np.arctan(np.sinh(ep) / np.cos(xp))), np.degrees(lat)



# ---- encoding ----
def enc(vals, scale):
    """integers at 1/scale, the first absolute and the rest as differences (the page's dec() undoes it)"""
    out, prev = [], 0
    for v in vals:
        q = int(round(float(v) * scale))
        out.append(q - prev)
        prev = q
    return out


def rle(vals):
    """run-length list [[count, value], ...]"""
    out = []
    for v in vals:
        if out and out[-1][1] == v:
            out[-1][0] += 1
        else:
            out.append([1, v])
    return out


def r1(v):
    return round(float(v), 1)


def r2(v):
    return round(float(v), 2)


# ---- nearest points on lines, by a spatial hash ----
class Near:
    """points (x, y) with a payload; nearest within a radius"""

    def __init__(self, cell=50.0):
        self.cell, self.h = cell, {}

    def add(self, x, y, item):
        self.h.setdefault((int(x // self.cell), int(y // self.cell)), []).append((x, y, item))

    def near(self, x, y, r):
        cx, cy, k = int(x // self.cell), int(y // self.cell), int(math.ceil(r / self.cell))
        best, bd = None, r
        for i in range(cx - k, cx + k + 1):
            for j in range(cy - k, cy + k + 1):
                for px, py, it in self.h.get((i, j), ()):
                    d = math.hypot(px - x, py - y)
                    if d <= bd:
                        best, bd = it, d
        return best, bd


def on_line(P, i, q):
    """chainage, signed offset (+ left) and distance of q on the segments either side of sample i of P [[c, x, y]]"""
    best = None
    for k in (i - 1, i):
        if k < 0 or k + 1 >= len(P):
            continue
        (c0, ax, ay), (c1, bx, by) = P[k], P[k + 1]
        dx, dy = bx - ax, by - ay
        L2 = dx * dx + dy * dy
        if L2 < 1e-9:
            continue
        s = min(1.0, max(0.0, ((q[0] - ax) * dx + (q[1] - ay) * dy) / L2))
        px, py = ax + s * dx, ay + s * dy
        d = math.hypot(q[0] - px, q[1] - py)
        if best is None or d < best[2]:
            best = (c0 + s * (c1 - c0), (dx * (q[1] - ay) - dy * (q[0] - ax)) / math.sqrt(L2), d)
    return best


def resample(c, step):
    """a polyline resampled to about `step` spacing (its corners kept)"""
    c = [tuple(map(float, q)) for q in c]
    out = [c[0]]
    for a, b in zip(c, c[1:]):
        L = math.hypot(b[0] - a[0], b[1] - a[1])
        n = max(1, int(L // step))
        for k in range(1, n + 1):
            f = k / n
            out.append((a[0] + f * (b[0] - a[0]), a[1] + f * (b[1] - a[1])))
    return out


def load_lines(cache, overlay=None):
    out = {}
    for sysk, idx in (('metro', 'lines/index.json'), ('rer', 'rer/lines/index.json')):
        rd = lambda rel: json.load(open((overlay or {}).get(rel) or os.path.join(cache, 'profiles', rel)))
        for l in rd(idx):
            d = rd(os.path.dirname(idx) + '/' + l['id'] + '.json')
            d['sys'] = 'cvx' if l['id'] == 'CVG_Express' else sysk
            out[l['id']] = d
    return out


def deck_ids(sys_, label, by_id):
    """the Profiles lines a Deck line label stands for: 'Metro Line 7' / 'Line 7'; 'RER A/D', 'B C E', 'A'; CVG Express"""
    label = label or ''
    if sys_ == 'cvx' or label.startswith('CVG'):
        ids = ['CVG_Express']
    elif sys_ == 'metro':
        ids = ['Line_' + label.split('Line ')[-1].strip()] if 'Line ' in label else []
    else:
        letters = label.replace('RER', '').replace('/', ' ').split()
        ids = [LETTER_RER[x] for x in letters if x in LETTER_RER]
    return [i for i in ids if i in by_id]


# Repo profiles the editor has not saved, served to it as if saved (and listed as issues): RER-4 north of Camp
# Washington is tied to the Deck's APEx level (Ben, 2026-10-27; tools/make_rer4_upper.py).
REPO_PROFILES = {'RER_4': 'data/profile/rer/alignments/RER_4.json'}


def repo_docs(cache):
    out = {}
    saved = os.path.join(cache, 'db/profiles_db/alignments')
    for lid, rel in REPO_PROFILES.items():
        f = os.path.join(HERE, '..', '..', rel)
        if os.path.exists(f) and not os.path.exists(os.path.join(saved, lid + '.json')):
            out['alignments/' + lid] = json.load(open(f))
    return out


# Repo line files served in place of the editor's published ones while it still has the old paths: RER-2 and RER-4 on
# the Deck's B/D route (Ben, 2026-10-27; tools/repath_rer_bd_trunk.py). Saved profiles made on the old paths are moved
# with the re-path's chainage map.
REPATH = 'data/profile/rer/repath_bd_trunk.json'


def repath(cache):
    """({published path: repo file}, {line: chainage map}) while the published lines are the old paths"""
    f = os.path.join(HERE, '..', '..', REPATH)
    if not os.path.exists(f):
        return {}, {}
    m = json.load(open(f))
    pub = json.load(open(os.path.join(cache, 'profiles/rer/lines/index.json')))
    old = {l['id'] for l in pub if l['id'] in m and abs(l['length_m'] - m[l['id']]['L0']) < 0.05}
    if not old:
        return {}, {}
    return {rel: os.path.join(HERE, '..', '..', 'data/profile', rel) for rel in m['files']}, {lid: m[lid] for lid in old}


def moved_docs(cache, maps, lines):
    """the editor's saved profiles on the old paths, moved onto the re-pathed lines"""
    out = {}
    for lid, s in maps.items():
        f = os.path.join(cache, 'db/profiles_db/alignments', lid + '.json')
        if not os.path.exists(f):
            continue
        d = json.load(open(f))
        if abs(d.get('length_m', 0) - s['L0']) > 0.05:
            continue
        mv = lambda c: round(c if c <= s['ca'] else c + s['delta'] if c >= s['cb'] else s['ca'] + (c - s['ca']) * s['dn'] / (s['cb'] - s['ca']), 1)
        d['pvi'] = [[mv(c), z] for c, z in d.get('pvi', [])]
        d['ovr'] = [[mv(r[0]), mv(r[1]), *r[2:]] for r in d.get('ovr', [])]
        nc = {x['name']: x['c'] for x in lines[lid]['stations']}
        for x in d.get('stations', []):
            x['c'] = x['point_c'] = nc.get(x['name'], mv(x['c']))
        d['length_m'] = lines[lid]['length_m']
        out['alignments/' + lid] = d
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--cache', default=os.path.join(HERE, 'cache'))
    ap.add_argument('--out', default=os.path.join(HERE, 'cache', 'snapshot.json'))
    ap.add_argument('--skip-harness', action='store_true', help='reuse cache/harness_out.json')
    a = ap.parse_args()
    E0, N0 = (float(v) for v in ll_to_utm(AREA['lon'], AREA['lat']))
    bx0, by0, bx1, by1 = AREA['box_utm']
    BOX = (bx0 - E0, by0 - N0, bx1 - E0, by1 - N0)
    inbox = lambda x, y: BOX[0] <= x <= BOX[2] and BOX[1] <= y <= BOX[3]

    overlay, maps = repath(a.cache)
    lines = load_lines(a.cache, overlay)
    jf, rf = os.path.join(a.cache, 'job.json'), os.path.join(a.cache, 'harness_out.json')
    if not a.skip_harness:
        job = {'lines': [{'id': lid, 'c0': 0.0, 'c1': float(d['length_m']), 'step': STEP} for lid, d in lines.items()], 'deck': True,
               'extra_docs': repo_docs(a.cache), 'override_docs': moved_docs(a.cache, maps, lines),
               'overlay': {k: os.path.abspath(v) for k, v in overlay.items()}}
        json.dump(job, open(jf, 'w'))
        subprocess.run(['node', os.path.join(HERE, 'harness.js'), a.cache, jf, rf], check=True)
    H = json.load(open(rf))
    issues = []
    if maps:
        issues.append(', '.join(lines[l]['line'] for l in sorted(maps)) + ": paths from the repo, re-pathed onto the Deck's B/D route from the "
                      "trunk to Union Terminal (Ben, 2026-10-27; tools/repath_rer_bd_trunk.py); the Rail Profiles editor still has the old "
                      "KMZ paths until it is republished, and saved profiles are moved along")

    # ---- Profiles lines: every sample inside the region, in pieces where a line leaves and re-enters it ----
    L = {}
    ground_pts = []
    for lid, d in lines.items():
        h = H['profiles'][lid]
        p = np.array(d['path'], float)
        E, N = ll_to_utm(p[:, 1], p[:, 2])
        xy = np.c_[E - E0, N - N0]
        g = np.array([np.nan if v is None else v / 10 for v in d['ground_dm']])
        gc = np.arange(len(g)) * d['step_m']
        S = []
        for c, z, t in h['samples']:
            x, y = float(np.interp(c, p[:, 0], xy[:, 0])), float(np.interp(c, p[:, 0], xy[:, 1]))
            S.append((c, x, y, z, t, float(np.interp(c, gc, g))))
        for k in range(0, len(gc), 5):   # ground every 5 steps for the grid
            if not math.isnan(g[k]):
                ground_pts.append((float(np.interp(gc[k], p[:, 0], xy[:, 0])), float(np.interp(gc[k], p[:, 0], xy[:, 1])), g[k]))
        pieces, cur = [], None
        for s_ in S:
            if inbox(s_[1], s_[2]):
                if cur is None:
                    cur = []
                    pieces.append(cur)
                cur.append(s_)
            else:
                cur = None
        al = h['align']
        names = [s['name'] for s in d['stations']]
        key = lambda i, s: f"{s['name']}#{i}" if names.count(s['name']) > 1 else s['name']
        dels = set(al.get('del') or [])
        kept = [s for i, s in enumerate(d['stations']) if key(i, s) not in dels]
        sts = []
        cs_all = np.array([s_[0] for s_ in S])
        for i, s in enumerate(kept):
            so = al['so'][i] if i < len(al.get('so') or []) else 0
            cmid = s['c'] + (so or 0)
            x, y = float(np.interp(cmid, p[:, 0], xy[:, 0])), float(np.interp(cmid, p[:, 0], xy[:, 1]))
            if not inbox(x, y):
                continue
            rail = al['st'][i] if i < len(al.get('st', [])) else None
            gz = float(np.interp(cmid, gc, g))
            j = int(np.argmin(np.abs(cs_all - cmid)))
            Lp = PLATFORM_M['rer' if d['sys'] == 'rer' else 'metro']
            sts.append({'name': s['name'], 'line': lid, 'c': r1(cmid), 'x': r2(x), 'y': r2(y),
                        'rail': r2(rail) if rail is not None else None, 'ground': r2(gz) if not math.isnan(gz) else None,
                        'depth': r2(gz - rail) if rail is not None and not math.isnan(gz) else None,
                        'type': S[j][4], 'offset': r1(so or 0), 'platform_m': Lp,
                        'from_c': r1(cmid - Lp / 2), 'to_c': r1(cmid + Lp / 2), 'saved': h['saved']})
        if lid in REPO_PROFILES and h['saved'] and not os.path.exists(os.path.join(a.cache, 'db/profiles_db/alignments', lid + '.json')):
            issues.append(f"{d['line']}: levels from the repo profile ({REPO_PROFILES[lid]}): north of Camp Washington tied to the Deck's APEx level, "
                          "7.9 m over the rails under it (Ben, 2026-10-27); not saved in the Rail Profiles editor")
        elif not h['saved'] and pieces:
            issues.append(f"{d['line']}: no saved alignment in the Profiles editor; drawn from its built-in defaults")
        name = d['line'] if d['sys'] != 'rer' else f"{d['line']} (TRI {RER_LETTER.get(lid, '?')})"
        L[lid] = {'id': lid, 'name': name, 'sys': d['sys'], 'color': d.get('color'), 'saved': h['saved'],
                  'S': pieces, 'stations': sts, 'deleted': sorted(dels)}

    near_line = {lid: Near() for lid in L}
    for lid, l in L.items():
        for pi, piece in enumerate(l['S']):
            for i, s_ in enumerate(piece):
                near_line[lid].add(s_[1], s_[2], (pi, i))

    def locate(lid, q, tol=MATCH_M):
        hit, d = near_line[lid].near(q[0], q[1], tol + 5)
        if hit is None:
            return None
        pi, i = hit
        P = [(s_[0], s_[1], s_[2]) for s_ in L[lid]['S'][pi][max(0, i - 1):i + 2]]
        res = on_line(P, min(i, 1), q)
        if res is None or res[2] > tol:
            return None
        return pi, res[0], res[1], res[2]

    def rail_at(lid, pi, c):
        P = L[lid]['S'][pi]
        return float(np.interp(c, [s_[0] for s_ in P], [s_[3] for s_ in P]))

    # ---- Deck tracks (platform_track's extract.js): levelled where they follow a Profiles line ----
    dd = H['deck_design']
    tracks, unlevelled = [], []
    unlev_m = {}
    il_dz = {}
    for t in dd['tracks']:
        cand = deck_ids(t['sys'], t['line'], L)
        pts = [(x - E0, y - N0) for x, y in resample(t['c'], TRACK_STEP)]
        pts = [q for q in pts if inbox(*q)]
        if len(pts) < 2:
            continue
        best, bn = None, 0
        for lid in cand:   # the line most of the track follows; ties to a saved line (A/D: RER-1)
            n = sum(1 for q in pts[::3] if locate(lid, q, TRACK_MATCH_M))
            if n > bn or (n == bn and n and L[lid]['saved'] and not L[best]['saved']):
                best, bn = lid, n
        loc = [locate(best, q, TRACK_MATCH_M) if best else None for q in pts]
        # the chainage must run one way along the track: a point that steps back (past the line's end, or onto
        # another stretch of the same line) is left unlevelled, so the track is never drawn folded back on itself
        for pi in {lc[0] for lc in loc if lc}:
            idx = [k for k, lc in enumerate(loc) if lc and lc[0] == pi]
            if len(idx) < 2:
                continue
            dirn = 1 if loc[idx[-1]][1] >= loc[idx[0]][1] else -1
            last = None
            for k in idx:
                if last is not None and (loc[k][1] - last) * dirn < 0.5:
                    loc[k] = None
                else:
                    last = loc[k][1]
        run, runs = None, []
        for q, lc in zip(pts, loc):
            kind = 'lev' if lc else 'unlev'
            if run is None or run[0] != kind or (lc and run[2] != lc[0]):
                run = [kind, [], lc[0] if lc else None]
                runs.append(run)
            run[1].append((q, lc))
        for kind, seg, pi in runs:
            if len(seg) < 2:
                continue
            if kind == 'lev':
                if seg[-1][1][1] < seg[0][1][1]:
                    seg.reverse()
                tracks.append({'line': best, 'deck_line': t['line'], 'side': t.get('side'), 'from': t['from'],
                               'c': enc([v[1][1] for v in seg], 10), 'off': enc([v[1][2] for v in seg], 100),
                               'x': enc([v[0][0] for v in seg], 10), 'y': enc([v[0][1] for v in seg], 10)})
                # the other lines the Deck runs on this pair (interlined) and how far their Profiles levels are off
                with_ = []
                for o in cand:
                    if o == best:
                        continue
                    lo = [(v, locate(o, v[0], INTERLINE_M)) for v in seg[::3]]
                    lo = [(v, x) for v, x in lo if x]
                    if len(lo) * 3 >= len(seg[::3]):
                        with_.append(o)
                        dz = max(abs(rail_at(o, x[0], x[1]) - rail_at(best, v[1][0], v[1][1])) for v, x in lo)
                        il_dz[(best, o)] = max(il_dz.get((best, o), 0), dz)
                if with_:
                    tracks[-1]['with'] = with_
            else:
                unlevelled.append({'deck_line': t['line'], 'sys': t['sys'], 'from': t['from'], 'lines': cand, 'cols': [L[i]['color'] for i in cand],
                                   'x': enc([v[0][0] for v in seg], 10), 'y': enc([v[0][1] for v in seg], 10)})
                unlev_m[t['line']] = unlev_m.get(t['line'], 0) + TRACK_STEP * (len(seg) - 1)
    for (b, o), dz in sorted(il_dz.items()):
        if dz > 1.0:
            issues.append(f"{L[o]['name']} interlined on the {L[b]['name']} tracks: Profiles rail up to {dz:.1f} m off {L[b]['name']}'s, drawn at {L[b]['name']}'s")
    for k, v in sorted(unlev_m.items(), key=lambda kv: -kv[1]):
        if v > 200:
            issues.append(f"Deck {k}: {v / 1000:.1f} km of track with no Profiles line within {TRACK_MATCH_M:.0f} m (mostly past the end of the Profiles line), drawn on the ground in its colour")

    # each line's plan follows its Deck tracks (Ben, 2026-10-27: the Profiles paths and the Deck's tracks differ by up
    # to 60 m in places, which drew a line's structure and its tracks apart): where a line has its own Deck tracks
    # its centre moves to their middle, tapering back to the Profiles path over SNAP_TAPER_M past their ends, and the
    # tracks' offsets are taken from the moved centre. Levels stay the Profiles editor's, by chainage.
    def dec_(v, sc):
        out, acc = [], 0
        for d_ in v:
            acc += d_
            out.append(acc / sc)
        return out
    by_line = {}
    for t in tracks:
        by_line.setdefault(t['line'], []).append(t)
    for lid, ts in by_line.items():
        tdat = [(np.array(dec_(t['c'], 10)), np.array(dec_(t['x'], 10)), np.array(dec_(t['y'], 10))) for t in ts]
        moved = []
        for pi, piece in enumerate(L[lid]['S']):
            cs = np.array([s_[0] for s_ in piece])
            px, py = np.array([s_[1] for s_ in piece]), np.array([s_[2] for s_ in piece])
            sx, sy, n = np.zeros(len(cs)), np.zeros(len(cs)), np.zeros(len(cs))
            for tc, tx, ty in tdat:
                inside = (cs >= tc[0]) & (cs <= tc[-1])
                sx[inside] += np.interp(cs[inside], tc, tx)
                sy[inside] += np.interp(cs[inside], tc, ty)
                n[inside] += 1
            have = n > 0
            if not have.any():
                continue
            # the middle of the line's Deck tracks, smoothed along each covered run (SNAP_SMOOTH_M), so a track that
            # ends before its pair does not step the centre
            dx, dy = np.zeros(len(cs)), np.zeros(len(cs))
            w = max(1, int(round(SNAP_SMOOTH_M / STEP)))
            k = 0
            while k < len(cs):
                if not have[k]:
                    k += 1
                    continue
                j = k
                while j + 1 < len(cs) and have[j + 1]:
                    j += 1
                cx, cy = sx[k:j + 1] / n[k:j + 1], sy[k:j + 1] / n[k:j + 1]
                ker = np.ones(2 * w + 1) / (2 * w + 1)
                cx = np.convolve(np.pad(cx, w, mode='edge'), ker, 'valid')
                cy = np.convolve(np.pad(cy, w, mode='edge'), ker, 'valid')
                dx[k:j + 1], dy[k:j + 1] = cx - px[k:j + 1], cy - py[k:j + 1]
                k = j + 1
            # past the covered runs the shift tapers back to the Profiles path over SNAP_TAPER_M
            hc = cs[have]
            for k in np.nonzero(~have)[0]:
                j = int(np.argmin(np.abs(hc - cs[k])))
                kk = int(np.nonzero(have)[0][j])
                f_ = max(0.0, 1 - abs(cs[k] - hc[j]) / SNAP_TAPER_M)
                dx[k], dy[k] = dx[kk] * f_, dy[kk] * f_
            L[lid]['S'][pi] = [(s_[0], float(x + ddx), float(y + ddy)) + tuple(s_[3:]) for s_, x, y, ddx, ddy in zip(piece, px, py, dx, dy)]
            moved.append((pi, cs, dx, dy))
        # the tracks' offsets from the moved centre; stations move with their line
        for t in ts:
            tc, tx, ty = np.array(dec_(t['c'], 10)), np.array(dec_(t['x'], 10)), np.array(dec_(t['y'], 10))
            offs = np.array(dec_(t['off'], 100))
            for pi, cs, dx, dy in moved:
                piece = L[lid]['S'][pi]
                for k in range(len(tc)):
                    if cs[0] <= tc[k] <= cs[-1]:
                        i = int(np.clip(np.searchsorted(cs, tc[k]), 0, len(cs) - 1))
                        res = on_line([(q[0], q[1], q[2]) for q in piece[max(0, i - 2):i + 3]], min(i, 2), (tx[k], ty[k]))
                        if res is not None:
                            offs[k] = res[1]
            t['off'] = enc(list(offs), 100)
        for st in L[lid]['stations']:
            for pi, cs, dx, dy in moved:
                if cs[0] <= st['c'] <= cs[-1]:
                    k = int(np.argmin(np.abs(cs - st['c'])))
                    st['x'], st['y'] = r2(st['x'] + dx[k]), r2(st['y'] + dy[k])
                    break
    # fold-backs left in the Profiles paths (a drawing error in the editor's line), listed
    for lid, l in L.items():
        bad = []
        for piece in l['S']:
            for k in range(2, len(piece) - 2):
                u = (piece[k][1] - piece[k - 2][1], piece[k][2] - piece[k - 2][2])
                v = (piece[k + 2][1] - piece[k][1], piece[k + 2][2] - piece[k][2])
                la, lb = math.hypot(*u), math.hypot(*v)
                if la > 1 and lb > 1 and (u[0] * v[0] + u[1] * v[1]) / la / lb < -0.5 and not any(abs(piece[k][0] - c) < 50 for c in bad):
                    bad.append(piece[k][0])
        if bad:
            issues.append(f"{l['name']}: the Profiles path folds back on itself at c {', '.join(f'{c:.0f}' for c in bad[:6])} with no Deck track to follow there (a drawing error in the line)")
    near_line.clear()
    near_line.update({lid: Near() for lid in L})
    for lid, l in L.items():
        for pi, piece in enumerate(l['S']):
            for i, s_ in enumerate(piece):
                near_line[lid].add(s_[1], s_[2], (pi, i))

    # interlined pairs (RER A/D, B D, B C E ...) are drawn once, on the line most of the pair follows, striped in every
    # line's colour (Ben, 2026-10-27): 'il' on that line's samples (1 + the index in 'interline'); the other lines are
    # marked shared within INTERLINE_M of the pair and draw nothing there. Elsewhere, where a line has no track of its
    # own but runs on another line's, it is shared too.
    combos = []
    for t in tracks:
        if t.get('with'):
            k = [t['line']] + t['with']
            if k not in combos:
                combos.append(k)
            t['il'] = combos.index(k) + 1
    il_near = Near()
    own_near, other_near = {lid: Near() for lid in L}, Near()
    def dec(v, s):
        out, acc = [], 0
        for d_ in v:
            acc += d_
            out.append(acc / s)
        return out
    for t in tracks:
        for x, y in zip(dec(t['x'], 10), dec(t['y'], 10)):
            own_near[t['line']].add(x, y, t.get('il', 0))
            other_near.add(x, y, t['line'])
            if t.get('with'):
                il_near.add(x, y, set(t['with']))
    for lid, l in L.items():
        l['shared'], l['il'] = [], []
        for piece in l['S']:
            sh, il = [], []
            for s_ in piece:
                own, _ = own_near[lid].near(s_[1], s_[2], 30)
                oth, _ = (None, 0) if own is not None else other_near.near(s_[1], s_[2], 10)
                w, _ = (None, 0) if own is not None else il_near.near(s_[1], s_[2], INTERLINE_M)
                sh.append(1 if (own is None and ((oth and oth != lid and L[oth]['sys'] == l['sys']) or (w and lid in w))) else 0)
                il.append(own or 0)
            l['shared'].append(sh)
            l['il'].append(il)

    # ---- the Deck's plan: streets, blocks, platform rings (its GeoJSON export) ----
    def to_local(coords):
        c = np.asarray(coords, float)
        E, N = ll_to_utm(c[..., 0], c[..., 1])
        return np.stack([E - E0, N - N0], -1)

    streets, blocks, plats = [], [], []
    for f in H['deck']['features']:
        p, g = f['properties'], f.get('geometry')
        lay = p.get('layer')
        if not g:
            continue
        if lay == 'street' and g['type'] == 'LineString':
            xy = to_local(g['coordinates'])
            if any(inbox(*q) for q in xy):
                streets.append({'w': p.get('width_m') or 10, 'kind': p.get('kind'), 'name': p.get('name', ''),
                                'x': enc(xy[:, 0], 10), 'y': enc(xy[:, 1], 10)})
        elif lay == 'block':
            rings = g['coordinates'] if g['type'] == 'Polygon' else [poly[0] for poly in g['coordinates']]
            xy = to_local(rings[0])
            if len(xy) >= 3 and any(inbox(*q) for q in xy):
                blocks.append({'type': p.get('type'), 'x': enc(xy[:, 0], 10), 'y': enc(xy[:, 1], 10)})
        elif lay in ('metro_platform', 'rer_platform', 'cvx_platform'):
            ring = to_local(g['coordinates'][0])
            if np.allclose(ring[0], ring[-1]):
                ring = ring[:-1]
            if not any(inbox(*q) for q in ring):
                continue
            sys_ = lay.split('_')[0]
            ids = deck_ids(sys_, p.get('line'), L)
            ctr = ring.mean(0)
            levels = []
            for lid in ids:
                lc = locate(lid, ctr)
                if lc is None:
                    continue
                pi, c, off, dist = lc
                piece = L[lid]['S'][pi]
                rail = float(np.interp(c, [s_[0] for s_ in piece], [s_[3] for s_ in piece]))
                levels.append({'line': lid, 'c': r1(c), 'rail': r2(rail), 'off': r1(off), 'saved': L[lid]['saved']})
            # a platform on a shared pair (RER A/D, B C E ...) serves every line on it, at the saved line's level
            lev = next((v for v in levels if v['saved']), levels[0] if levels else None)
            plats.append({'station': p.get('station'), 'deck_line': p.get('line'), 'sys': sys_, 'type': p.get('type'), 'n': p.get('n'),
                          'lines': ids, 'levels': levels, 'line': lev['line'] if lev else None,
                          'rail': lev['rail'] if lev else None,
                          'top': r2(lev['rail'] + PLATFORM_ABOVE_RAIL['rer' if sys_ == 'rer' else 'metro']) if lev else None,
                          'x': enc(ring[:, 0], 100), 'y': enc(ring[:, 1], 100)})
    # the Union Terminal TRI box (Deck: three fixed islands, Chatelet-Les Halles): north island A and B westbound,
    # centre D, south B and A eastbound, by their order north to south (its axis runs about east-west, heading -3.75)
    ut = [pl for pl in plats if (pl['deck_line'] or '') == 'Union Terminal box' and pl['station'] == 'Union Terminal']
    if len(ut) == 3:
        ctr = lambda pl: (np.mean(dec(pl['x'], 100)), np.mean(dec(pl['y'], 100)))
        for pl, ids, name in zip(sorted(ut, key=lambda q: -ctr(q)[1]), (['RER_1', 'RER_2'], ['RER_4'], ['RER_2', 'RER_1']),
                                 ('north island, A and B westbound', 'centre island, D', 'south island, B and A eastbound')):
            cx, cy = ctr(pl)
            levels = []
            for lid in ids:
                prof = [s for s in L[lid]['stations'] if s['name'] == 'Union Terminal' and s['rail'] is not None]
                if prof:
                    levels.append({'line': lid, 'c': prof[0]['c'], 'rail': prof[0]['rail'], 'off': None, 'saved': L[lid]['saved']})
            levels.sort(key=lambda v: v['line'])   # the saved line first in letter order (A before B), as elsewhere
            lev = next((v for v in levels if v['saved']), levels[0] if levels else None)
            pl.update(lines=ids, levels=levels, line=lev['line'] if lev else None, rail=lev['rail'] if lev else None,
                      top=r2(lev['rail'] + PLATFORM_ABOVE_RAIL['rer']) if lev else None, type='island', box_island=name)
            if len({v['rail'] for v in levels}) > 1:
                issues.append(f"Union Terminal box, {name}: cross-platform lines at different Profiles levels ("
                              + ', '.join(f"{L[v['line']]['name']} {v['rail']} m" for v in levels) + f"); drawn at {L[lev['line']]['name']}'s")
    nolev = [pl for pl in plats if pl['rail'] is None]
    if nolev:
        issues.append(f"{len(nolev)} Deck platforms have no Profiles line within {MATCH_M:.0f} m (drawn at ground level): "
                      + ', '.join(sorted({f"{pl['station']} ({pl['deck_line']})" for pl in nolev})[:12]) + (' ...' if len(nolev) > 12 else ''))

    # ---- stations: the Deck's station and stops merged with the Profiles stations on the same lines ----
    norm = lambda s: ''.join(ch for ch in (s or '').lower() if ch.isalnum())
    prof_sts = [s for l in L.values() for s in l['stations']]
    used = set()
    stations = []
    for st in dd['stations']:
        x, y = st['E'] - E0, st['N'] - N0
        if not inbox(x, y):
            continue
        stops = []
        line_ids = set()
        for o in st['stops']:
            ids = deck_ids(st['sys'], o.get('line'), L)
            if not o.get('line') and st['name'] == 'Union Terminal' and st['sys'] == 'rer':
                ids = ['RER_1', 'RER_2', 'RER_4']   # the TRI box: A, B and D (its islands above)
            line_ids.update(ids)
            stops.append({'deck_line': o.get('line'), 'lines': ids, 'type': o.get('type'), 'type_generated': o.get('type_generated'),
                          'ben': o.get('edit'), 'L': o.get('L'), 'slid': r1((o.get('o') or 0) - (o.get('o_generated') or 0)),
                          'bands': o.get('bands'), 'track_offsets': o.get('track_offsets'), 'tracks_from': o.get('tracks_from'),
                          'bored_at_centre': o.get('bored_at_centre')})
        prof = []
        for k, s in enumerate(prof_sts):
            if k in used or s['line'] not in line_ids:
                continue
            dist = math.hypot(s['x'] - x, s['y'] - y)
            if (norm(s['name']) == norm(st['name']) and dist < 400) or dist < 150:
                prof.append(dict(s, dist=r1(dist)))
                used.add(k)
        stations.append({'id': st['key'], 'name': st['name'], 'sys': st['sys'], 'x': r1(x), 'y': r1(y),
                         'deleted': st['deleted'], 'edited': st['edited'], 'stops': stops, 'profiles': prof})
    for k, s in enumerate(prof_sts):   # Profiles stations the Deck has no station for
        if k not in used:
            stations.append({'id': f"profiles:{s['line']}:{s['name']}", 'name': s['name'], 'sys': L[s['line']]['sys'],
                             'x': s['x'], 'y': s['y'], 'deleted': False, 'edited': False, 'stops': [], 'profiles': [dict(s, dist=None)],
                             'note': 'in the Rail Profiles editor only'})
    only_prof = [s for s in stations if s.get('note')]
    if only_prof:
        issues.append(f"{len(only_prof)} Profiles stations have no Deck station within reach: "
                      + ', '.join(sorted({f"{s['name']} ({s['profiles'][0]['line']})" for s in only_prof})[:12]) + (' ...' if len(only_prof) > 12 else ''))

    # ---- ground: a coarse grid from the Profiles ground along every line ----
    gx0, gy0 = BOX[0], BOX[1]
    nx, ny = int(math.ceil((BOX[2] - BOX[0]) / GRID)) + 1, int(math.ceil((BOX[3] - BOX[1]) / GRID)) + 1
    acc, cnt = np.zeros((ny, nx)), np.zeros((ny, nx))
    for x, y, z in ground_pts:
        i, j = int(round((y - gy0) / GRID)), int(round((x - gx0) / GRID))
        if 0 <= i < ny and 0 <= j < nx:
            acc[i, j] += z
            cnt[i, j] += 1
    G = np.where(cnt > 0, acc / np.maximum(cnt, 1), np.nan)
    for _ in range(8):   # fill out from the lines, a cell at a time
        known = ~np.isnan(G)
        pad = np.pad(np.where(known, G, 0), 1)
        pk = np.pad(known.astype(float), 1)
        s_ = sum(pad[1 + di:1 + di + ny, 1 + dj:1 + dj + nx] for di in (-1, 0, 1) for dj in (-1, 0, 1))
        n_ = sum(pk[1 + di:1 + di + ny, 1 + dj:1 + dj + nx] for di in (-1, 0, 1) for dj in (-1, 0, 1))
        G = np.where(known, G, np.where(n_ > 0, s_ / np.maximum(n_, 1), np.nan))
    ground = {'x0': r1(gx0), 'y0': r1(gy0), 'step': GRID, 'nx': nx, 'ny': ny,
              'z': [None if math.isnan(v) else int(round(v * 10)) for v in G.ravel()]}

    # ---- the other systems at CUT and Norwood Central: structures, tracks, platforms, piers, finished ground ----
    import context3d
    ut_isl = [([list(q) for q in zip(dec(pl['x'], 100), dec(pl['y'], 100))], pl['rail']) for pl in ut] if len(ut) == 3 and all(pl['rail'] is not None for pl in ut) else None
    ctx = context3d.build(E0, N0, ut_isl)
    unlevelled += ctx['unlevelled']
    gtiles = context3d.tiles(ctx, E0, N0, gx0, gy0)
    context = ctx['items']

    # ---- checks: the Deck's spacing against the Profiles structure ----
    for lid, l in L.items():
        own = [t for t in tracks if t['line'] == lid]
        if not own:
            continue
        bad = {'tube': 0.0, 'box': 0.0, 'rer': 0.0}
        cs_off = [(dec(t['c'], 10), dec(t['off'], 100)) for t in own]
        plat = [(s['from_c'] - 40, s['to_c'] + 40) for s in l['stations']]
        for piece in l['S']:
            for s_, s2 in zip(piece, piece[1:]):
                c = s_[0]
                if any(p0 <= c <= p1 for p0, p1 in plat):
                    continue
                offs = [float(np.interp(c, cc, oo)) for cc, oo in cs_off if cc[0] <= c <= cc[-1]]
                if len(offs) != 2:
                    continue
                gap = abs(offs[0] - offs[1])
                k = structure(lid, s_[4])['k']
                if l['sys'] == 'metro' and k == 'tube' and gap < 6.0:
                    bad['tube'] += s2[0] - c
                elif l['sys'] == 'metro' and k == 'box' and gap > 6.0:
                    bad['box'] += s2[0] - c
                elif l['sys'] == 'rer' and k == 'tube' and gap < RER_ST['bore']['od'] + 1:
                    bad['rer'] += s2[0] - c
        if bad['tube'] > 50:
            issues.append(f"{l['name']}: {bad['tube'] / 1000:.2f} km bored in the Profiles editor but at box spacing (3.9 m) in the Deck")
        if bad['box'] > 50:
            issues.append(f"{l['name']}: {bad['box'] / 1000:.2f} km cut and cover in the Profiles editor but twin tubes (8.0 m) in the Deck")
        if bad['rer'] > 50:
            issues.append(f"{l['name']}: {bad['rer'] / 1000:.2f} km bored with the Deck's tracks closer than two {RER_ST['bore']['od']} m tubes allow (TRI spacing ignores construction)")

    # ---- the snapshot ----
    snap_lines = []
    for lid, l in L.items():
        if not l['S']:
            continue
        pieces = []
        for piece, sh, il in zip(l['S'], l['shared'], l['il']):
            pieces.append({'c0': r1(piece[0][0]), 'step': STEP, 'n': len(piece),
                           'x': enc([s_[1] for s_ in piece], 10), 'y': enc([s_[2] for s_ in piece], 10),
                           'z': enc([s_[3] for s_ in piece], 100), 't': rle([s_[4] for s_ in piece]), 'sh': rle(sh), 'il': rle(il)})
        snap_lines.append({'id': lid, 'name': l['name'], 'sys': l['sys'], 'color': l['color'], 'saved': l['saved'],
                           'pieces': pieces, 'stations': l['stations']})
    struct = {lid: {t: structure(lid, t) for t in ('cutcover', 'shield', 'deep', 'elevated', 'atgrade', 'trough')} for lid in L}
    meta = {
        'area': AREA['id'], 'name': AREA['name'], 'default_station': AREA['default_station'],
        'synced_at': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
        'origin': {'lon': AREA['lon'], 'lat': AREA['lat'], 'E': r2(E0), 'N': r2(N0), 'crs': 'EPSG:32616'},
        'frame_turn_deg': AREA['frame_turn'], 'box': [r1(v) for v in BOX],
        'interline': combos, 'stripe_m': STRIPE_M,
        'platform_m': PLATFORM_M, 'platform_above_rail': PLATFORM_ABOVE_RAIL, 'struct': struct, 'box_margin': BOX_MARGIN,
        'assumed': ASSUMED, 'deck_rules': dd.get('constants'), 'issues': issues,
        'rules': ['Levels: the Rail Profiles editor; plan, tracks and platforms: the Mill Creek Deck',
                  'A platform on a shared pair (RER A/D, B C E ...) serves every line on it, at the level of the saved Profiles line (Ben, 2026-10-26: A and D share the Fountain Square platforms)',
                  'An interlined pair (RER A/D, B/D, B C E ...) is one pair of tracks, drawn once at the level of the line most of it follows and striped in every line\'s colour (Ben, 2026-10-27)',
                  'Platforms: Metro 400 ft, TRI 670 ft (Ben, 2026-10-26)'],
        'ctx': {'tile': context3d.TILE, 'counts': dict(ctx['counts'], tiles=len(gtiles)), 'sources': ctx['sources'],
                    'rules': ['CUT and Norwood Central structures from the Mill Creek Deck, drawn as in the Rail Profiles context (the same definitions)',
                              f'Past the Deck\'s structures the APEx, intercity, C&O and Transvalley tracks have no Deck level: from each structure end they run at most {context3d.EXT_GRADE["apex"] * 100:.1f}% (APEx), {context3d.EXT_GRADE["orr"] * 100:.1f}% (lower level) or {context3d.EXT_GRADE["tv"] * 100:.0f}% (Transvalley) to the ground smoothed over {context3d.EXT_SMOOTH_M:.0f} m; the Deck\'s tunnel tracks {context3d.TUNNEL_RAIL_M:.0f} m under it; over water at least {context3d.WATER_RAIL_M:.0f} m above the Ohio pool (drawing values, Ben 2026-10-27: into Ludlow and to the region\'s edge)',
                              'Union Terminal TRI box: one level for RER-1, 2 and 4, the Profiles level (Ben, 2026-10-26)',
                              'Structure types at CUT (Ben, 2026-10-26): the fan from W 9th to W Liberty is an embankment with a bridge over each street; the wide south approach to the Cardinal crossing and the north trunk are arch viaducts, an arch over each street (piers on the street edges), solid between; the rest are normal viaducts on piers; the intercity and C&O descents are embankments with blind arches',
                              'No footing check under the structures (Ben, 2026-10-26); drawing values: piers every 25 m, 2 m thick, on normal viaducts; blind arches every 10 m',
                              'The Deck\'s street re-grades are finished ground (Ben, 2026-10-26); finished ground at 10 m round the structures',
                              'Lower-pair levels from the Deck\'s dive figures until the Deck publishes a level per point (Ben, 2026-10-26)',
                              'Norwood ORR, Transvalley and APEx tracks are fixed context; levels approximate, from the ground (Ben, 2026-10-26)']},
        'sources': {'profiles_saved': {lid: l['saved'] for lid, l in L.items()}},
        'counts': {'lines': len(snap_lines), 'tracks': len(tracks), 'unlevelled': len(unlevelled), 'stations': len(stations),
                   'platforms': len(plats), 'streets': len(streets), 'blocks': len(blocks)},
    }
    vf = os.path.join(a.cache, 'versions.json')
    if os.path.exists(vf):
        meta['sources'].update(json.load(open(vf)))
    snap = dict(meta, lines=snap_lines, tracks=tracks, unlevelled=unlevelled, stations=stations, platforms=plats,
                streets=streets, blocks=blocks, ground=ground, context=context, gtiles=gtiles)
    json.dump(snap, open(a.out, 'w'), separators=(',', ':'))

    # ---- database documents: parts of at most ~200 KB of JSON text (the limit is 256 KiB a document), the meta document last ----
    ddir = os.path.join(os.path.dirname(a.out), 'db_out')
    os.makedirs(ddir, exist_ok=True)
    for f in os.listdir(ddir):
        os.remove(os.path.join(ddir, f))
    parts = []
    for key in ('lines', 'tracks', 'unlevelled', 'stations', 'platforms', 'streets', 'blocks', 'context', 'gtiles'):
        items, chunk, size, n = snap[key], [], 0, 0
        def flush():
            nonlocal chunk, size, n
            if not chunk:
                return
            name = f'{key}-{n}'
            json.dump({'json': json.dumps({'key': key, 'items': chunk}, separators=(',', ':')), 'synced_at': meta['synced_at']},
                      open(os.path.join(ddir, name + '.json'), 'w'))
            parts.append(name)
            chunk, size, n = [], 0, n + 1
        for it in items:
            s_ = len(json.dumps(it, separators=(',', ':')))
            if size + s_ > 200_000:   # a database document holds at most 256 KiB (JSON text escaped inside it)
                flush()
            chunk.append(it)
            size += s_
        flush()
    json.dump({'json': json.dumps({'key': 'ground', 'value': ground}, separators=(',', ':')), 'synced_at': meta['synced_at']},
              open(os.path.join(ddir, 'ground-0.json'), 'w'))
    parts.append('ground-0')
    json.dump({'json': json.dumps(meta, separators=(',', ':')), 'parts': parts, 'synced_at': meta['synced_at']},
              open(os.path.join(ddir, 'meta.json'), 'w'))

    # ---- report ----
    fs = [s for s in stations if s['name'] == AREA['default_station']]
    for s in fs:
        for p in s['profiles']:
            print(f"{s['name']:<16} {L[p['line']]['name']:<22} rail {p['rail']} m  ground {p['ground']}  {p['type']}", file=sys.stderr)
    for pl in plats:
        if pl['station'] == AREA['default_station']:
            print(f"  platform {pl['deck_line']:<14} {pl['type']:<7} lines {','.join(pl['lines'])}  rail {pl['rail']}", file=sys.stderr)
    print(json.dumps(meta['counts']), json.dumps(meta['ctx']['counts']), file=sys.stderr)
    sizes = {f: os.path.getsize(os.path.join(ddir, f)) for f in os.listdir(ddir)}
    print(f"{len(parts)} parts, largest {max(sizes.values()) // 1024} KB, total {sum(sizes.values()) // 1024} KB", file=sys.stderr)
    print(f"{len(issues)} issues", file=sys.stderr)
    for i in issues:
        print('  issue:', i, file=sys.stderr)


if __name__ == '__main__':
    main()
