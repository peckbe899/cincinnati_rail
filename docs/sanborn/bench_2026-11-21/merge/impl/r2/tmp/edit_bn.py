import sys
p = sys.argv[1]; s = open(p, encoding='utf8', newline='').read()
R = [
("""    cd data/sanborn
    ../../tools/sanborn/unet/.venv/Scripts/python.exe ../../tools/sanborn/unet/blocks_noguide.py N [N ...] [--pred-only] [--outlines-only] [--out DIR]
""",
 """    cd data/sanborn
    ../../tools/sanborn/unet/.venv/Scripts/python.exe ../../tools/sanborn/unet/blocks_noguide.py N [N ...] [--pred-only] [--outlines-only] [--out DIR]
(an option it does not know stops it: a slip such as --outline-only would otherwise run the networks again)
"""),
("""- Ben's edits (picks22_guided/22-N/edges_ben.json) are keyed to the lines of unet_data/N_edges.json (their a0, b0): a
  new N_edges.json leaves every edit of his hanging. So on a plate with edges_ben.json, N_edges.json is never written
  again; the new lines go to unet_data/N_edges.new.json, and the run says so.
- outline_version(): a short hash of outlines.py, blocks_noguide.py and map_area.py, the outline step's version
  (outlines.py writes it into N_outlines.json, run_plates.py keeps it per plate and redoes the step where it changed).
\"\"\"""",
 """- Ben's edits (picks22_guided/22-N/edges_ben.json) are keyed to the lines of unet_data/N_edges.json (their a0, b0): a
  new N_edges.json leaves every edit of his hanging, and the ink sorting reads those lines with the outlines that made
  them (picks22_guided/22-N/outlines.json, N_outlines.json, N_mapground.png). So on a plate with edges_ben.json and an
  N_edges.json, steps 3 and 4 write everything into unet_data/N_new/ (outlines.json, N_outlines.json, N_edges.json,
  N_blocks_ng.json, ...) and leave the plate's own files as they are; the run says so. (Where there is no N_edges.json
  yet, his edits can only be lines he drew or sheet-edge lines, keyed to nothing of this step: the lines are written.)
- outline_version(): a short hash of what the outline step runs (VERSION_FILES: outlines.py, blocks_noguide.py,
  map_area.py and its templates, ink_bins.py, whose railroad rule and block ground the step uses). outlines.py writes
  it into N_outlines.json, run_plates.py keeps it per plate and redoes the step where it changed.
\"\"\""""),
("""import hashlib, json, os, subprocess, sys, time
""", """import argparse, hashlib, json, os, subprocess, sys, time
"""),
("""VERSION_FILES = ('outlines.py', 'blocks_noguide.py', 'map_area.py')


def outline_version():
    \"\"\"the outline step's version: a short hash of outlines.py, blocks_noguide.py and map_area.py\"\"\"
    h = hashlib.sha256()
    for f in VERSION_FILES:
        p = os.path.join(HERE, f)
        h.update(f.encode() + b'\\0' + (open(p, 'rb').read() if os.path.exists(p) else b'missing') + b'\\0')
    return h.hexdigest()[:12]
""",
 """VERSION_FILES = ('outlines.py', 'blocks_noguide.py', 'map_area.py', 'ink_bins.py') + tuple(f'templates/{k}.png' for k in ('key', 'title', 'bar200', 'bar400', 'bar400b', 'note200a', 'note200b', 'note400a', 'rose'))


def outline_version():
    \"\"\"the outline step's version: a short hash of the files in VERSION_FILES (a missing one counts as 'missing')\"\"\"
    h = hashlib.sha256()
    for f in VERSION_FILES:
        p = os.path.join(HERE, f)
        h.update(f.encode() + b'\\0' + (open(p, 'rb').read() if os.path.exists(p) else b'missing') + b'\\0')
    return h.hexdigest()[:12]


def protected(N):
    \"\"\"Ben has edited plate N's lines: his edges_ben.json is keyed to its N_edges.json, which must then stay as it is\"\"\"
    return os.path.exists(SP + f'picks22_guided/22-{N}/edges_ben.json') and os.path.exists(U + f'{N}_edges.json')
"""),
("""def run(N, nets, pred_only, outlines_only=False, out=None):
    t0 = time.time(); odir = (os.path.abspath(out).replace('\\\\', '/') + '/') if out else U
    if out: os.makedirs(odir, exist_ok=True)
    if outlines_only:
        maps = [odir + f'{N}_pred_{AREA}.png', odir + f'{N}_lines_{LINES}.png']
        if out and not all(os.path.exists(m) for m in maps): maps = [U + f'{N}_pred_{AREA}.png', U + f'{N}_lines_{LINES}.png']   # --out: the saved maps of the plate
        if not all(os.path.exists(m) for m in maps): raise RuntimeError(f'--outlines-only: no saved maps ({", ".join(os.path.basename(m) for m in maps)}); run the networks first')
        pa = cv2.imread(maps[0], 0); msg = f'plate {N:4s} block share {float((pa > 127).mean()):.2f}, maps as saved'; del pa
    else:
        msg = predict(N, nets, odir); maps = [odir + f'{N}_pred_{AREA}.png', odir + f'{N}_lines_{LINES}.png']
    if pred_only: print(msg, f'| {time.time() - t0:.0f} s', flush=True); return
    if os.path.exists(U + f'{N}_guide.png'): print(msg, '| has a guide: outlines and lines left as they are', flush=True); return
    cmd = [sys.executable, os.path.join(HERE, 'outlines.py'), N, AREA, LINES]
    if out: cmd += ['--out', odir, '--area-png', maps[0], '--lines-png', maps[1]]
    r = subprocess.run(cmd, cwd=SP, capture_output=True, text=True, encoding='utf8', errors='replace')
    if r.returncode: raise RuntimeError('outlines: ' + ((r.stderr + r.stdout).strip().splitlines() or ['failed'])[-1])
    rep = json.loads(r.stdout.strip().splitlines()[-1])
    out_e = step4(json.load(open((odir + 'outlines.json') if out else SP + f'picks22_guided/22-{N}/outlines.json', encoding='utf8')))
    ef = odir + f'{N}_edges.json'; note = ''
    if not out and os.path.exists(SP + f'picks22_guided/22-{N}/edges_ben.json'):
        # Ben's edits are keyed to the lines of N_edges.json: a new N_edges.json would leave them hanging
        ef = U + f'{N}_edges.new.json'; note = f' | Ben has edited this plate\\'s lines (picks22_guided/22-{N}/edges_ben.json, keyed to unet_data/{N}_edges.json): N_edges.json left as it is, the new lines are in {N}_edges.new.json'
    json.dump(out_e, open(ef + '.tmp', 'w', encoding='utf8', newline='\\n')); os.replace(ef + '.tmp', ef)""",
 """def run(N, nets, pred_only, outlines_only=False, out=None):
    t0 = time.time(); odir = (os.path.abspath(out).replace('\\\\', '/') + '/') if out else U
    if out: os.makedirs(odir, exist_ok=True)
    if outlines_only:
        maps = [odir + f'{N}_pred_{AREA}.png', odir + f'{N}_lines_{LINES}.png']
        if out and not all(os.path.exists(m) for m in maps): maps = [U + f'{N}_pred_{AREA}.png', U + f'{N}_lines_{LINES}.png']   # --out: the saved maps of the plate
        if not all(os.path.exists(m) for m in maps): raise RuntimeError(f'--outlines-only: no saved maps ({", ".join(os.path.basename(m) for m in maps)}); run the networks first')
        pa = cv2.imread(maps[0], 0); msg = f'plate {N:4s} block share {float((pa > 127).mean()):.2f}, maps as saved'; del pa
    else:
        msg = predict(N, nets, odir); maps = [odir + f'{N}_pred_{AREA}.png', odir + f'{N}_lines_{LINES}.png']
    if pred_only: print(msg, f'| {time.time() - t0:.0f} s', flush=True); return
    if os.path.exists(U + f'{N}_guide.png'): print(msg, '| has a guide: outlines and lines left as they are', flush=True); return
    note = ''
    if not out and protected(N):   # Ben's edits are keyed to N_edges.json's lines: steps 3 and 4 go to unet_data/N_new/, the plate's own files stay
        odir = U + f'{N}_new/'; os.makedirs(odir, exist_ok=True)
        note = (f" | Ben has edited this plate's lines (picks22_guided/22-{N}/edges_ben.json, keyed to unet_data/{N}_edges.json): its outlines and lines are left as they are;"
                f" the new ones are in unet_data/{N}_new/")
    cmd = [sys.executable, os.path.join(HERE, 'outlines.py'), N, AREA, LINES]
    if odir != U: cmd += ['--out', odir, '--area-png', maps[0], '--lines-png', maps[1]]
    r = subprocess.run(cmd, cwd=SP, capture_output=True, text=True, encoding='utf8', errors='replace')
    if r.returncode: raise RuntimeError('outlines: ' + ((r.stderr + r.stdout).strip().splitlines() or ['failed'])[-1])
    rep = json.loads(r.stdout.strip().splitlines()[-1])
    out_e = step4(json.load(open((odir + 'outlines.json') if odir != U else SP + f'picks22_guided/22-{N}/outlines.json', encoding='utf8')))
    ef = odir + f'{N}_edges.json'
    json.dump(out_e, open(ef + '.tmp', 'w', encoding='utf8', newline='\\n')); os.replace(ef + '.tmp', ef)"""),
("""                   edges_file=os.path.basename(ef), keep_unlined=KEEP_UNLINED""", """                   edges_file=ef[len(SP):] if ef.startswith(SP) else ef, keep_unlined=KEEP_UNLINED"""),
("""if __name__ == '__main__':
    pl = [a for a in sys.argv[1:] if not a.startswith('--')]; out = None
    if '--out' in sys.argv: out = sys.argv[sys.argv.index('--out') + 1]; pl.remove(out)
    only = '--outlines-only' in sys.argv; nets = None
    if not only:""",
 """if __name__ == '__main__':
    ap = argparse.ArgumentParser(description='block recognition on plates never placed (see the docstring)', allow_abbrev=False)
    ap.add_argument('plates', nargs='+', metavar='N'); ap.add_argument('--pred-only', action='store_true', help='stop after the two networks')
    ap.add_argument('--outlines-only', action='store_true', help='steps 3 and 4 only, on the saved maps'); ap.add_argument('--out', help='write every output here, nothing into the repo')
    A_ = ap.parse_args()   # an option it does not know is an error (exit 2), never ignored
    pl = [n.upper() for n in A_.plates]; out = A_.out; only = A_.outlines_only; nets = None
    if not only:"""),
("""    for n in pl:
        try: run(n, nets, '--pred-only' in sys.argv, only, out)""",
 """    for n in pl:
        try: run(n, nets, A_.pred_only, only, out)"""),
]
for a, b in R:
    assert s.count(a) == 1, a[:120]
    s = s.replace(a, b)
open(p, 'w', encoding='utf8', newline='').write(s)
print('ok')
