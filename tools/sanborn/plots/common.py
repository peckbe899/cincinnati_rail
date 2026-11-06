"""Shared loading for the plot generator: blocks, streets (with frontage/alley class), Sanborn tile sampling."""
try: import _ws  # Sanborn paths: tools/sanborn/_ws.py, configs/sanborn_paths.json (was the Topography workspace scratchpad and the chat uploads)
except ImportError: import os as _o, sys as _s; _s.path.append(_o.path.normpath(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..'))); import _ws
import json, math, os, numpy as np
from PIL import Image
from shapely.geometry import LineString, Polygon, MultiPolygon, Point, shape, box
from shapely.ops import unary_union
from shapely.strtree import STRtree
SP = _ws.DATA
def load_layers():
    D = json.load(open(SP + 'deckpage/deck.json')); B = json.load(open(SP + 'deckpage/basin.json'))
    blocks, streets, open_areas = [], [], []
    for src, fc in (('deck', D), ('basin', B)):
        for f in fc['features']:
            p = f['properties']; L = p.get('layer')
            if L == 'block':
                g = shape(f['geometry'])
                if not g.is_valid: g = g.buffer(0)
                blocks.append(dict(id=p['id'], src=src, set=p.get('src') or p.get('side') or ('deck' if src == 'deck' else ''), type=p.get('type'), g=g, area=g.area))
            elif L == 'street':
                c = f['geometry']['coordinates']
                if len(c) < 2: continue
                w = p.get('width_m') or 10.0
                alley = p.get('kind') == 'we_alley' or w < 6.5
                streets.append(dict(id=p['id'], name=p.get('name', ''), kind=p.get('kind'), w=w, alley=alley, line=LineString(c)))
            elif L in ('boulevard', 'roundabout', 'forecourt', 'cut_square', 'we_forecourt'):
                open_areas.append(dict(id=L, g=shape(f['geometry'])))
    return blocks, streets, open_areas
class Tiles:
    """the warped Sanborn tiles (0.25 m), basin and north sets; luminance sampling in map coordinates"""
    def __init__(s):
        s.sets = []
        for d in ('tiles_b', 'tiles_n'):
            idx = json.load(open(SP + f'deckpage/{d}/index.json')); s.sets.append((d, idx['size'], idx['res'], {tuple(t) for t in idx['tiles']}))
        s.cache = {}
    def _img(s, d, tx, ty):
        k = (d, tx, ty)
        if k not in s.cache:
            im = Image.open(SP + f'deckpage/{d}/{tx}_{ty}.webp').convert('RGBA'); a = np.asarray(im).astype(np.float32)
            lum = 0.299 * a[..., 0] + 0.587 * a[..., 1] + 0.114 * a[..., 2]; lum[a[..., 3] < 128] = np.nan
            s.cache[k] = lum
            if len(s.cache) > 40: s.cache.pop(next(iter(s.cache)))
        return s.cache[k]
    def sample(s, X, Y, prefer=None):
        """luminance at map points (nearest pixel); NaN where no sheet. Tries the basin set first, then north."""
        X = np.asarray(X, float); Y = np.asarray(Y, float); out = np.full(X.shape, np.nan)
        order = s.sets if prefer is None else sorted(s.sets, key=lambda q: q[0] != prefer)
        for d, T, res, have in order:
            need = np.isnan(out)
            if not need.any(): break
            tx = (np.floor(X / T) * T).astype(int); ty = (np.floor(Y / T) * T).astype(int)
            for key in set(zip(tx[need], ty[need])):
                if key not in have: continue
                m = need & (tx == key[0]) & (ty == key[1]); im = s._img(d, *key); n = im.shape[0]
                px = np.clip(((X[m] - key[0]) / res).astype(int), 0, n - 1); py = np.clip(((key[1] + T - Y[m]) / res).astype(int), 0, n - 1)
                out[m] = im[py, px]
        return out
