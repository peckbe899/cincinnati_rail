"""Write integrate/FROZEN.txt: sha256 of finder4.py and of every file it imports or loads, the exact command, the
software versions, and the sha256 of the 10 whole-plate masks it made (out/finder4). Run once, from data/sanborn.

    python -B bench_2026-11-26/text_fix/integrate/code/freeze.py
"""
import hashlib, os, sys, time, json
sys.dont_write_bytecode = True
I = os.path.join('bench_2026-11-26', 'text_fix', 'integrate')
TV1 = os.path.join('bench_2026-11-25', 'text_v1')
TF = os.path.join('bench_2026-11-26', 'text_fix')


def sha(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''): h.update(b)
    return h.hexdigest()


FILES = [
    ('finder4 (this tool)', os.path.join(I, 'code', 'finder4.py')),
    ('ditto step, byte-identical copy of fix_ditto/code/dittofix.py', os.path.join(I, 'code', 'dittofix.py')),
    ('block step A, byte-identical copy of fix_block_a/code/blockfix.py', os.path.join(I, 'code', 'blockfix_a.py')),
    ('block step B, byte-identical copy of fix_block_b/code/blockfix.py', os.path.join(I, 'code', 'blockfix_b.py')),
    ('block step B digit models (copy of fix_block_b/models/tmpl_real_all.npz)', os.path.join(I, 'models', 'tmpl_real_all.npz')),
    ('block step B figure classifier (copy of fix_block_b/models/cls_all.npz)', os.path.join(I, 'models', 'cls_all.npz')),
    ('block step B number model (copy of fix_block_b/models/num_all.npz)', os.path.join(I, 'models', 'num_all.npz')),
    ('finder3, imported read-only', os.path.join(TV1, 'code', 'finder3.py')),
    ('finder2, imported by finder3, blockfix_a and blockfix_b', os.path.join(TV1, 'code', 'finder2.py')),
    ('classifier piece features, imported by finder3', os.path.join(TV1, 'classifier', 'scripts', 'common.py')),
    ('classifier net, imported by finder3', os.path.join(TV1, 'classifier', 'scripts', 'model_np.py')),
    ('combiner, imported by finder3 at run time', os.path.join(TV1, 'classifier', 'scripts', 'stack.py')),
    ('finder3 CNN weights', os.path.join(TV1, 'classifier', 'out', 'model_cnn2.npz')),
    ('finder3 combiner weights', os.path.join(TV1, 'classifier', 'out', 'combiner_cnn2.npz')),
    ('scale table, read by finder4, finder2 and dittofix', 'scale_table.json'),
]
SOURCES = {os.path.join(I, 'code', 'dittofix.py'): os.path.join(TF, 'fix_ditto', 'code', 'dittofix.py'),
           os.path.join(I, 'code', 'blockfix_a.py'): os.path.join(TF, 'fix_block_a', 'code', 'blockfix.py'),
           os.path.join(I, 'code', 'blockfix_b.py'): os.path.join(TF, 'fix_block_b', 'code', 'blockfix.py'),
           os.path.join(I, 'models', 'tmpl_real_all.npz'): os.path.join(TF, 'fix_block_b', 'models', 'tmpl_real_all.npz'),
           os.path.join(I, 'models', 'cls_all.npz'): os.path.join(TF, 'fix_block_b', 'models', 'cls_all.npz'),
           os.path.join(I, 'models', 'num_all.npz'): os.path.join(TF, 'fix_block_b', 'models', 'num_all.npz')}

out = os.path.join(I, 'FROZEN.txt')
if os.path.exists(out): raise SystemExit('FROZEN.txt exists already: finder4 is frozen')
import numpy, cv2, scipy  # noqa: E402
L = ['finder4 FROZEN ' + time.strftime('%Y-%m-%d %H:%M') + ' (integrate, text_fix). No change to any file below after this.', '',
     'Command (run from data/sanborn = C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn):',
     '    python -B bench_2026-11-26/text_fix/integrate/code/finder4.py N --out DIR',
     '    (optional: --win X0 Y0 X1 Y1 for a window. A sealed plate is refused unless --sealed-ok is given: that flag is',
     '     for the final gate only. --finder3-mask is a dev shortcut and is not part of the frozen command.)',
     'Writes DIR/N_text.png (codes 0-5; text = codes 2,3), DIR/N_text.json, DIR/N_blocks.json.',
     'Settings inside finder4.py: S4 = block Upix (B, plus A where B changed nothing), order ditto_then_block, pad 8.',
     f'Software: python {sys.version.split()[0]}, numpy {numpy.__version__}, opencv {cv2.__version__}, scipy {scipy.__version__} (system python).', '',
     'sha256 of every file finder4 imports or loads (paths from data/sanborn):']
for why, p in FILES:
    L.append(f'  {sha(p)}  {p.replace(os.sep, "/")}    [{why}]')
L += ['', 'The copies are byte-identical to their sources (sha256 of the source, same as above):']
for c, s in SOURCES.items():
    a, b = sha(c), sha(s); L.append(f'  {"SAME" if a == b else "DIFFERENT"}  {s.replace(os.sep, "/")}  {b}')
L += ['', 'Per plate it also reads the scan cufp/22-N.jpg and the paper mask cufp/N/png_alpha_s4.npy (not listed).', '',
      'Outputs made with exactly these files before the freeze (out/finder4, whole plates; sha256 of N_text.png):']
d = os.path.join(I, 'out', 'finder4')
for f in sorted(os.listdir(d)):
    if f.endswith('_text.png'): L.append(f'  {sha(os.path.join(d, f))}  {f}')
open(out, 'w', encoding='utf8', newline='\n').write('\n'.join(L) + '\n')
print('\n'.join(L))
