"""Network time per plate (GPU, DirectML, AMD RX 7900 XTX), gathered from the runs' info files.

    python timing_summary.py      -> timing.json

The machine was shared with other agents' CPU jobs all afternoon (CPU at 100% from about 12:25), and the network passes
also use the CPU (tile cutting, transfers, flips), so times from later runs are inflated and uneven. The cleanest are
the first make_maps44.py run (12:1x, logs/make_maps44.log) and repro_batch44.py. Seconds exclude reading the scan and
the outline step (CPU, 16-23 s in bench44).
"""
import glob, json, os
HERE = os.path.dirname(os.path.abspath(__file__)).replace('\\', '/') + '/'
out = {}
first = {}
for line in open(HERE + 'logs/make_maps44.log', encoding='utf8'):
    if line.startswith('{'):
        d = json.loads(line); first[d['name']] = d['seconds']
out['plate44_first_run_low_load'] = first
out['plate44_repro_batch44'] = {k: v for k, v in json.load(open(HERE + 'logs/repro_batch44.json')).items() if k.endswith('_s')}
out['plate44_test_patch_patched_code'] = {k: v for k, v in json.load(open(HERE + 'logs/test_patch.json')).items() if k.endswith('_s')}
out['plate44_all_variants_any_load'] = {os.path.basename(os.path.dirname(f)): json.load(open(f))['seconds'] for f in sorted(glob.glob(HERE + 'maps/*/info.json'))}
pl = {}
for f in sorted(glob.glob(HERE + 'maps_plates/*/*_info.json')):
    d = json.load(open(f)); pl.setdefault(d['setting'], {})[d['plate']] = dict(size=d['size'], **d['seconds'])
out['plates_400ft'] = pl
json.dump(out, open(HERE + 'timing.json', 'w'), indent=1)
for k in ('batch', 'a_tta4', 'a_tta8', 'a_hann', 'a_hann_tta8', 'l_tta8', 'l_hann', 'l_hann_tta8'):
    if k in first: print(f'{k:14s} area {first[k]["area_s"]:6.2f} s  lines {first[k]["lines_s"]:6.2f} s')
for s, d in pl.items():
    tt = [v['area_s'] + v['lines_s'] for v in d.values()]
    print(s, 'plates', len(tt), 'networks s: min %.0f median %.0f max %.0f' % (min(tt), sorted(tt)[len(tt) // 2], max(tt)))
