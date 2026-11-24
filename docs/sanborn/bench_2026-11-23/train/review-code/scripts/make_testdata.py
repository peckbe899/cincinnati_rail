"""review-code: a small data folder in the train_v2 format, cut from train_v2/1A (with its validation edge inside the
window) and train_v2/43, for CPU tests of the staged trainers. Reads train_v2 and cufp; writes only review-code/testdata/.

    python -B make_testdata.py
"""
import hashlib, json, os, shutil
import cv2, numpy as np
SP = 'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn/'
OUT = SP + 'bench_2026-11-23/train/review-code/testdata/'
WIN = {'T1': ('1A', 832, 980), 'T2': ('43', 1536, 4608), 'T3': ('43', 128, 4352)}   # plate, half-size y, x; 512 x 640 half
H2, W2 = 512, 640


def sha(p): return hashlib.sha256(open(p, 'rb').read()).hexdigest()


if os.path.isdir(OUT): shutil.rmtree(OUT)
man = dict(note='review-code test data', plates={})
for name, (src, y, x) in WIN.items():
    d = OUT + name + '/'; os.makedirs(d)
    s = SP + f'train_v2/{src}/'
    for f in ('label.png', 'edge.png', 'area_in.png', 'valmask.png'):
        a = cv2.imread(s + f, 0)
        if a is None: continue
        a = a[y:y + H2, x:x + W2]
        if f == 'valmask.png' and not a.any(): continue
        cv2.imwrite(d + f, a)
    cv2.imwrite(d + 'img.jpg', cv2.imread(s + 'img.jpg')[y:y + H2, x:x + W2], [cv2.IMWRITE_JPEG_QUALITY, 95])
    full = cv2.imread(SP + f'cufp/22-{src}.jpg')[2 * y:2 * y + 2 * H2, 2 * x:2 * x + 2 * W2]
    cv2.imwrite(d + 'full.jpg', full, [cv2.IMWRITE_JPEG_QUALITY, 95])
    cv2.imwrite(d + 'lines.png', cv2.imread(s + 'lines.png', 0)[2 * y:2 * y + 2 * H2, 2 * x:2 * x + 2 * W2])
    meta = dict(plate=name, source='label' if src != '1A' else 'map', cut_from=dict(plate=src, half_y=y, half_x=x, h=H2, w=W2), ft_per_inch=100)
    json.dump(meta, open(d + 'meta.json', 'w'), indent=1)
    man['plates'][name] = dict(source=meta['source'], files={f: sha(d + f) for f in sorted(os.listdir(d)) if f != 'meta.json'}, meta_sha256=sha(d + 'meta.json'))
    print(name, sorted(os.listdir(d)))
json.dump(man, open(OUT + 'manifest.json', 'w'), indent=1)
print('wrote', OUT)
