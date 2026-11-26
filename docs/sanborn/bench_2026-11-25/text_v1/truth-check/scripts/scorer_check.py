"""scorer_check.py SCRATCH_DIR - checks that text_v1/code/score_text.py runs on the held-out crops H1-H4 and gives the
expected numbers on masks whose answer is known. Uses only the truth files (no finder, no other method). It writes test
masks into SCRATCH_DIR (they are temporary) and the scorer outputs into truth-check/scores/.
Run from data/sanborn:  python -B bench_2026-11-25/text_v1/truth-check/scripts/scorer_check.py <scratch dir>"""
import os, sys, json, subprocess, shutil
import numpy as np, cv2
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import tc

SC = os.path.join(tc.V1, 'code', 'score_text.py')
FIX = tc.FIXED; OUT = os.path.join(tc.KEY, 'scores'); os.makedirs(OUT, exist_ok=True)
IDS = ['H1', 'H2', 'H3', 'H4']


def run(name, mask, mode, truth=FIX, extra=()):
    cmd = [sys.executable, '-B', SC, mask] + (['--binary'] if mode == 'binary' else ['--codes', mode]) + ['--truth', truth, '--out', os.path.join(OUT, name + '.json')] + list(extra)
    r = subprocess.run(cmd, cwd=tc.ROOT, capture_output=True, text=True)
    txt = f'$ {" ".join(os.path.relpath(c, tc.ROOT) if os.path.isabs(c) and c.startswith(tc.ROOT) else c for c in cmd[1:])}\n{r.stdout}{r.stderr}'
    open(os.path.join(OUT, name + '.txt'), 'w', encoding='utf8').write(txt)
    print(f'=== {name}\n{txt}')
    return json.load(open(os.path.join(OUT, name + '.json'))) if r.returncode == 0 else None


def main():
    scr = os.path.abspath(sys.argv[1]); os.makedirs(scr, exist_ok=True)
    crops = json.load(open(os.path.join(FIX, 'crops.json')))
    # 1. the delivered held-out folder has no crops.json: the scorer stops
    r = subprocess.run([sys.executable, '-B', SC, os.path.join(tc.HELD, '{crop}_mask.png'), '--codes', '2', '--truth', tc.HELD], cwd=tc.ROOT, capture_output=True, text=True)
    print('=== heldout/ as delivered: return code', r.returncode, '|', (r.stderr.strip().splitlines() or [''])[-1])
    # 2. the fixed truth scored as its own prediction: every number must be 1
    a = run('self_codes2_cropsize', os.path.join(FIX, '{crop}_mask.png'), '2')
    # 3. a crop-sized 0/255 binary mask of the text, and the same text pasted into plate-sized masks
    plates = {}
    for c in IDS:
        t = tc.truth(c, True); cv2.imwrite(os.path.join(scr, f'{c}_bin.png'), np.where(t == 2, 255, 0).astype(np.uint8))
        p = crops[c]['plate']; x0, y0, x1, y1 = crops[c]['win']
        if p not in plates:
            H, W = tc.plate_img(p).shape[:2]; plates[p] = np.zeros((H, W), np.uint8)
        plates[p][y0:y1, x0:x1] = np.where(t == 2, 7, np.where(t > 0, 1, 0))      # text as code 7, other ink 1
    for p, m in plates.items(): cv2.imwrite(os.path.join(scr, f'{p}_plate.png'), m)
    b = run('self_binary_cropsize', os.path.join(scr, '{crop}_bin.png'), 'binary')
    c_ = run('self_code7_platesize', os.path.join(scr, '{plate}_plate.png'), '7')
    # 4. all ink called text, and nothing called text
    for c in IDS:
        t = tc.truth(c, True); cv2.imwrite(os.path.join(scr, f'{c}_allink.png'), np.where(t > 0, 255, 0).astype(np.uint8))
        cv2.imwrite(os.path.join(scr, f'{c}_empty.png'), np.zeros(t.shape, np.uint8))
    d = run('allink_binary', os.path.join(scr, '{crop}_allink.png'), 'binary')
    e = run('empty_binary', os.path.join(scr, '{crop}_empty.png'), 'binary')
    # 5. the delivered (unfixed) held-out truth scored against the fixed truth: how much the fixes moved
    f = run('delivered_vs_fixed', os.path.join(tc.HELD, '{crop}_mask.png'), '2', extra=['--group', 'H1H2=H1,H2', '--group', 'H3H4=H3,H4'])
    # expected values
    ok = []
    ok.append(('self crop-size codes', a['pools']['ALL']['pix']['f1'] == 1.0))
    ok.append(('self binary crop-size', b['pools']['ALL']['pix']['f1'] == 1.0))
    ok.append(('self plate-size code 7', c_['pools']['ALL']['pix']['f1'] == 1.0))
    tp = sum(int((tc.truth(c, True) == 2).sum()) for c in IDS); ink = sum(int(np.isin(tc.truth(c, True), [1, 2]).sum()) for c in IDS)
    ok.append(('all ink: recall 1, precision = text share of scored ink', d['pools']['ALL']['pix']['recall'] == 1.0 and abs(d['pools']['ALL']['pix']['precision'] - tp / ink) < 1e-4))
    ok.append(('empty: recall 0', e['pools']['ALL']['pix']['recall'] == 0.0))
    for n, v in ok: print(('PASS ' if v else 'FAIL ') + n)
    json.dump(dict(checks=[dict(check=n, passed=bool(v)) for n, v in ok], text_px=tp, scored_ink_px=ink), open(os.path.join(OUT, 'scorer_check.json'), 'w'), indent=1)


if __name__ == '__main__':
    main()
