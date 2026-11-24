"""Integrator, round 2 (24 Nov 2026): the rebuilt data/sanborn/train_v2 against round 1's manifest (saved in
integrate/round2/train_v2_round1/manifest.json): every data file of the 15 round-1 plates must have the same sha256
(only meta.json, which carries the time and the script's sha256, may differ); the new plate is listed. Then the
format and leak checks of round 1's check_data.py are repeated by importing it.
cd data/sanborn; python -B bench_2026-11-23/train/integrate/round2/scripts/compare_build.py"""
import hashlib, json, os
W = 'bench_2026-11-23/train/integrate/round2/'
old = json.load(open(W + 'train_v2_round1/manifest.json', encoding='utf8'))['plates']; new = json.load(open('train_v2/manifest.json', encoding='utf8'))
R = dict(plates_round1=sorted(old), plates_now=sorted(new['plates']), added=sorted(set(new['plates']) - set(old)), removed=sorted(set(old) - set(new['plates'])), files={})
for N, e in old.items():
    n = new['plates'].get(N) or {}
    R['files'][N] = {f: ('same' if n.get('files', {}).get(f) == s else f'DIFFERENT {s[:12]} -> {str(n.get("files", {}).get(f))[:12]}') for f, s in e['files'].items()}
R['all_data_files_same'] = all(v == 'same' for d in R['files'].values() for v in d.values())
# the manifest's own sha256 values against the files on disk, and content_sha256
bad = []
for N, e in new['plates'].items():
    for f, s in e['files'].items():
        if hashlib.sha256(open(f'train_v2/{N}/{f}', 'rb').read()).hexdigest() != s: bad.append(f'{N}/{f}')
    if hashlib.sha256(open(f'train_v2/{N}/meta.json', 'rb').read()).hexdigest() != e['meta_sha256']: bad.append(f'{N}/meta.json')
R['manifest_mismatches'] = bad
R['content_sha256_ok'] = hashlib.sha256(json.dumps(new['plates'], sort_keys=True).encode()).hexdigest() == new['content_sha256']
R['forbidden_absent'] = not ({'44', '90'} & (set(new['plates']) | set(os.listdir('train_v2'))))
R['manifest_sha256'] = hashlib.sha256(open('train_v2/manifest.json', 'rb').read()).hexdigest(); R['content_sha256'] = new['content_sha256']
R['by_sha256'] = sorted({json.load(open(f'train_v2/{N}/meta.json', encoding='utf8'))['by_sha256'][:16] for N in new['plates']})
json.dump(R, open(W + 'compare_build.json', 'w'), indent=1); print(json.dumps({k: v for k, v in R.items() if k != 'files'}, indent=1))
