"""Selection agent (23 Nov 2026): what one plate costs the line net's loader, in RAM and seconds. System Python, CPU only.

    python -B load_cost.py N [N ...]     -> load_cost.json in this folder (appends by plate)

Rebuilds what edgenet.load holds for a plate (x: H x W x 7 uint8; t: H x W uint8; wgt: H x W float32), the same steps
in the same order, from the scan (cufp/22-N.jpg), the area map (unet_data/N_pred_area_ng1.png, half size, made
full size), a stand-in target (a lines.png would be read here; the line net's map unet_data/N_lines_lines_ng1.png > 127
is used, it has the same size) and the paper (cufp/N/png_alpha_s4.npy). Nothing is written but the json.
Reports the resident bytes per full-size pixel, the seconds, and the process's peak working set (Windows).
"""
import ctypes, json, os, sys, time
from ctypes import wintypes
import numpy as np
import cv2

SP = 'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn/'; U = SP + 'unet_data/'
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'load_cost.json')
LINE, GAP, NEG_INK, POS = 3, 4, 4.0, 3.0


class PMC(ctypes.Structure):
    _fields_ = [('cb', wintypes.DWORD), ('PageFaultCount', wintypes.DWORD), ('PeakWorkingSetSize', ctypes.c_size_t), ('WorkingSetSize', ctypes.c_size_t),
                ('QuotaPeakPagedPoolUsage', ctypes.c_size_t), ('QuotaPagedPoolUsage', ctypes.c_size_t), ('QuotaPeakNonPagedPoolUsage', ctypes.c_size_t),
                ('QuotaNonPagedPoolUsage', ctypes.c_size_t), ('PagefileUsage', ctypes.c_size_t), ('PeakPagefileUsage', ctypes.c_size_t)]


def mem():
    c = PMC(); c.cb = ctypes.sizeof(PMC); k32 = ctypes.WinDLL('kernel32'); ps = ctypes.WinDLL('psapi')
    k32.GetCurrentProcess.restype = wintypes.HANDLE; ps.GetProcessMemoryInfo.argtypes = [wintypes.HANDLE, ctypes.POINTER(PMC), wintypes.DWORD]
    ps.GetProcessMemoryInfo(k32.GetCurrentProcess(), ctypes.byref(c), c.cb)
    return c.WorkingSetSize, c.PeakWorkingSetSize


def ink_image(bgr):
    hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV); gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    ink = (hsv[:, :, 2] < 120) | ((hsv[:, :, 1] < 90) & (hsv[:, :, 2] < 170))
    return np.where(ink, gray, 255).astype(np.uint8), ink


def load(N):
    t0 = time.time(); full = cv2.imread(SP + f'cufp/22-{N}.jpg'); H, W = full.shape[:2]; t_read = time.time() - t0
    inkimg, ink = ink_image(full)
    z = np.zeros((H, W), np.uint8)
    sp = cv2.resize(cv2.imread(U + f'{N}_pred_area_ng1.png', 0), (W, H), interpolation=cv2.INTER_LINEAR)
    x = np.dstack([full[:, :, ::-1], inkimg, z, z, sp]); del full
    line = (cv2.imread(U + f'{N}_lines_lines_ng1.png', 0) > 127).astype(np.uint8)
    alpha = cv2.resize(np.load(SP + f'cufp/{N}/png_alpha_s4.npy').astype(np.float32), (W, H)) > 0.5
    near = cv2.dilate(line, np.ones((2 * (LINE + GAP) + 1, 2 * (LINE + GAP) + 1), np.uint8)) > 0
    t = np.where(line > 0, 1, 0).astype(np.uint8); t[near & (line == 0)] = 255; t[~alpha] = 255
    wgt = np.ones((H, W), np.float32); wgt[ink & (t == 0)] = NEG_INK; wgt[t == 1] = POS
    return x, t, wgt, time.time() - t0, t_read


def main():
    res = json.load(open(OUT, encoding='utf8')) if os.path.exists(OUT) else {}
    keep = []
    for N in sys.argv[1:]:
        before, _ = mem(); x, t, wgt, sec, rd = load(N); after, peak = mem()
        keep.append((x, t, wgt))
        px = x.shape[0] * x.shape[1]; held = x.nbytes + t.nbytes + wgt.nbytes
        res[N] = dict(W=x.shape[1], H=x.shape[0], full_mpx=round(px / 1e6, 2), x_bytes=x.nbytes, t_bytes=t.nbytes, wgt_bytes=wgt.nbytes, held_bytes_per_px=round(held / px, 2),
                      held_gb=round(held / 2 ** 30, 2), seconds=round(sec, 1), jpeg_read_seconds=round(rd, 1), working_set_growth_gb=round((after - before) / 2 ** 30, 2),
                      peak_working_set_gb_so_far=round(peak / 2 ** 30, 2))
        print(N, res[N], flush=True)
    json.dump(res, open(OUT, 'w', encoding='utf8', newline='\n'), indent=1)


if __name__ == '__main__':
    main()
