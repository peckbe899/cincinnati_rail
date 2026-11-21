"""merge/impl: the staged street_map.editor_lines() on 44 against the lines of Ben's saved street map (made by the
repo's street_map.py from the same N_edges.json and edges_ben.json), without running street_map.py's main (it writes
into the repo). -> merge/impl/street_map_check.json"""
import common as C, json, sys, os
C.step4_mod(); sys.path.insert(0, C.SU)
import street_map as SMOD
assert os.path.normcase(os.path.abspath(SMOD.__file__)).startswith(os.path.normcase(os.path.abspath(C.SU)))
os.chdir(C.DATA)
sm = json.load(open('streetmap/22-44.json', encoding='utf8'))
L, SH = SMOD.editor_lines('44', *sm['size'], json.load(open('unet_data/44_edges.json', encoding='utf8')), json.load(open('picks22_guided/22-44/edges_ben.json', encoding='utf8')))
mine = [dict(a=[round(v, 1) for v in l['a']], b=[round(v, 1) for v in l['b']], kind=l['kind'], name=l['name']) for l in L]
res = dict(lines_from_editor_lines=len(mine), lines_in_streetmap=len(sm['lines']), identical=mine == sm['lines'])
print(res); json.dump(res, open(C.IMPL + 'street_map_check.json', 'w'))
