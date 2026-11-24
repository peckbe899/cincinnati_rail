"""Memory of the staged line trainer's plate store for 20 plates, measured (no GPU, no training).

    VENV -B memtest.py [N]          (default 20: the N largest plates of the census by W x H, never 44 or 90)

Each plate's scan (cufp/22-N.jpg) is read and packed with the STAGED edgenet.pack (H x W x 5 uint8; the 7th input and
the target are zeros here, which does not change the size); the process's working set and private bytes are read after
each (Windows GetProcessMemoryInfo) and with the machine's free memory (GlobalMemoryStatusEx). The area trainer's store
at half size (5-channel input + label uint8, edge weights float32, edge target uint8: 11 bytes per half-size px) is
allocated and touched on top, as both are never held in one process, but this bounds a driver that did.
Also prints what today's edgenet.load would hold (12 bytes a px). Writes memtest.json beside this file.
"""
import csv, ctypes, ctypes.wintypes as wt, importlib.util, json, os, sys, time
sys.dont_write_bytecode = True
REPO = 'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/'; SP = REPO + 'data/sanborn/'
HERE = os.path.dirname(os.path.abspath(__file__)).replace('\\', '/') + '/'
STAGED = REPO + 'data/sanborn/bench_2026-11-23/train/staged/tools/sanborn/unet/'
sys.path.insert(0, REPO + 'tools/sanborn'); sys.path.insert(0, STAGED)
import numpy as np, cv2
import unet as UN, edgenet as EN


class MS(ctypes.Structure):
    _fields_ = [('dwLength', wt.DWORD), ('dwMemoryLoad', wt.DWORD), ('ullTotalPhys', ctypes.c_ulonglong), ('ullAvailPhys', ctypes.c_ulonglong), ('ullTotalPageFile', ctypes.c_ulonglong),
                ('ullAvailPageFile', ctypes.c_ulonglong), ('ullTotalVirtual', ctypes.c_ulonglong), ('ullAvailVirtual', ctypes.c_ulonglong), ('ullAvailExtendedVirtual', ctypes.c_ulonglong)]


def free_gb():
    m = MS(); m.dwLength = ctypes.sizeof(MS); ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(m)); return round(m.ullAvailPhys / 1e9, 2)


if __name__ == '__main__':
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 20
    rows = list(csv.DictReader(open(SP + 'bench_2026-11-21/census/census.csv', encoding='utf8')))
    big = sorted(((int(r['W']) * int(r['H']), r['plate']) for r in rows if r['plate'] not in ('44', '90')), reverse=True)[:n]
    f0 = free_gb()
    if f0 < 15: sys.exit(f'only {f0} GB free: not run')
    out = dict(plates=[p for _, p in big], free_gb_before=f0, start=UN.mem_now(), per_plate=[]); store = []; t0 = time.time(); px = 0
    for _, p in big:
        t1 = time.time(); full = cv2.imread(SP + f'cufp/22-{p}.jpg'); H, W = full.shape[:2]
        S = EN.pack(full, None, np.zeros((H, W), np.uint8)); del full; store.append(S); px += H * W
        out['per_plate'].append(dict(plate=p, W=W, H=H, mpx=round(H * W / 1e6, 2), stored_gb=round(S.nbytes / 1e9, 3), seconds=round(time.time() - t1, 1), process=UN.mem_now(), free_gb=free_gb()))
        print(json.dumps(out['per_plate'][-1]), flush=True)
    out['lines_store'] = dict(plates=len(store), mpx=round(px / 1e6, 1), stored_gb=round(sum(S.nbytes for S in store) / 1e9, 2), seconds=round(time.time() - t0, 1), process=UN.mem_now(), free_gb=free_gb(),
                              todays_load_would_hold_gb=round(px * 12 / 1e9, 2))
    A = []
    for S in store:
        h, w = S.shape[0] // 2, S.shape[1] // 2
        a = dict(x=np.ones((h, w, 5), np.uint8), lab=np.ones((h, w), np.uint8), wm=np.ones((h, w), np.float32), et=np.ones((h, w), np.uint8)); A.append(a)
    out['plus_area_store'] = dict(stored_gb=round(sum(sum(v.nbytes for v in a.values()) for a in A) / 1e9, 2), process=UN.mem_now(), free_gb=free_gb())
    print(json.dumps({k: v for k, v in out.items() if k != 'per_plate'}, indent=1))
    json.dump(out, open(HERE + 'memtest.json', 'w'), indent=1)
