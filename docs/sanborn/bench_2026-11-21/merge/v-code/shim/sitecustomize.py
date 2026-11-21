import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _ws  # noqa: the review shim, so edit_server's later 'import _ws' does not load the repo's (_mirror)
if os.environ.get('V_PEAK_FILE'):
    import atexit, ctypes, ctypes.wintypes as wt, json, time
    class _PMC(ctypes.Structure):
        _fields_ = [('cb', wt.DWORD), ('PageFaultCount', wt.DWORD), ('PeakWorkingSetSize', ctypes.c_size_t), ('WorkingSetSize', ctypes.c_size_t),
                    ('a', ctypes.c_size_t), ('b', ctypes.c_size_t), ('c', ctypes.c_size_t), ('d', ctypes.c_size_t), ('PagefileUsage', ctypes.c_size_t), ('PeakPagefileUsage', ctypes.c_size_t)]
    _T0 = time.time()
    def _report():
        c = _PMC(); c.cb = ctypes.sizeof(_PMC); k = ctypes.windll.kernel32; k.GetCurrentProcess.restype = wt.HANDLE
        f_ = ctypes.windll.psapi.GetProcessMemoryInfo; f_.argtypes = [wt.HANDLE, ctypes.c_void_p, wt.DWORD]; ok = f_(k.GetCurrentProcess(), ctypes.byref(c), c.cb)
        with open(os.environ['V_PEAK_FILE'], 'a') as f:
            f.write(json.dumps(dict(argv=sys.argv[:3], ok=bool(ok), peak_ws_gb=round(c.PeakWorkingSetSize / 2**30, 2), peak_commit_gb=round(c.PeakPagefileUsage / 2**30, 2), sec=round(time.time() - _T0, 1))) + '\n')
    atexit.register(_report)
