"""Does 1A teach 'blank paper = street' more than the old labels? Blank = no black/grey ink (edgenet's ink rule on the
half-size img.jpg) within 6 half px. Per training plate: share of taught street that is blank, share of taught block
that is blank, and P(street | blank, taught). On 44's undecided ground: of the pixels the baseline calls block and a
new area net calls street (grid0), the share that is blank. Reads only; system python."""
import json, glob, numpy as np, cv2
SP = 'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn/'; EV = SP + 'train_v2_runs/eval/'; OUT = SP + 'bench_2026-11-25/diag/recipe/'
def blank(img):
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV); ink = ((hsv[:, :, 2] < 120) | ((hsv[:, :, 1] < 90) & (hsv[:, :, 2] < 170))).astype(np.uint8)
    return cv2.dilate(ink, np.ones((13, 13), np.uint8)) == 0
res = {}
for p in ['43', '45', '80', '82A', '1A']:
    img = cv2.imread(SP + f'train_v2/{p}/img.jpg'); lab = cv2.imread(SP + f'train_v2/{p}/label.png', 0); b = blank(img)
    tr = np.ones(lab.shape, bool)
    if p == '1A': tr = cv2.imread(SP + 'train_v2/1A/valmask.png', 0) == 0
    st = (lab == 0) & tr; bl = (lab == 1) & tr
    res[p] = dict(street_blank=round(float(b[st].mean()), 3), block_blank=round(float(b[bl].mean()), 3), p_street_given_blank=round(float((st & b).sum() / max(1, ((st | bl) & b).sum())), 3),
                  blank_share_of_taught=round(float(b[st | bl].mean()), 3))
    print(p, res[p], flush=True)
img = cv2.resize(cv2.imread(SP + 'cufp/22-44.jpg'), None, fx=0.5, fy=0.5, interpolation=cv2.INTER_AREA); b44 = blank(img)
dec = cv2.imread(glob.glob(SP + 'bench_2026-11-23/train/integrate/round2/driver_mini/eval/runs_baseline44/cache/decided_half_*.png')[0], 0) > 0; h, w = dec.shape
b44 = b44[:h, :w]; al = cv2.resize(np.load(SP + 'cufp/44/png_alpha_s4.npy').astype(np.float32), (w, h)) > 0.5; und = al & ~dec
pb = cv2.imread(EV + 'baseline/maps44/grid0/44_area.png', 0) > 127
res['44_undecided_blank_share'] = round(float(b44[und].mean()), 3)
for s in ['V1S1', 'V2S1', 'V1S2', 'V2S2']:
    pv = cv2.imread(EV + f'{s}/maps44/grid0/44_area.png', 0) > 127; flip = und & pb & ~pv; back = und & ~pb & pv
    res[s] = dict(base_block_new_street_px=int(flip.sum()), of_which_blank=round(float(b44[flip].mean()), 3), base_street_new_block_px=int(back.sum()), of_which_blank_rev=round(float(b44[back].mean()), 3))
    print(s, res[s], flush=True)
json.dump(res, open(OUT + 'blank_paper.json', 'w'), indent=1); print(res['44_undecided_blank_share'])
