"""make_masks.py (text/effect, 25 Nov 2026): the text masks tested here, written to masks/ as 0/255 PNGs, with counts
in masks/masks_N_G.json.
    cd data/sanborn; python -B bench_2026-11-25/text/effect/code/make_masks.py N G      (5 nets | 5 none | 44 map)

  S0   bin 8 of today's sorting (runs/N_G_base.png): text as it is today, sorted AFTER the railroad rule took its ink
  S1   bin 8 of the same sorting with the railroad rule's result thrown away (runs/N_G_norail.png): what today's text
       rules call text when rail has not taken ink first. The stand-in for a text-first stage built from bin 8
  S1g1, S1g2   S1 grown by 1 or 2 px (round 2's 'bin 8 grown 1 px')
  I    idealised: S1 plus every ink pixel within R px of S1 that is NOT line core (ink a straight 35 px line fits, the
       railroad rule's own 'long' test: ink_bins.railroad long_), minus the band of BEN_RAIL (10) px round Ben's checked
       tracks (rail_ben.json, both kinds). So: whole characters, including the strokes of a digit that touches a line,
       never the line itself, never ink on a real track. It uses the truth (Ben's tracks), so it is an upper bound on what
       a text stage could hand over, not something a rule can make by itself
  Inp  the same without the protection of Ben's tracks (what a rule could make without the truth)
Read-only on the repo."""
import sys, os, json, importlib.util
sys.dont_write_bytecode = True
import numpy as np, cv2
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE); MK = os.path.join(ROOT, 'masks')
spec = importlib.util.spec_from_file_location('ib_copy', os.path.join(HERE, 'orig', 'ink_bins.py')); IB = importlib.util.module_from_spec(spec); spec.loader.exec_module(IB)
N, G = sys.argv[1], sys.argv[2]; R = 8
RB = {'5': os.path.join(ROOT, 'inputs', 'rail_ben_5_copy.json'), '44': os.path.join(ROOT, 'inputs', 'rail_ben_44_copy.json')}[N]


def line_core(ink):
    """ink_bins.railroad's long_: ink under a straight 35 px line (24 directions) fitted in the ink grown by 1 px"""
    r8 = ink.astype(np.uint8); fat = cv2.dilate(r8, np.ones((3, 3), np.uint8)); lc = np.zeros_like(r8)
    for i in range(24):
        lc |= cv2.morphologyEx(fat, cv2.MORPH_OPEN, IB.line_kernel(35, np.pi * i / 24)) & r8
    return lc > 0


def main():
    im = cv2.imread(f'cufp/22-{N}.jpg'); H, W = im.shape[:2]
    L = cv2.cvtColor(im, cv2.COLOR_BGR2LAB)[..., 0]; del im
    paper = cv2.resize(np.load(f'cufp/{N}/png_alpha_s4.npy'), (W, H), interpolation=cv2.INTER_NEAREST) > 0
    ink = (L < IB.INK_L) & paper; del L
    B0 = cv2.imread(os.path.join(ROOT, 'runs', f'{N}_{G}_base.png'), 0); B1 = cv2.imread(os.path.join(ROOT, 'runs', f'{N}_{G}_norail.png'), 0)
    S0 = B0 == 8; S1 = B1 == 8
    LC = line_core(ink); np.save(os.path.join(MK, f'{N}_linecore.npy'), np.packbits(LC)) if G != 'none' else None
    ben = IB.ben_masks(json.load(open(RB, encoding='utf8'))['tracks'], H, W); band = (ben['railroad'] > 0) | (ben['streetcar'] > 0)
    near = cv2.distanceTransform((~S1).astype(np.uint8), cv2.DIST_L2, 5) <= R
    glued = ink & ~LC & near & ~S1
    Inp = S1 | glued; I = Inp & ~band
    M = dict(S0=S0, S1=S1, S1g1=cv2.dilate(S1.astype(np.uint8), np.ones((3, 3), np.uint8)) > 0, S1g2=cv2.dilate(S1.astype(np.uint8), np.ones((5, 5), np.uint8)) > 0, I=I, Inp=Inp)
    rec = dict(plate=N, ground=G, R=R, ink_px=int(ink.sum()), line_core_px=int(LC.sum()), ben_band_px=int(band.sum()), masks={})
    for k, m in M.items():
        cv2.imwrite(os.path.join(MK, f'{N}_{G}_{k}.png'), m.astype(np.uint8) * 255)
        mi = m & ink
        rec['masks'][k] = dict(mask_px=int(m.sum()), ink_px=int(mi.sum()), share_of_ink=round(float(mi.sum() / ink.sum()), 4), on_line_core=int((mi & LC).sum()),
                               on_ben_railroad_band=int((mi & (ben['railroad'] > 0)).sum()), on_ben_streetcar_band=int((mi & (ben['streetcar'] > 0)).sum()),
                               base_bins_of_its_ink={IB.NAMES.get(b, 'none'): int(c) for b, c in enumerate(np.bincount(B0[mi], minlength=10)) if c})
        print(k, rec['masks'][k], flush=True)
    rec['glued_px'] = int(glued.sum()); rec['glued_on_ben_band'] = int((glued & band).sum())
    json.dump(rec, open(os.path.join(MK, f'masks_{N}_{G}.json'), 'w'), indent=1)


if __name__ == '__main__':
    main()
