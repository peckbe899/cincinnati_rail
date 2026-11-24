"""review-leak: the data folder train_v2/ against the plan. Reads only.
cd data/sanborn; python -B bench_2026-11-23/train/review-leak/scripts/data_checks.py"""
import hashlib, json, os, datetime
import numpy as np, cv2
OUT = 'bench_2026-11-23/train/review-leak/'; D = 'train_v2/'; U = 'unet_data/'


def sha(p):
    if not os.path.exists(p): return None
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''): h.update(b)
    return h.hexdigest()


def mt(p): return datetime.datetime.fromtimestamp(os.path.getmtime(p)).isoformat(timespec='seconds') if os.path.exists(p) else None


man = json.load(open(D + 'manifest.json', encoding='utf8')); P = man['plates']
dirs = sorted(d for d in os.listdir(D) if os.path.isdir(D + d))
R = dict(dirs=dirs, manifest_plates=sorted(P), forbidden_dirs=[d for d in dirs if d.strip().upper().lstrip('0') in ('44', '90') or d.upper().startswith(('44', '90'))],
         forbidden_manifest=[p for p in P if p.strip().upper().lstrip('0') in ('44', '90') or p.upper().startswith(('44', '90'))])
# content_sha256 as the docstring defines it: sha256 of the plates section, json with sorted keys
cs = [hashlib.sha256(json.dumps(P, sort_keys=True).encode()).hexdigest(), hashlib.sha256(json.dumps(P, sort_keys=True, separators=(',', ':')).encode()).hexdigest()]
R['content_sha256'] = dict(manifest=man.get('content_sha256'), recomputed_default=cs[0], recomputed_compact=cs[1])
test_img = {t: sha(U + f'{t}_img.jpg') for t in ('44', '90')}; test_scan = {t: sha(f'cufp/22-{t}.jpg') for t in ('44', '90')}
R['test_hashes'] = dict(img=test_img, scan=test_scan)
area_ng1_pt = U + 'models/area_ng1.pt'; R['area_ng1_pt_mtime'] = mt(area_ng1_pt)
an1 = json.load(open(U + 'models/area_ng1.json', encoding='utf8')); ln1 = json.load(open(U + 'models/lines_ng1.json', encoding='utf8'))
R['area_ng1_plates'] = an1['plates']; R['lines_ng1_plates'] = ln1['plates']
ng1_train = {s.split(':')[0] for s in an1['plates'] if not s.endswith(':val')}
plates = {}; img_sh = {}
for N in dirs:
    d = D + N + '/'; meta = json.load(open(d + 'meta.json', encoding='utf8')); e = P.get(N, {})
    r = dict(source=meta.get('source'), manifest_source=e.get('source'), files=sorted(os.listdir(d)))
    r['manifest_mismatch'] = [f for f, s in (e.get('files') or {}).items() if sha(d + f) != s]
    r['meta_sha_ok'] = sha(d + 'meta.json') == e.get('meta_sha256')
    r['full_jpg_present'] = os.path.exists(d + 'full.jpg')
    s_img = sha(d + 'img.jpg'); img_sh[N] = s_img
    r['img_equals_test'] = [t for t in ('44', '90') if s_img == test_img[t]]
    sc = (meta.get('scan') or {}); r['scan_meta'] = sc.get('path'); r['scan_sha_now'] = sha(f'cufp/22-{N}.jpg'); r['scan_sha_matches_meta'] = sc.get('sha256') in (None, r['scan_sha_now'])
    r['scan_equals_test'] = [t for t in ('44', '90') if r['scan_sha_now'] == test_scan[t]]
    # the 7th channel: byte for byte the batch's area_ng1 map?
    src = U + f'{N}_pred_area_ng1.png'
    r['area_in_equals_unet_data_pred_area_ng1'] = sha(d + 'area_in.png') == sha(src)
    r['pred_area_ng1_mtime'] = mt(src); r['area_in_in_sample_for_area_ng1'] = N in ng1_train
    r['area_in_meta'] = ((meta.get('files') or {}).get('area_in.png') or {}).get('note')
    if meta.get('source') == 'label':
        r['copied_equal'] = {f: sha(d + f) == sha(U + f'{N}_{g}') for f, g in (('img.jpg', 'img.jpg'), ('label.png', 'label.png'), ('edge.png', 'edge.png'))}
    lab = cv2.imread(d + 'label.png', 0); r['label_values'] = np.unique(lab).tolist(); r['half_shape'] = list(lab.shape)
    li = cv2.imread(d + 'lines.png', 0); r['lines_values'] = np.unique(li).tolist(); r['full_shape'] = list(li.shape)
    full = cv2.imread(f'cufp/22-{N}.jpg', cv2.IMREAD_REDUCED_GRAYSCALE_8); r['scan_shape_approx'] = [full.shape[0] * 8, full.shape[1] * 8]
    r['half_is_floor_half_of_lines'] = [li.shape[0] // 2, li.shape[1] // 2] == list(lab.shape)
    if os.path.exists(d + 'valmask.png'):
        v = cv2.imread(d + 'valmask.png', 0) > 0; cols = np.nonzero(v.any(0))[0]; rows_full = v[:, cols[0]:].all()
        r['valmask'] = dict(shape=list(v.shape), first_col=int(cols[0]), last_col=int(cols[-1]), half_plane=bool(rows_full and not v[:, :cols[0]].any()), share=round(float(v.mean()), 4),
                            taught_in=int((lab[v] != 255).sum()), block_in=int((lab[v] == 1).sum()), street_in=int((lab[v] == 0).sum()), taught_out=int((lab[~v] != 255).sum()))
    if meta.get('source') == 'map':
        srcs = meta.get('sources_sha256', {})
        r['map_sources_now'] = {k: dict(meta=s, now=sha('../../' + k if k.startswith('data/') else k)) for k, s in srcs.items()}
        r['map_sources_now'] = {k: dict(meta=s, now=sha(os.path.relpath(os.path.join('..', '..', k)))) for k, s in srcs.items()}
        r['edges_ben_mtime'] = mt('picks22_guided/22-1A/edges_ben.json')
    plates[N] = r; print(N, json.dumps({k: v for k, v in r.items() if k not in ('files',)}))
dup = {}
for a in img_sh:
    for b in img_sh:
        if a < b and img_sh[a] == img_sh[b]: dup[f'{a}={b}'] = True
R['duplicate_img'] = dup; R['plates'] = plates
json.dump(R, open(OUT + 'data_checks.json', 'w'), indent=1)
print(json.dumps({k: v for k, v in R.items() if k != 'plates'}, indent=1))
