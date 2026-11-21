"""merge/impl: how long ink_bins.railroad() takes on a plate (read-only; imports the repo's ink_bins.py with -B)."""
import sys, time, os
import numpy as np, cv2
sys.path.insert(0, 'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/tools/sanborn/unet')
import ink_bins as IB
N = sys.argv[1]; D = 'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn/'
im = cv2.imread(D + f'cufp/22-{N}.jpg'); H, W = im.shape[:2]
L = cv2.cvtColor(im, cv2.COLOR_BGR2LAB)[..., 0]
paper = cv2.resize(np.load(D + f'cufp/{N}/png_alpha_s4.npy'), (W, H), interpolation=cv2.INTER_NEAREST) > 0
ink = (L < IB.INK_L) & paper; closed = np.zeros((H, W), np.uint8)
t = time.time(); rr, info = IB.railroad(ink, closed, paper); print(N, 'railroad() s', round(time.time() - t, 1), 'px', int(rr.sum()))
