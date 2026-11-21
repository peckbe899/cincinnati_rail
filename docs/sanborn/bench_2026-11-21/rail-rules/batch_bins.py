"""Re-run the proposed ink_bins.py on batch plates, writes only into rail-rules/batch/ (rail-rules, 21 Nov 2026), and
compare each result with the batch's own unet_data/N_bins.png (read only).
    cd data/sanborn
    python bench_2026-11-21/rail-rules/batch_bins.py [-j 3] [--rail JSON --tag TAG] N [N ...]   or  --keyplates
--keyplates: the 36 plates whose KEY the proposed key_box() finds (key/key_scan_top.json, mean score >= 0.62).
Writes batch/[TAG_]N_bins.png, batch/[TAG_]N.log and batch/[TAG_]bins_compare.json: pixels that differ from the batch's
bins, how many of them lie inside the KEY box, and the railroad / streetcar bin px before and after."""
import sys, os, json, subprocess, re
from concurrent.futures import ThreadPoolExecutor
import numpy as np, cv2
HERE = os.path.dirname(os.path.abspath(__file__)); OUT = os.path.join(HERE, 'batch'); os.makedirs(OUT, exist_ok=True)
a = sys.argv[1:]; jobs = int(a[a.index('-j') + 1]) if '-j' in a else 3
rail = a[a.index('--rail') + 1] if '--rail' in a else None; tag = (a[a.index('--tag') + 1] + '_') if '--tag' in a else ''
skip = {a[i + 1] for i, x in enumerate(a) if x in ('-j', '--rail', '--tag')}
if '--keyplates' in a:
    K = json.load(open(os.path.join(HERE, 'key/key_scan_top.json'))); plates = [r['plate'] for r in K if (r['T19top'] + r['T86top']) / 2 >= 0.62]
else: plates = [x for x in a if not x.startswith('-') and x not in skip]


def one(N):
    o = os.path.join(OUT, f'{tag}{N}_bins.png'); log = os.path.join(OUT, f'{tag}{N}.log')
    cmd = [sys.executable, os.path.join(HERE, 'run_ink_bins.py'), N, o] + (['--rail', rail] if rail else [])
    with open(log, 'w') as f: r = subprocess.run(cmd, stdout=f, stderr=subprocess.STDOUT)
    if r.returncode: return dict(plate=N, error=open(log).read()[-500:])
    new = cv2.imread(o, 0); old = cv2.imread(f'unet_data/{N}_bins.png', 0); d = new != old
    txt = open(log).read(); m = re.search(r'the printed KEY at \((\d+), (\d+), (\d+), (\d+)\)', txt); kb = [int(v) for v in m.groups()] if m else None
    ink = np.zeros_like(d)
    if kb: ink[kb[1]:kb[3], kb[0]:kb[2]] = True
    res = dict(plate=N, key=kb, differ_px=int(d.sum()), differ_outside_key=int((d & ~ink).sum()),
               rr_before=int((old == 4).sum()), rr_after=int((new == 4).sum()), sc_before=int((old == 5).sum()), sc_after=int((new == 5).sum()),
               rr_in_key_before=int(((old == 4) & ink).sum()), sc_in_key_before=int(((old == 5) & ink).sum()))
    print(json.dumps(res), flush=True); return res


with ThreadPoolExecutor(jobs) as ex: R = list(ex.map(one, plates))
json.dump(R, open(os.path.join(OUT, f'{tag}bins_compare.json'), 'w'), indent=1)
print('plates', len(R), 'errors', sum('error' in r for r in R), 'differ outside KEY', sum(r.get('differ_outside_key', 0) for r in R))
