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
  2. sorts the ink: ink_bins.py N -> unet_data/N_bins.png, N_bins.json;
  3. turns the rail the rules found into tracks for the line editor: rail_tracks.py N -> unet_data/N_rail_rule.json;
  4. block recognition (Ben, 21 November 2026: "the code should have run the block recognition too"): on a plate with no
     placement, blocks_noguide.py N -> unet_data/N_edges.json, the block lines the line editor shows. It needs the two
     networks trained with a blank guide (train_noguide.py, run once); until they are there this step is left out and
     the run says so. A plate that has a placement (a guide: 43, 44, 45, 80, 82A) keeps the lines it has.

Plates Ben has not cut (19 November 2026: "They are in the same path as the PNGs, but under /Sanborn/Maps as PDFs (the
full plates, not the cut ones that I use)"): a plate number with no PNG at all is taken from its PDF
(<folder beside New Sanborn>/Sanborn/Maps/Sanborn Cincinnati N.pdf, or --pdf DIR; also looked for in that folder's
TBD, where the PDFs of the plates not yet cut were moved the same day: "Move the pdfs that are outstanding to their own
folder 'TBD'"). The PDF holds one JPEG, 11,211 by
7,433 px at 300 to the inch, the same scan the PNGs were cut from (plate 44: the cut PNG sits at 367, 96 in it), and it
is copied out as it is, not drawn again. The paper is told from the dark scanner bed by its lightness. Such a plate is
the WHOLE sheet: margin, title, the printed KEY and any inset are on it, and its pixels are not those of a PNG cut from
it later (cufp/N/source.json says where the scan came from). A number Ben cut in two (8 -> 8A, 8B) is not taken again.
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
NETS = [os.path.join(DATA, 'unet_data', 'models', m + '.pt') for m in ('area_ng1', 'lines_ng1')]; VPY = os.path.join(HERE, '.venv', 'Scripts', 'python.exe')
STATE = os.path.join(DATA, 'unet_data', 'run_plates.json'); LOG = os.path.join(DATA, 'unet_data', 'run_plates.log')


def png_dir():
    cfg = json.load(open(os.path.join(REPO, 'configs', 'sanborn_paths.json'), encoding='utf8'))
    return os.path.normpath(os.path.join(cfg['new_sanborn'], 'PNG'))


def pdf_dir():
    if '--pdf' in sys.argv: return sys.argv[sys.argv.index('--pdf') + 1]
    return os.path.normpath(os.path.join(png_dir(), '..', '..', 'Sanborn', 'Maps'))


def plates(pdir):
    """every plate with a scan: {N: path of the raw PNG, or of the PDF for a plate that was never cut, or None where only
    the prepared scan is here}. 26a.png is plate 26A"""
    out = {}
    if os.path.isdir(pdir):
        for f in os.listdir(pdir):
            m = re.fullmatch(r'(\d+[A-Za-z]?)\.png', f)
            if m: out[m.group(1).upper()] = os.path.join(pdir, f)
    for f in os.listdir(os.path.join(DATA, 'cufp')):
        m = re.fullmatch(r'22-(\d+[A-Z]?)\.jpg', f)
        if m and os.path.exists(os.path.join(DATA, 'cufp', m.group(1), 'png_alpha_s4.npy')): out.setdefault(m.group(1), None)
    have = {re.match(r'\d+', n).group() for n in out}; qdir = pdf_dir()   # a number Ben cut (8 -> 8A, 8B) is not taken again whole
    for q in (qdir, os.path.join(qdir, 'TBD')):   # TBD: the plates Ben has not cut yet, which he had moved there (19 November 2026)
        if not os.path.isdir(q): continue
        for f in sorted(os.listdir(q)):
            m = re.fullmatch(r'Sanborn Cincinnati (\d+)\s*([A-Za-z]?)\.pdf', f, re.I)
            if m and m.group(1) not in have: out.setdefault(m.group(1) + m.group(2).upper(), os.path.join(q, f))
    return out


def order(n):
    m = re.match(r'(\d+)(.*)', n); return int(m.group(1)), m.group(2)


def prepare(n, png):
    """the scan as the rules read it. Done once; a prepared plate is left as it is"""
    jpg = os.path.join(DATA, 'cufp', f'22-{n}.jpg'); d = os.path.join(DATA, 'cufp', n); alpha = os.path.join(d, 'png_alpha_s4.npy')
    if os.path.exists(jpg) and os.path.exists(alpha): return 'was ready'
    if png is None: raise RuntimeError('no raw PNG for this plate')
    import cv2, numpy as np
    if png.lower().endswith('.pdf'):   # an uncut plate: the scan is the one JPEG inside the PDF, copied out as it is
        import fitz
        doc = fitz.open(png); ims = doc[0].get_images(full=True)
        if len(doc) != 1 or len(ims) != 1: raise RuntimeError(f'expected one page with one picture, found {len(doc)} pages, {len(ims)} pictures')
        x = doc.extract_image(ims[0][0]); a = cv2.imdecode(np.frombuffer(x['image'], np.uint8), cv2.IMREAD_COLOR)
        if a is None or x['ext'] not in ('jpeg', 'jpg'): raise RuntimeError(f'the picture in the PDF is {x["ext"]}, not a JPEG')
        # the paper: the light sheet against the dark scanner bed. Lightness at quarter size, the largest light piece,
        # its holes filled (a dark building or a river is still paper), 4 px in from its edge
        g = cv2.GaussianBlur(cv2.cvtColor(a[::4, ::4], cv2.COLOR_BGR2LAB)[..., 0], (0, 0), 3); t, m = cv2.threshold(g, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        cs = cv2.findContours(m, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)[0]; c = max(cs, key=cv2.contourArea); m = np.zeros_like(m); cv2.drawContours(m, [c], -1, 1, -1)
        m = cv2.erode(m, np.ones((9, 9), np.uint8)); share = float(m.mean())
        if not 0.5 <= share <= 0.99: raise RuntimeError(f'the paper was not told from the scanner bed (paper {100 * share:.0f}% of the scan)')
        os.makedirs(d, exist_ok=True)
        if not os.path.exists(jpg):
            open(jpg + '.tmp.jpg', 'wb').write(x['image']); os.replace(jpg + '.tmp.jpg', jpg)
        np.save(alpha + '.tmp.npy', m.astype(np.uint8)); os.replace(alpha + '.tmp.npy', alpha)
        json.dump(dict(plate=n, source='pdf', file=png.replace('\\', '/'), size=[a.shape[1], a.shape[0]], paper_share=round(share, 3), note='the whole uncut sheet: margin, title, key and insets are on it; its pixels are not those of a PNG cut from it later'), open(os.path.join(d, 'source.json'), 'w', encoding='utf8', newline='\n'), indent=1)
        return f'from the PDF {a.shape[1]} x {a.shape[0]}, paper {100 * share:.0f}%'
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
    pdir = png_dir(); P = plates(pdir); rules = hashlib.sha256(open(INK, 'rb').read()).hexdigest()[:12]; npdf = sum(1 for n, v in P.items() if (v and v.lower().endswith('.pdf')) or os.path.exists(os.path.join(DATA, 'cufp', n, 'source.json')))   # source.json: an uncut plate already prepared
    want = sorted((a.upper() for a in args), key=order) if args else sorted(P, key=order)
    state = json.load(open(STATE, encoding='utf8')) if os.path.exists(STATE) else {}
    nets = all(os.path.exists(f) for f in NETS) and os.path.exists(NETS[1][:-3] + '.done') and os.path.exists(VPY); netid = '+'.join(str(int(os.path.getmtime(f))) for f in NETS) if nets else ''; todo = []
    for n in want:
        s = state.get(n, {}); done = s.get('state') == 'done' and s.get('rules') == rules and os.path.exists(os.path.join(DATA, 'unet_data', f'{n}_bins.png'))
        if n not in P: print(f'plate {n}: no scan found in {pdir}'); continue
        if done and nets and s.get('blocks_nets') != netid: done = False   # sorted before the block networks were there (or they were trained again)
        if done and not redo: continue
        todo.append(n)
    print(f'{len(P)} plates have a scan: {len(P) - npdf} cut ({pdir}), {npdf} uncut from PDF ({pdf_dir()}). Asked for {len(want)}; already done with these rules {len(want) - len(todo) - sum(n not in P for n in want)}; to run {len(todo)}: {" ".join(todo)}')
    print('block recognition: ' + ('on (the blank-guide networks are trained)' if nets else 'LEFT OUT: the blank-guide networks are not trained yet; run  python tools\\sanborn\\unet\\train_noguide.py  once, then this again'))
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
            r = subprocess.run([sys.executable, os.path.join(HERE, 'rail_tracks.py'), n], cwd=DATA, capture_output=True, text=True, encoding='utf8', errors='replace')
            with open(LOG, 'a', encoding='utf8', newline='\n') as f: f.write(r.stdout + r.stderr + '\n')
            if r.returncode: raise RuntimeError('tracks: ' + (r.stderr.strip().splitlines() or ['rail_tracks.py failed'])[-1])
            if nets:
                r = subprocess.run([VPY, '-W', 'ignore', os.path.join(HERE, 'blocks_noguide.py'), n], cwd=DATA, capture_output=True, text=True, encoding='utf8', errors='replace')
                with open(LOG, 'a', encoding='utf8', newline='\n') as f: f.write(r.stdout + r.stderr + '\n')
                if r.returncode: raise RuntimeError('blocks: ' + ((r.stdout + r.stderr).strip().splitlines() or ['blocks_noguide.py failed'])[-1])
                rec.update(blocks_nets=netid, blocks=(r.stdout.strip().splitlines() or [''])[-1].partition('|')[2].strip())
            rec.update(state='done', ink_px=b['ink_px'], railroad_px=px.get('railroad', 0), streetcar_px=px.get('streetcar', 0), note=b.get('note', ''), ben_rail=bool(b.get('ben_rail')))
        except KeyboardInterrupt:
            print('\nstopped. Start it again to carry on from this plate.'); return
        except Exception as e:
            rec['error'] = f'{type(e).__name__}: {e}'; bad.append(n)
        rec['seconds'] = round(time.time() - t0)
        state[n] = rec; json.dump(state, open(STATE + '.tmp', 'w', encoding='utf8', newline='\n'), indent=1); os.replace(STATE + '.tmp', STATE)
        left = (time.time() - t_all) / (k + 1) * (len(todo) - k - 1)
        print(f'[{k + 1}/{len(todo)}] plate {n:4s} ' + (f'done in {rec["seconds"]} s: railroad {rec["railroad_px"]} px, streetcar {rec["streetcar_px"]} px' + (f' | blocks: {rec["blocks"]}' if rec.get('blocks') else '') if rec['state'] == 'done' else f'FAILED: {rec["error"]}') + f' | about {left / 60:.0f} min left', flush=True)
    print(f'finished {len(todo) - len(bad)} of {len(todo)} in {(time.time() - t_all) / 60:.0f} min' + (f'; failed: {" ".join(bad)} (see {LOG})' if bad else '') + f'. Results: {STATE}')


if __name__ == '__main__':
    main()
