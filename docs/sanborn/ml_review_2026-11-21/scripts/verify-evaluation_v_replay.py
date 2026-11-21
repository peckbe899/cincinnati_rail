"""Replay street_map.py's key matching on plate 44 (eval-12): how many truth lines did Ben touch?"""
import json, os, sys, time
import numpy as np, cv2
sys.path.insert(0, 'C:/Users/peckb/AppData/Local/Temp/claude/8945a8e3044b4e4c/2a2bcb12-80e8-4366-9a59-3be15cce3445/scratchpad/ml_review/evaluation')
import evallib as E
SP = E.SP
print('44_edges.json mtime', time.ctime(os.path.getmtime(E.U + '44_edges.json')))
B = json.load(open(SP + 'picks22_guided/22-44/edges_ben.json', encoding='utf8'))
T = json.load(open(SP + 'streetmap/22-44.json', encoding='utf8')); W, H = T['size']
SH = E.sheet('44', W, H); Ed = E.clean(json.load(open(E.U + '44_edges.json', encoding='utf8'))) + SH
key = lambda a, b: tuple(round(v) for v in list(a) + list(b))
by = {key(l['a0'], l['b0']): l for l in B['lines'] if not l.get('added')}
KIND = dict(green='printed', orange='printed', sheet='sheet_edge')
cnt = dict(touched_kept=0, touched_wrong=0, untouched_interior=0, untouched_sheet=0, untouched_hidden=0)
L = []
for e in Ed:
    s = by.get(key(e['a'], e['b']))
    if s:
        if s.get('verdict') == 'wrong': cnt['touched_wrong'] += 1; continue
        cnt['touched_kept'] += 1; L.append(s['a'] + s['b'])
    elif e['state'] in KIND:
        cnt['untouched_sheet' if e['state'] == 'sheet' else 'untouched_interior'] += 1; L.append(e['a'] + e['b'])
    else: cnt['untouched_hidden'] += 1
added = [l for l in B['lines'] if l.get('added') and l.get('verdict') != 'wrong']
cnt['drawn'] = len(added); cnt['total_truth_before_len_filter'] = cnt['touched_kept'] + cnt['untouched_interior'] + cnt['untouched_sheet'] + cnt['drawn']
cnt['streetmap_lines'] = len(T['lines'])
# matched keys from edges_ben that found no shown line (stale)
cnt['ben_entries_not_added'] = len(by); cnt['ben_entries_matched'] = sum(1 for e in Ed if key(e['a'], e['b']) in by)
# verdict / moved breakdown
from collections import Counter
cnt['verdict_moved_added'] = {str(k): v for k, v in Counter((l.get('verdict'), bool(l.get('moved')), bool(l.get('added'))) for l in B['lines']).items()}
print(json.dumps(cnt, indent=1)); json.dump(cnt, open('v_replay.json', 'w'), indent=1)
