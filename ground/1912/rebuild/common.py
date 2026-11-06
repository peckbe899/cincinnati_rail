"""Shared setup for the 1912 rebuild: paths, sheet ids, start model."""
import json, os, re
from pathlib import Path
import numpy as np

from georef_model import load_start

REPO = Path(__file__).resolve().parents[3]


def load_paths(path):
    P = json.load(open(path))
    Path(P['work']).mkdir(parents=True, exist_ok=True)
    return P


def sheet_ids(P):
    """s001.. in the raw folder's sorted order of sheet scans, with the survey's own two-digit number."""
    files = sorted(f.name for f in Path(P['sheets']).glob('Sheet_*.jpg'))
    out = {}
    for i, f in enumerate(files, 1):
        num = re.match(r'Sheet_(\d+)_', f).group(1)
        out[f's{i:03d}'] = dict(file=f, num=num)
    return out


def load_all(P):
    S = json.load(open(P['sheet_index']))
    start, meta = load_start(P['georef_start'])
    ids = sheet_ids(P)
    for sid, d in ids.items():
        d.update(S[d['num']]); d['start'] = start[d['num']]
    return ids, meta


def frame_px(d):
    return [d['corners'][k] for k in ('TL', 'TR', 'BR', 'BL')]


def norm_name(s):
    s = s.lower().replace('.', ' ')
    s = re.sub(r'\b(street|st|avenue|ave|av|road|rd|place|pl|lane|ln|alley|al|boulevard|blvd|drive|dr|court|ct|terrace|ter|pike|way|row)\b', ' ', s)
    s = re.sub(r'\b(west|east|north|south|w|e|n|s)\b', ' ', s)
    return re.sub(r'\s+', ' ', s).strip()


def neighbours(ids):
    """Shared edges between sheets: list of (a, b, kind, fixed, lo, hi) in survey feet."""
    out = []
    keys = sorted(ids)
    for i, a in enumerate(keys):
        A = ids[a]
        for b in keys[i + 1:]:
            B = ids[b]
            for (ea, eb, kind) in ((A['x_e'], B['x_w'], 'x'), (A['x_w'], B['x_e'], 'x'), (A['y_s'], B['y_n'], 'y'), (A['y_n'], B['y_s'], 'y')):
                if ea != eb:
                    continue
                if kind == 'x':
                    lo, hi = max(A['y_s'], B['y_s']), min(A['y_n'], B['y_n'])
                else:
                    lo, hi = max(A['x_w'], B['x_w']), min(A['x_e'], B['x_e'])
                if hi - lo > 100:
                    out.append((a, b, kind, ea, lo, hi))
    return out
