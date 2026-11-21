"""v-code: run a staged script with the review shim, cwd data/sanborn, and record its peak memory (Windows)."""
import ctypes, ctypes.wintypes as wt, json, os, subprocess, sys, time
REPO = 'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/'
DATA = REPO + 'data/sanborn/'; MERGE = DATA + 'bench_2026-11-21/merge/'; ME = MERGE + 'v-code/'
SU = MERGE + 'staged/tools/sanborn/unet/'; RU = REPO + 'tools/sanborn/unet'
VPY = RU + '/.venv/Scripts/python.exe'; SYSPY = 'python'
class PMC(ctypes.Structure):
    _fields_ = [('cb', wt.DWORD), ('PageFaultCount', wt.DWORD), ('PeakWorkingSetSize', ctypes.c_size_t), ('WorkingSetSize', ctypes.c_size_t),
                ('QuotaPeakPagedPoolUsage', ctypes.c_size_t), ('QuotaPagedPoolUsage', ctypes.c_size_t), ('QuotaPeakNonPagedPoolUsage', ctypes.c_size_t),
                ('QuotaNonPagedPoolUsage', ctypes.c_size_t), ('PagefileUsage', ctypes.c_size_t), ('PeakPagefileUsage', ctypes.c_size_t)]
def peak(h):
    c = PMC(); c.cb = ctypes.sizeof(PMC)
    ok = ctypes.windll.psapi.GetProcessMemoryInfo(wt.HANDLE(int(h)), ctypes.byref(c), c.cb)
    return (c.PeakWorkingSetSize, c.PeakPagefileUsage) if ok else (None, None)
def run(cmd, cwd=DATA, extra_env=None):
    e = dict(os.environ); e['PYTHONPATH'] = ME + 'shim' + os.pathsep + RU; e['PYTHONDONTWRITEBYTECODE'] = '1'; e.update(extra_env or {})
    t0 = time.time(); p = subprocess.Popen(cmd, cwd=cwd, env=e, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding='utf8', errors='replace')
    pk = (0, 0); import threading
    res = {}
    def rd(): res['out'], res['err'] = p.communicate()
    th = threading.Thread(target=rd); th.start()
    while th.is_alive():
        v = peak(p._handle)
        if v[0]: pk = (max(pk[0], v[0]), max(pk[1], v[1]))
        time.sleep(0.25)
    th.join()
    return dict(code=p.returncode, out=res['out'], err=res['err'], sec=round(time.time() - t0, 1), peak_ws_gb=round(pk[0] / 2**30, 2), peak_commit_gb=round(pk[1] / 2**30, 2))
if __name__ == '__main__':
    r = run(sys.argv[1:]); print(r['out'][-3000:]); print(r['err'][-3000:], file=sys.stderr)
    print(json.dumps({k: r[k] for k in ('code', 'sec', 'peak_ws_gb', 'peak_commit_gb')}))
