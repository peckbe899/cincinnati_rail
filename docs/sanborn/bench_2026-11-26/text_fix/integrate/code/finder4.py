"""finder4 (integrate, 26 Nov 2026): finder3, then the ditto fix, then the two block-number fixes put together.
Frozen after the checks: ../FROZEN.txt holds the sha256 of this file and of every file it imports or loads.

    cd data/sanborn
    python -B bench_2026-11-26/text_fix/integrate/code/finder4.py N [--win X0 Y0 X1 Y1] --out DIR

Writes DIR/N_text.png, one code per pixel as finder2 and finder3: 0 paper, 1 line ink, 2 text sure, 3 text by context,
4 shared ink where a glyph touches a line, 5 other ink (text for scoring = codes 2 and 3); DIR/N_text.json (pixel counts,
settings, timings, and every change of each step: the ditto marks taken, A's figure words, B's numbers); DIR/N_blocks.json
(the block numbers step B reads: reading, box, scores, flags from checks by code, and the chains it refused).
Reads only the scan cufp/22-N.jpg, its paper mask cufp/N/png_alpha_s4.npy, scale_table.json, finder3's weights
(text_v1/classifier/out) and the block models in ../models. No truth, no street map, no rail file, no line file.

Steps (each step only recodes ink; the ink, codes > 0, never changes: asserted):
  1. finder3: text_v1/code/finder3.py, imported read-only and unchanged (it imports finder2.py and the classifier).
  2. DITTO MARKS: dittofix.py, a byte-identical copy of fix_ditto/code/dittofix.py. Small marks of free ink (1-4 pieces)
     that pass its dash tests and stand in a row of like marks, beside a figure (200 ft) or as a strong pair, go 5 -> 3.
  3. BLOCK NUMBERS: both fixes run on step 2's codes and are put together pixel by pixel ('Upix'):
       B  blockfix_b.py, a byte-identical copy of fix_block_b/code/blockfix.py, with the final models (../models:
          tmpl_real_all.npz, cls_all.npz, num_all.npz, copies of fix_block_b/models). It finds figures with digit models
          and a small net, reads numbers (N_blocks.json), and gives each recognised figure's ink to text (code 2); line
          cores carried through a figure keep their code.
       A  blockfix_a.py, a byte-identical copy of fix_block_a/code/blockfix.py. Geometry: it groups the bold pieces of
          the ink into rows of figures, fits the lines that cross them, takes out only those lines, and gives the rest of
          the figure ink to text (2; 4 where it touches line ink), for groups that finder3 already calls a quarter or
          more text (or bold upright figures standing free).
     Result: B's codes, plus A's changes at every pixel that B left alone. Neither fix takes text away.
  blockfix_b refuses sealed plates by itself; finder4 has its own guard (run(): sealed plates only with --sealed-ok, which
  is for the final gate alone) and lifts blockfix_b's guard for that one call.

Why this set-up (dev numbers, MEASURED; the full tables and the report are in ../scores and the report):
  - Block step, dev block truth (45 crops; B with cross-fold models): block-number pixel recall finder3 0.792 (38/45 words),
    A 0.891 (41/45), B 0.850 (41/45), both put together 0.909 (43/45); fold A 0.748 -> 0.882, fold B 0.847 -> 0.942.
    B then A in sequence (0.912) and A then B (0.912) score about the same, but B then A calls more of Ben's line ink
    text on plate 5 (0.484% within 3 px against 0.459%), and 'Upix' lets each fix see the codes it was built on.
    Gating A by B (A only where B reads a number) loses most of A's right changes (street and owner letters).
  - Order: ditto first or block first give the same score on every truth set; on 21 whole dev plates they differ in
    144 px at 5 marks, 3 of them dittos found only when the ditto step runs first on the finder3 codes it was built on.
Options (dev only): run(s={'block': mode, 'order': ...}) with mode none, A, B, BA, AB, Ubox, Upix, Gbox, Gpix (combine()),
order 'ditto_then_block' (default) or 'block_then_ditto'; --finder3-mask PATH starts from finder3's stored codes.
"""
import json, os, sys, time
sys.dont_write_bytecode = True
import numpy as np, cv2

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
TV1 = os.path.normpath(os.path.join(HERE, '..', '..', '..', '..', 'bench_2026-11-25', 'text_v1', 'code'))
sys.path.insert(0, TV1)
import finder3  # noqa: E402  (text_v1/code/finder3.py, read-only; it imports finder2.py and the classifier scripts)
import blockfix_a as BA  # noqa: E402  (byte-identical copy of fix_block_a/code/blockfix.py)
import blockfix_b as BB  # noqa: E402  (byte-identical copy of fix_block_b/code/blockfix.py)
import dittofix as DF  # noqa: E402  (byte-identical copy of fix_ditto/code/dittofix.py)

MOD = os.path.normpath(os.path.join(HERE, '..', 'models'))
SEALED = {'6', '9', '52', '56', '58', '63', '35', '38', '41', '66', '71', '76', '84', '88', '46', '92'}
S4 = dict(block='Upix', order='ditto_then_block', pad=8,
          b_tmpl=os.path.join(MOD, 'tmpl_real_all.npz'), b_model=os.path.join(MOD, 'cls_all.npz'), b_num=os.path.join(MOD, 'num_all.npz'))
BLOCK_MODES = ('none', 'A', 'B', 'BA', 'AB', 'Ubox', 'Upix', 'Gbox', 'Gpix')


def grown_box(b, pad, H, W):
    x0, y0, x1, y1 = (int(round(v)) for v in b[:4])
    return max(0, x0 - pad), max(0, y0 - pad), min(W, x1 + pad + 1), min(H, y1 + pad + 1)


def overlaps(a, b): return a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]


def combine(f3, outA, infoA, outB, infoB, mode, pad=8):
    """put A's and B's block changes together (both made on the same input codes f3). Modes:
    Upix  B's codes, plus A's changes at pixels B left alone (finder4's setting)
    Ubox  B's codes inside every number B reads (its box grown pad px), A's codes elsewhere
    Gbox  B's codes, plus A's changes only in A's figure words that overlap a number B reads, outside B's boxes
    Gpix  B's codes, plus A's changes in those words at pixels B left alone
    Returns codes and a short record."""
    H, W = f3.shape; dA = outA != f3; dB = outB != f3
    bb = [grown_box(c['box'], pad, H, W) for c in infoB['changes']]
    bmask = np.zeros(f3.shape, bool)
    for x0, y0, x1, y1 in bb: bmask[y0:y1, x0:x1] = True
    rec = dict(mode=mode, b_numbers=len(bb), a_px=int(dA.sum()), b_px=int(dB.sum()), both_px=int((dA & dB).sum()))
    if mode == 'Ubox':
        out = outA.copy(); out[bmask] = outB[bmask]
    elif mode == 'Upix':
        out = outB.copy(); m = dA & ~dB; out[m] = outA[m]; rec['a_px_added'] = int(m.sum())
    elif mode in ('Gbox', 'Gpix'):
        gmask = np.zeros(f3.shape, bool); kept = dropped = 0
        for c in infoA['changes']:
            g = grown_box(c['box'], pad, H, W)
            if any(overlaps(g, b) for b in bb): gmask[g[1]:g[3], g[0]:g[2]] = True; kept += 1
            else: dropped += 1
        m = dA & gmask & (~bmask if mode == 'Gbox' else ~dB)
        out = outB.copy(); out[m] = outA[m]; rec.update(a_words_kept=kept, a_words_dropped=dropped)
    else: raise ValueError(mode)
    rec['px_changed'] = int((out != f3).sum())
    return out, rec


def block_step(N, codes, ft, mode, s=S4):
    """the block-number step. Returns (codes, record, blocks or None)"""
    T = {}; rec = dict(mode=mode); blocks = None
    if mode == 'none': return codes, rec, None

    def run_a(src):
        t0 = time.time(); o, inf = BA.apply(N, src, None, ft, return_info=True); T['A'] = round(time.time() - t0, 1); return o, inf

    def run_b(src):
        t0 = time.time(); keep = BB.SEALED
        try:
            BB.SEALED = set()   # the sealed-plate guard is finder4's own (run()); blockfix_b's copy is not edited
            o, inf, nums, rej = BB.apply(N, src, None, ft, tmpl=s['b_tmpl'], model=s['b_model'], return_info=True, num_model=s['b_num'])
        finally: BB.SEALED = keep
        T['B'] = round(time.time() - t0, 1)
        return o, inf, dict(plate=str(N), scale_ft=ft, model=inf['model'], numbers=nums, rejected=rej)

    if mode == 'A': out, iA = run_a(codes); rec['A'] = slim_a(iA)
    elif mode == 'B': out, iB, blocks = run_b(codes); rec['B'] = slim_b(iB)
    elif mode == 'BA': o1, iB, blocks = run_b(codes); out, iA = run_a(o1); rec['B'] = slim_b(iB); rec['A'] = slim_a(iA)
    elif mode == 'AB': o1, iA = run_a(codes); out, iB, blocks = run_b(o1); rec['A'] = slim_a(iA); rec['B'] = slim_b(iB)
    elif mode in ('Ubox', 'Upix', 'Gbox', 'Gpix'):
        oA, iA = run_a(codes); oB, iB, blocks = run_b(codes)
        out, cr = combine(codes, oA, iA, oB, iB, mode, s['pad']); rec.update(A=slim_a(iA), B=slim_b(iB), combine=cr)
    else: raise ValueError(mode)
    rec['seconds'] = T
    return out, rec, blocks


def slim_a(i): return {k: i[k] for k in ('rough_words', 'why', 'changed_words', 'px_to_text', 'px_to_shared', 'seconds', 'changes') if k in i}


def slim_b(i): return {k: i[k] for k in ('peaks', 'proposals', 'figures', 'numbers', 'rejected', 'px_to_text', 'px_to_shared', 'seconds', 'changes', 'tmpl', 'model') if k in i}


def ditto_step(N, codes, gray, paper, ft):
    rep = {}; t0 = time.time(); out = DF.apply(N, codes, gray, ft, paper=paper, report=rep); rep['seconds_total'] = round(time.time() - t0, 1)
    return out, rep


def run(N, win=None, out=None, f3_codes=None, s=None, verbose=True, sealed_ok=False):
    """finder4 on plate N (or a window). f3_codes: finder3's codes made before (dev only); otherwise finder3 runs here."""
    s = dict(S4, **(s or {})); N = str(N)
    if N in SEALED and not sealed_ok: raise SystemExit(f'plate {N} is sealed (only the final gate runs it, with --sealed-ok)')
    t0 = time.time(); T = {}
    ft = int(json.load(open('scale_table.json'))[N]['ft_per_inch'])
    if f3_codes is None:
        f3_codes, rec3 = finder3.run(N, win, None, verbose=False); T['finder3'] = round(time.time() - t0, 1)
    else:
        rec3 = None; f3_codes = f3_codes if win is None else f3_codes[win[1]:win[3], win[0]:win[2]]
    gray, paper = DF.load(N)
    if win: gray, paper = gray[win[1]:win[3], win[0]:win[2]], paper[win[1]:win[3], win[0]:win[2]]
    code = f3_codes; rd = rb = None; blocks = None
    for step in (('block', 'ditto') if s['order'] == 'block_then_ditto' else ('ditto', 'block')):
        t1 = time.time()
        if step == 'block': code, rb, blocks = block_step(N, code, ft, s['block'], s)
        else: code, rd = ditto_step(N, code, gray, paper, ft)
        T[step] = round(time.time() - t1, 1)
    assert np.array_equal(code > 0, f3_codes > 0), 'ink changed'
    T['total'] = round(time.time() - t0, 1)
    rec = dict(finder='finder4', plate=N, win=win, scale_ft=ft, settings={k: (os.path.relpath(v, os.getcwd()) if isinstance(v, str) and os.path.isabs(v) else v) for k, v in s.items()},
               px={nm: int((code == v).sum()) for nm, v in finder3.finder2.CODE.items()},
               px_finder3={nm: int((f3_codes == v).sum()) for nm, v in finder3.finder2.CODE.items()},
               px_changed_from_finder3=int((code != f3_codes).sum()), seconds=T, ditto=rd, block=rb, finder3=rec3, made=time.strftime('%Y-%m-%d %H:%M'))
    if out:
        os.makedirs(out, exist_ok=True); stem = os.path.join(out, f'{N}_text')
        cv2.imwrite(stem + '.png', code)
        json.dump(rec, open(stem + '.json', 'w', encoding='utf8', newline='\n'), indent=1, default=str)
        if blocks is not None: json.dump(blocks, open(os.path.join(out, f'{N}_blocks.json'), 'w', encoding='utf8', newline='\n'), indent=1, default=str)
    if verbose: print(f"finder4 plate {N}: {rec['px_changed_from_finder3']} px changed from finder3; seconds {T}", flush=True)
    return code, rec, blocks


if __name__ == '__main__':
    a = sys.argv
    if len(a) < 2 or '--out' not in a: raise SystemExit(__doc__)
    N = a[1]
    win = tuple(int(v) for v in a[a.index('--win') + 1:a.index('--win') + 5]) if '--win' in a else None
    out = a[a.index('--out') + 1]
    f3 = cv2.imread(a[a.index('--finder3-mask') + 1], cv2.IMREAD_UNCHANGED) if '--finder3-mask' in a else None
    run(N, win, out, f3, sealed_ok='--sealed-ok' in a)
