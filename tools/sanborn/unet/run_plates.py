"""Run the ink sorting (ink_bins.py, with the rail rules) on many 1922 plates, by itself (19 November 2026).

Ben, 19 November 2026: "if there are more than 80 plates, we should run them on a good percentage of the plates,
checked manually, and retrained with a powerful enough ML U-net. can you set up a program to run in powershell (not
here), I will have them run, let you know when they're done".

From the repo folder, in PowerShell:

    python tools\\sanborn\\unet\\run_plates.py                 every plate that has a scan
    python tools\\sanborn\\unet\\run_plates.py 43 45 80        only these plates
    python tools\\sanborn\\unet\\run_plates.py --list          say what would be run, and run nothing
    python tools\\sanborn\\unet\\run_plates.py --redo          run again the plates already done with today's rules

For each plate N it
  1. prepares the scan, if that was not done before: the raw PNG (New Sanborn/PNG/N.png, configs/sanborn_paths.json)
     -> cufp/22-N.jpg (full size) and cufp/N/png_alpha_s4.npy (where the paper is), as cufp/prep.py does;
  2. sorts the ink: ink_bins.py N -> unet_data/N_bins.png, N_bins.json.
A plate takes about a minute. Each plate runs as its own process, so one that fails does not stop the rest; the run can
be stopped (Ctrl+C) and started again, and picks up where it stopped. A plate already sorted with the same rules (the
same ink_bins.py) is skipped.

What it does NOT do: it never touches the lines or tracks Ben drew (edges_ben.json, rail_ben.json; where he drew tracks,
ink_bins.py uses them, as the line editor's own button does), it trains nothing, and it makes no street lines. Only
plate 44 has a street map, so on every other plate only the rail bins (railroad, streetcar) are worth checking.

Progress is printed and kept in unet_data/run_plates.json (plate, state, seconds, railroad and streetcar px, the error
if any) and unet_data/run_plates.log (everything ink_bins.py printed).
"""
import hashlib, json, os, re, subprocess, sys, time

HERE = os.path.dirname(os.path.abspath(__file__)); REPO = os.path.normpath(os.path.join(HERE, '..', '..', '..'))
DATA = os.path.join(REPO, 'data', 'sanborn'); INK = os.path.join(HERE, 'ink_bins.py')
STATE = os.path.join(DATA, 'unet_data', 'run_plates.json'); LOG = os.path.join(DATA, 'unet_data', 'run_plates.log')


def png_dir():
    cfg = json.load(open(os.path.join(REPO, 'configs', 'sanborn_paths.json'), encoding='utf8'))
    return os.path.normpath(os.path.join(cfg['new_sanborn'], 'PNG'))


def plates(pdir):
    """every plate with a scan: {N: path of the raw PNG, or None where only the prepared scan is here}. 26a.png is plate 26A"""
    out = {}
    if os.path.isdir(pdir):
        for f in os.listdir(pdir):
            m = re.fullmatch(r'(\d+[A-Za-z]?)\.png', f)
            if m: out[m.group(1).upper()] = os.path.join(pdir, f)
    for f in os.listdir(os.path.join(DATA, 'cufp')):
        m = re.fullmatch(r'22-(\d+[A-Z]?)\.jpg', f)
        if m and os.path.exists(os.path.join(DATA, 'cufp', m.group(1), 'png_alpha_s4.npy')): out.setdefault(m.group(1), None)
    return out


def order(n):
    m = re.match(r'(\d+)(.*)', n); return int(m.group(1)), m.group(2)


def prepare(n, png):
    """the scan as the rules read it. Done once; a prepared plate is left as it is"""
    jpg = os.path.join(DATA, 'cufp', f'22-{n}.jpg'); d = os.path.join(DATA, 'cufp', n); alpha = os.path.join(d, 'png_alpha_s4.npy')
    if os.path.exists(jpg) and os.path.exists(alpha): return 'was ready'
    if png is None: raise RuntimeError('no raw PNG for this plate')
    import cv2, numpy as np
    from PIL import Image
    Image.MAX_IMAGE_PIXELS = None
    im = np.array(Image.open(png).convert('RGBA')); a = im[:, :, 3]; rgb = im[:, :, :3].copy(); rgb[a == 0] = 255
    os.makedirs(d, exist_ok=True)
    if not os.path.exists(jpg):
        cv2.imwrite(jpg + '.tmp.jpg', rgb[:, :, ::-1], [cv2.IMWRITE_JPEG_QUALITY, 88]); os.replace(jpg + '.tmp.jpg', jpg)
    if not os.path.exists(alpha):
        np.save(alpha + '.tmp.npy', (a[::4, ::4] > 0).astype(np.uint8)); os.replace(alpha + '.tmp.npy', alpha)
    return f'prepared {im.shape[1]} x {im.shape[0]}'


def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]; redo = '--redo' in sys.argv; only_list = '--list' in sys.argv
    pdir = png_dir(); P = plates(pdir); rules = hashlib.sha256(open(INK, 'rb').read()).hexdigest()[:12]
    want = sorted((a.upper() for a in args), key=order) if args else sorted(P, key=order)
    state = json.load(open(STATE, encoding='utf8')) if os.path.exists(STATE) else {}
    todo = []
    for n in want:
        s = state.get(n, {}); done = s.get('state') == 'done' and s.get('rules') == rules and os.path.exists(os.path.join(DATA, 'unet_data', f'{n}_bins.png'))
        if n not in P: print(f'plate {n}: no scan found in {pdir}'); continue
        if done and not redo: continue
        todo.append(n)
    print(f'{len(P)} plates have a scan ({pdir}). Asked for {len(want)}; already done with these rules {len(want) - len(todo) - sum(n not in P for n in want)}; to run {len(todo)}: {" ".join(todo)}')
    if only_list or not todo: return
    os.makedirs(os.path.dirname(STATE), exist_ok=True); t_all = time.time(); bad = []
    for k, n in enumerate(todo):
        t0 = time.time(); rec = dict(state='failed', rules=rules, when=time.strftime('%Y-%m-%d %H:%M:%S'))
        try:
            rec['scan'] = prepare(n, P[n])
            r = subprocess.run([sys.executable, INK, n], cwd=DATA, capture_output=True, text=True, encoding='utf8', errors='replace')
            with open(LOG, 'a', encoding='utf8', newline='\n') as f: f.write(f'===== plate {n} {rec["when"]} rules {rules} exit {r.returncode}\n{r.stdout}\n{r.stderr}\n')
            if r.returncode: raise RuntimeError((r.stderr.strip().splitlines() or ['ink_bins.py failed'])[-1])
            b = json.load(open(os.path.join(DATA, 'unet_data', f'{n}_bins.json'), encoding='utf8'))
            px = {v['name']: v['px'] for v in b['bins'].values()}
            rec.update(state='done', ink_px=b['ink_px'], railroad_px=px.get('railroad', 0), streetcar_px=px.get('streetcar', 0), note=b.get('note', ''), ben_rail=bool(b.get('ben_rail')))
        except KeyboardInterrupt:
            print('\nstopped. Start it again to carry on from this plate.'); return
        except Exception as e:
            rec['error'] = f'{type(e).__name__}: {e}'; bad.append(n)
        rec['seconds'] = round(time.time() - t0)
        state[n] = rec; json.dump(state, open(STATE + '.tmp', 'w', encoding='utf8', newline='\n'), indent=1); os.replace(STATE + '.tmp', STATE)
        left = (time.time() - t_all) / (k + 1) * (len(todo) - k - 1)
        print(f'[{k + 1}/{len(todo)}] plate {n:4s} ' + (f'done in {rec["seconds"]} s: railroad {rec["railroad_px"]} px, streetcar {rec["streetcar_px"]} px' if rec['state'] == 'done' else f'FAILED: {rec["error"]}') + f' | about {left / 60:.0f} min left', flush=True)
    print(f'finished {len(todo) - len(bad)} of {len(todo)} in {(time.time() - t_all) / 60:.0f} min' + (f'; failed: {" ".join(bad)} (see {LOG})' if bad else '') + f'. Results: {STATE}')


if __name__ == '__main__':
    main()
