"""merge/impl/r2: nothing in the repo changed (21 Nov 2026). Reads only.

    python -B safety.py     -> merge/impl/r2/safety.json

- sha256 of the repo files the staged code replaces (and rail_tracks.py, edit_server.py), against the values the
  task and the four checks gave;
- every file under tools/sanborn (the venv included), data/sanborn/{unet_data, picks22_guided, streetmap, cufp},
  configs, newer than merge/impl/r2/start_stamp (this round's start);
- no __pycache__ under merge/staged; Ben's files on 90 and 44 as they were (rail_ben.json 37 / 26 tracks, no
  edges_ben.json on 90).
"""
import hashlib, json, os
import common as C
H = lambda p: hashlib.sha256(open(p, 'rb').read()).hexdigest()[:8]
want = dict(outlines='bccc2b34', blocks_noguide='3700ff13', ink_bins='de9b7914', street_map='41d33506', run_plates='2c6ee4a9', rail_tracks='16a4c4ed', edit_server='f24a99a6')
got = {k: H(C.REPO + f'tools/sanborn/unet/{k}.py') for k in want}
t0 = os.path.getmtime(C.IMPL + 'start_stamp'); newer = []
for root in ('tools/sanborn', 'data/sanborn/unet_data', 'data/sanborn/picks22_guided', 'data/sanborn/streetmap', 'data/sanborn/cufp', 'configs'):
    for d, _, fs in os.walk(C.REPO + root):
        for f in fs:
            p = os.path.join(d, f)
            if os.path.getmtime(p) > t0: newer.append(p.replace('\\', '/')[len(C.REPO):])
pyc = [d for d, _, _ in os.walk(C.STAGED) if '__pycache__' in d]
r90 = json.load(open(C.DATA + 'picks22_guided/22-90/rail_ben.json')); r44 = json.load(open(C.DATA + 'picks22_guided/22-44/rail_ben.json'))
res = dict(repo_hashes=got, hashes_as_given=got == want, newer_than_start=newer, pycache_in_staged=pyc, rail_ben_90_tracks=len(r90['tracks']), rail_ben_44_tracks=len(r44['tracks']),
           edges_ben_90_exists=os.path.exists(C.DATA + 'picks22_guided/22-90/edges_ben.json'), data_sanborn_new_dirs=sorted(set(os.listdir(C.DATA)) - set(json.load(open(C.IMPL + 'data_dirs_at_start.json')))))
json.dump(res, open(C.IMPL + 'safety.json', 'w'), indent=1); print(json.dumps(res, indent=1))
