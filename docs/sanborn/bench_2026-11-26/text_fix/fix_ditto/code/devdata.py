"""Dev data helpers for the ditto fix (26 Nov 2026). Dev and check use only; dittofix.py never imports this.

Reads (read-only): the finder3 masks, the scans, the dev ditto truth, its negatives and truth v2 (T1-T7).
Run from data/sanborn.
"""
import json, os
import numpy as np, cv2

DS = os.getcwd()
TF = os.path.join('bench_2026-11-26', 'text_fix')
F3_DIRS = [os.path.join('bench_2026-11-25', 'text_v1', 'classifier', 'out', 'finder3'),
           os.path.join(TF, 'dev_ditto', 'runs', 'finder3')]
DD = os.path.join(TF, 'dev_ditto', 'truth')
NEG = os.path.join(TF, 'dev_ditto', 'negatives')
TV2 = os.path.join('bench_2026-11-25', 'text_v1', 'truth')
SEALED = {'6', '9', '52', '56', '58', '63', '35', '38', '41', '66', '71', '76', '84', '88', '46', '92'}
HELD = {'H1': ('90', [5640, 3950, 7140, 4950]), 'H2': ('90', [880, 2100, 2380, 3100]),
        'H3': ('47', [7040, 4560, 8540, 5560]), 'H4': ('54A', [7190, 3950, 8690, 4950])}
# folds by plate (balanced by scale and ditto words): A tunes, B checks, then the other way round
FOLD_A = {'44', '2', '3', '54A', '30', '60B', '74', '90', '48'}
FOLD_B = {'4', '12', '57', '1A', '26A', '64A', '19', '86', '47', '49', '93A', '5'}


def f3_path(N):
    for d in F3_DIRS:
        p = os.path.join(d, f'{N}_text.png')
        if os.path.exists(p): return p
    raise FileNotFoundError(N)


def fold(N):
    return 'A' if N in FOLD_A else ('B' if N in FOLD_B else '?')


def crops(which=('dd', 'neg', 't')):
    out = {}
    if 'dd' in which:
        for k, v in json.load(open(os.path.join(DD, 'crops.json'))).items(): out[k] = dict(v, set='dd', dir=DD)
    if 'neg' in which:
        for k, v in json.load(open(os.path.join(NEG, 'crops.json'))).items(): out[k] = dict(v, set='neg', dir=NEG)
    if 't' in which:
        for k, v in json.load(open(os.path.join(TV2, 'crops.json'))).items(): out[k] = dict(v, set='t', dir=TV2)
    for k, v in out.items(): assert v['plate'] not in SEALED
    return out


def truth(c, k):
    m = cv2.imread(os.path.join(c['dir'], f'{k}_mask.png'), 0)
    w = json.load(open(os.path.join(c['dir'], f'{k}_words.json'), encoding='utf8'))['words']
    return m, w
