"""merge/impl: the staged run_plates.py --list against the real repo data, writing nothing (21 Nov 2026).

The staged run_plates.py finds its data from where it lies (REPO = its folder/../../..), which in merge/staged is not the
repo. So it is imported as a module and pointed at the repo's data/sanborn (read only), with HERE left as the staged
folder: the outline version and the rules hash are those of the STAGED files (rail_tracks.py is not staged, so the
repo's is hashed). --list only reads: run_plates.json, the scans, the maps and the files bins_from() hashes.
    python -B dryrun_run_plates.py [N ...]      -> prints the plan per plate; merge/impl/dryrun_run_plates.txt
Checked after: no file under data/sanborn/unet_data, picks22_guided, streetmap or cufp is newer than the run's start.
"""
import io, os, sys, time, contextlib
import common as C
C.step4_mod()                       # the shim _ws first, then the staged folder on the path
import importlib.util
spec = importlib.util.spec_from_file_location('run_plates_staged', C.SU + 'run_plates.py'); RP = importlib.util.module_from_spec(spec); spec.loader.exec_module(RP)
assert os.path.abspath(RP.HERE).replace('\\', '/').rstrip('/') == C.SU.rstrip('/')
RP.REPO = os.path.normpath(C.REPO); RP.DATA = os.path.normpath(C.DATA)
RP.NETS = [os.path.join(RP.DATA, 'unet_data', 'models', m + '.pt') for m in ('area_ng1', 'lines_ng1')]; RP.VPY = C.VPY
RP.STATE = os.path.join(RP.DATA, 'unet_data', 'run_plates.json'); RP.LOG = os.devnull     # --list never writes; the log is pointed at nothing anyway
RP.RULES = (C.SU + 'ink_bins.py', C.SU + 'street_map.py', C.RU + '/rail_tracks.py')
t0 = time.time(); sys.argv = ['run_plates.py', '--list'] + sys.argv[1:]
buf = io.StringIO()
with contextlib.redirect_stdout(buf): RP.main()
txt = buf.getvalue(); print(txt); open(C.IMPL + 'dryrun_run_plates.txt', 'w', encoding='utf8').write(txt)
newer = [os.path.join(dp, f) for d in ('unet_data', 'picks22_guided', 'streetmap', 'cufp') for dp, _, fs in os.walk(C.DATA + d) for f in fs if os.path.getmtime(os.path.join(dp, f)) >= t0 - 1]
print('files written during the dry run under unet_data, picks22_guided, streetmap, cufp:', newer or 'none')
