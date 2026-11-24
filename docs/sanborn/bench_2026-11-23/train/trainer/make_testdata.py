"""TEST data folder for the trainer smoke tests (bench_2026-11-23/train/trainer/testdata). NOT training labels.

    VENV -B make_testdata.py

- 80: a labelled plate, copied from unet_data byte for byte (img.jpg, label.png, edge.png, area_in.png =
  80_pred_area_ng1.png); lines.png is the target the REPO's edgenet.load('80') builds today (--no-guide); valmask.png
  the right-hand quarter (half size, cut = int(w * 0.75), as unet.train's quarter hold-out).
- 1A: a crude stand-in for a pseudo plate, only to exercise the code: img.jpg made as make_labels.py makes N_img.jpg;
  label.png = 1A_pred_area_ng1.png > 0.95 -> 1, < 0.05 -> 0, else 255 (and 255 off the paper); edge.png empty;
  lines.png = Ben's 1A lines (street_map.editor_lines of unet_data/1A_edges.json with his edges_ben.json) drawn 3 px
  wide with edgenet.load's margin and off-paper rules; area_in.png = 1A_pred_area_ng1.png; valmask.png the right quarter.
Reads only; writes only into testdata/ beside this file.
"""
import hashlib, json, os, shutil, sys
sys.dont_write_bytecode = True
REPO = 'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/'
sys.path.insert(0, REPO + 'tools/sanborn/unet'); sys.path.insert(0, REPO + 'tools/sanborn')
sys.argv = [sys.argv[0], '--no-guide', '--area', 'area_ng1']   # the repo edgenet reads these at import
import numpy as np, cv2
import edgenet as E_repo          # the REPO's edgenet.py (its load() is the reference for lines.png)
import street_map as SM           # the REPO's street_map.editor_lines
SP = REPO + 'data/sanborn/'; U = SP + 'unet_data/'
OUT = os.path.dirname(os.path.abspath(__file__)).replace('\\', '/') + '/testdata/'


def sha(p): return hashlib.sha256(open(p, 'rb').read()).hexdigest()


def quarter(h, w):
    v = np.zeros((h, w), np.uint8); v[:, int(w * 0.75):] = 1; return v


def plate80():
    d = OUT + '80/'; os.makedirs(d, exist_ok=True)
    for a, b in (('80_img.jpg', 'img.jpg'), ('80_label.png', 'label.png'), ('80_edge.png', 'edge.png'), ('80_pred_area_ng1.png', 'area_in.png')): shutil.copyfile(U + a, d + b)
    _, t, _ = E_repo.load('80'); cv2.imwrite(d + 'lines.png', t)
    lab = cv2.imread(d + 'label.png', 0); cv2.imwrite(d + 'valmask.png', quarter(*lab.shape))
    json.dump(dict(plate='80', source='label', test_only=True, scale_ft_per_inch=200, note='TRAINER SMOKE TEST copy of the labelled plate',
                   made={'img.jpg': 'copy of unet_data/80_img.jpg', 'label.png': 'copy of unet_data/80_label.png', 'edge.png': 'copy of unet_data/80_edge.png',
                         'area_in.png': 'copy of unet_data/80_pred_area_ng1.png (IN SAMPLE: area_ng1 was trained on 80)', 'lines.png': "the repo's edgenet.load('80') target, --no-guide",
                         'valmask.png': 'right-hand quarter, half size'},
                   area_in=dict(file='unet_data/80_pred_area_ng1.png', in_sample=True)), open(d + 'meta.json', 'w'), indent=1)
    return t.shape


def plate1A():
    d = OUT + '1A/'; os.makedirs(d, exist_ok=True)
    full = cv2.imread(SP + 'cufp/22-1A.jpg'); H, W = full.shape[:2]
    img = cv2.resize(full, (W // 2, H // 2), interpolation=cv2.INTER_AREA); cv2.imwrite(d + 'img.jpg', img, [cv2.IMWRITE_JPEG_QUALITY, 92])
    pa = cv2.imread(U + '1A_pred_area_ng1.png', 0); h, w = pa.shape
    alpha = cv2.resize(np.load(SP + 'cufp/1A/png_alpha_s4.npy').astype(np.float32), (w, h), interpolation=cv2.INTER_LINEAR) > 0.5
    lab = np.full((h, w), 255, np.uint8); lab[pa > 0.95 * 255] = 1; lab[pa < 0.05 * 255] = 0; lab[~alpha] = 255
    cv2.imwrite(d + 'label.png', lab); cv2.imwrite(d + 'edge.png', np.zeros((h, w), np.uint8)); shutil.copyfile(U + '1A_pred_area_ng1.png', d + 'area_in.png')
    L, _ = SM.editor_lines('1A', W, H, json.load(open(U + '1A_edges.json', encoding='utf8')), json.load(open(SP + 'picks22_guided/22-1A/edges_ben.json', encoding='utf8')))
    line = np.zeros((H, W), np.uint8)
    for l in L: cv2.line(line, tuple(np.round(l['a']).astype(int)), tuple(np.round(l['b']).astype(int)), 1, E_repo.LINE)
    labF = cv2.resize(lab, (W, H), interpolation=cv2.INTER_NEAREST); alphaF = cv2.resize(np.load(SP + 'cufp/1A/png_alpha_s4.npy').astype(np.float32), (W, H)) > 0.5
    k = 2 * (E_repo.LINE + E_repo.GAP) + 1; near = cv2.dilate(line, np.ones((k, k), np.uint8)) > 0
    t = line.copy(); t[(labF == 255) & ~near] = 255; t[near & (line == 0)] = 255; t[~alphaF] = 255
    cv2.imwrite(d + 'lines.png', t); cv2.imwrite(d + 'valmask.png', quarter(h, w))
    json.dump(dict(plate='1A', source='test-pseudo', test_only=True, scale_ft_per_inch=100, note='TRAINER SMOKE TEST: crude stand-in labels, not training labels',
                   made={'img.jpg': 'cufp/22-1A.jpg at half size, INTER_AREA, JPEG 92 (as make_labels.py)', 'label.png': 'area_ng1 P > 0.95 block, < 0.05 street, else 255',
                         'edge.png': 'empty', 'lines.png': f"Ben's 1A editor lines ({len(L)}), 3 px, edgenet.load margins", 'area_in.png': 'copy of unet_data/1A_pred_area_ng1.png (out of sample)',
                         'valmask.png': 'right-hand quarter, half size'},
                   area_in=dict(file='unet_data/1A_pred_area_ng1.png', in_sample=False)), open(d + 'meta.json', 'w'), indent=1)
    return t.shape


if __name__ == '__main__':
    os.makedirs(OUT, exist_ok=True)
    s80 = plate80(); s1a = plate1A()
    man = dict(note='TRAINER SMOKE TEST data folder (not train_v2)', plates={})
    for p in ('80', '1A'):
        m = json.load(open(OUT + f'{p}/meta.json'))
        man['plates'][p] = dict(source=m['source'], files={f: sha(OUT + f'{p}/{f}') for f in sorted(os.listdir(OUT + p))})
    json.dump(man, open(OUT + 'manifest.json', 'w'), indent=1)
    print('80 full', s80, '1A full', s1a)
    print(json.dumps(man, indent=1)[:1500])
