"""DEV ONLY (integrate, 26 Nov 2026): run the two block fixes and the ditto fix on whole dev plates, from finder3's stored
masks, in the orders and combinations finder4 might use. The fixers are the byte-identical copies in this folder's code/
(blockfix_a.py = fix_block_a/code/blockfix.py, blockfix_b.py = fix_block_b/code/blockfix.py, dittofix.py =
fix_ditto/code/dittofix.py; models in ../models). Reads no truth.

    cd data/sanborn
    python -B bench_2026-11-26/text_fix/integrate/code/devrun.py OUT_ROOT VARIANTS N [N ...]

VARIANTS, comma separated (each writes OUT_ROOT/<variant>/N_text.png and N_text.json, B steps also N_blocks.json):
  A     block fix A on finder3                       Bf    block fix B, final models (fitted on all 12 dev plates)
  Bx    block fix B, cross-fold models (a fold-A plate gets the models fitted on fold B's plates, and the other way round;
        fix_block_b's folds: A = 3 54A 30 26A 74 49, B = 12 19 64A 60B 93A 48); only for those 12 plates
  BfA   A run on Bf's output                         BxA   A run on Bx's output
  ABf   B (final) run on A's output                  ABx   B (cross-fold) run on A's output
  D     dittofix on finder3
  <V>D  dittofix on variant V's output (e.g. BfAD)   D<V> the block step(s) of V run on D's output (e.g. DBfA)
Inputs are read from OUT_ROOT/<variant>/ when they were made before (so A is not run twice).
"""
import json, os, sys, time
sys.dont_write_bytecode = True
import numpy as np, cv2
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import blockfix_a as BA, blockfix_b as BB, dittofix as DF  # noqa: E402

F3 = os.path.join(HERE, '..', 'work', 'f3')
MOD = os.path.normpath(os.path.join(HERE, '..', 'models'))
SEALED = {'6', '9', '52', '56', '58', '63', '35', '38', '41', '66', '71', '76', '84', '88', '46', '92'}
BFOLD = {'A': {'3', '54A', '30', '26A', '74', '49'}, 'B': {'12', '19', '64A', '60B', '93A', '48'}}


def other_fold(N):
    for f, s in BFOLD.items():
        if N in s: return 'B' if f == 'A' else 'A'
    return None


def b_args(N, kind):
    if kind == 'f': return dict(tmpl=os.path.join(MOD, 'tmpl_real_all.npz'), model=os.path.join(MOD, 'cls_all.npz'), num_model=os.path.join(MOD, 'num_all.npz'))
    o = other_fold(N)
    if o is None: return None
    return dict(tmpl=os.path.join(MOD, f'tmpl_real_{o}.npz'), model=os.path.join(MOD, f'cls_{o}.npz'), num_model=os.path.join(MOD, f'num_{o}.npz'))


def save(root, v, N, code, info, blocks=None):
    d = os.path.join(root, v); os.makedirs(d, exist_ok=True)
    cv2.imwrite(os.path.join(d, f'{N}_text.png'), code)
    json.dump(info, open(os.path.join(d, f'{N}_text.json'), 'w', encoding='utf8', newline='\n'), indent=1, default=str)
    if blocks is not None: json.dump(blocks, open(os.path.join(d, f'{N}_blocks.json'), 'w', encoding='utf8', newline='\n'), indent=1, default=str)


def main():
    root, vs, plates = sys.argv[1], sys.argv[2].split(','), sys.argv[3:]
    ftab = json.load(open('scale_table.json'))
    for N in plates:
        if N in SEALED: raise SystemExit(f'plate {N} is sealed')
        ft = int(ftab[N]['ft_per_inch']); f3 = cv2.imread(os.path.join(F3, f'{N}_text.png'), cv2.IMREAD_UNCHANGED)
        have = {'F3': f3}; gp = {}

        def get(v):
            if v in have: return have[v]
            p = os.path.join(root, v, f'{N}_text.png')
            if os.path.exists(p): have[v] = cv2.imread(p, cv2.IMREAD_UNCHANGED); return have[v]
            return make(v)

        def block(step, src):
            """one block step on src codes: 'A', 'Bf' or 'Bx'"""
            t0 = time.time()
            if step == 'A':
                out, info = BA.apply(N, src, None, ft, return_info=True); blocks = None
            else:
                kw = b_args(N, step[1])
                if kw is None: return None, None, None
                tm, mo = kw.pop('tmpl'), kw.pop('model')
                out, info, nums, rej = BB.apply(N, src, None, ft, tmpl=tm, model=mo, return_info=True, **kw)
                blocks = dict(plate=N, scale_ft=ft, model=info['model'], numbers=nums, rejected=rej)
            info['step_seconds'] = round(time.time() - t0, 1); return out, info, blocks

        def ditto(src):
            if 'g' not in gp: gp['g'] = DF.load(N)
            gray, paper = gp['g']; rep = {}; t0 = time.time()
            out = DF.apply(N, src, gray, ft, paper=paper, report=rep); rep['step_seconds'] = round(time.time() - t0, 1); return out, rep

        def make(v):
            t0 = time.time()
            if v == 'D': out, info = ditto(f3); blocks = None
            elif v.endswith('D'):
                src = get(v[:-1])
                if src is None: return None
                out, info = ditto(src); blocks = None
            elif v.startswith('D') and len(v) > 1:
                rest = v[1:]; src = get('D')
                # the block steps of rest, in order, on D's output
                steps = split(rest); blocks = None
                for s in steps:
                    src, info, b = block(s, src)
                    if src is None: return None
                    blocks = b or blocks
                out = src
            else:
                steps = split(v)
                if len(steps) == 1:
                    out, info, blocks = block(steps[0], f3)
                    if out is None: return None
                else:
                    src = get(join(steps[:-1]))
                    if src is None: return None
                    out, info, blocks = block(steps[-1], src)
                    if out is None: return None
            info['variant'] = v; info['variant_seconds'] = round(time.time() - t0, 1)
            save(root, v, N, out, info, blocks); have[v] = out
            print(f'{N} {v}: {int((out != f3).sum())} px differ from finder3, {time.time() - t0:.0f} s', flush=True)
            return out

        for v in vs: get(v)


def split(v):
    """'BfA' -> ['Bf', 'A'], 'ABx' -> ['A', 'Bx']"""
    out = []; i = 0
    while i < len(v):
        if v[i] == 'A': out.append('A'); i += 1
        elif v[i] == 'B': out.append(v[i:i + 2]); i += 2
        else: raise ValueError(v)
    return out


def join(steps): return ''.join(steps)


if __name__ == '__main__':
    main()
