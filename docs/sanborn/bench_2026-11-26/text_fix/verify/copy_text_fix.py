"""Copy the text_fix records (scripts, scores, truth masks, frozen finder4 models, block readings, key pictures) to docs.
python copy_text_fix.py SRC DST [--go]"""
import os, sys, shutil
SRC, DST = sys.argv[1], sys.argv[2]; GO = '--go' in sys.argv
SKIPDIR = ('_second_copy', '/runs/', '/rerun', '/pics/', '/work/', '/tmp/', '/out/dev', '/out/sel', '/out/repro', '/out/finder3/',
           '/finder3_runs/', '/finders/', '/base_samples', '/v0_merged/', '/truth_v1_frozen/', '/synthetic/', '__pycache__',
           '/data/', '/masks/', '/out/dittofix/', '/base/')
MASKDIRS = ('dev_block/truth/', 'dev_ditto/truth/', 'dev_ditto/negatives/', 'sealed_final/')
KEEP = {'integrate/models/' + f for f in ('tmpl_real_all.npz', 'cls_all.npz', 'num_all.npz', 'tmpl_real_A.npz', 'tmpl_real_B.npz',
                                          'cls_A.npz', 'cls_B.npz', 'num_A.npz', 'num_B.npz')}
KEEP |= {'gate/pics/sealed/miss_block_00.png'} | {f'gate/pics/sealed/miss_ditto_0{i}.png' for i in range(6)}
KEEP |= {f'sealed_check/pics/diff/fix1_0{i}.png' for i in range(3)} | {'sealed_check/pics/diff/fix2_00.png'}
KEEP |= {'skeptic/pics/p6_rail_dittos.png', 'skeptic/pics/straight_edge.png',
         'step4/pics/spots/44_28.png', 'step4/pics/spots/1A_15_wide.png'}
tot = n = 0; skipped_big = []; seen_keep = set()
for r, ds, fs in os.walk(SRC):
    for f in fs:
        p = os.path.join(r, f); rel = os.path.relpath(p, SRC).replace(os.sep, '/'); s = os.path.getsize(p)
        ext = os.path.splitext(f)[1].lower(); keep = False
        if rel in KEEP: keep = True; seen_keep.add(rel)
        elif any(k in '/' + rel for k in SKIPDIR): keep = False
        elif ext in ('.py', '.sh', '.md', '.csv'): keep = True
        elif ext in ('.txt', '.json'):
            keep = s < 400_000
            if not keep: skipped_big.append((rel, s))
        elif ext == '.png' and rel.startswith(MASKDIRS) and rel.count('/') == rel.split('/')[0].count('/') + MASKDIRS[[rel.startswith(m) for m in MASKDIRS].index(True)].count('/') and s < 3_000_000: keep = True
        if keep:
            tot += s; n += 1
            if GO:
                d = os.path.join(DST, rel); os.makedirs(os.path.dirname(d), exist_ok=True); shutil.copy2(p, d)
print(n, 'files', round(tot / 1e6, 1), 'MB', 'copied' if GO else '(dry run)')
for rel, s in skipped_big: print('  skipped big', rel, s)
for rel in sorted(KEEP - seen_keep): print('  KEEP not found', rel)
