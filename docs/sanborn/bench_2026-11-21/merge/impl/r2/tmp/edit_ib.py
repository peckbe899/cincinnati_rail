import sys
p = sys.argv[1]; s = open(p, encoding='utf8', newline='').read()
R = [
# docstring: the nets condition and the test options
("""every plate never placed, block line, lot line, water pipe and sewer were 0 and all line ink was 'not sorted' (2.43M px
on 90). Such a plate now takes its block lines and ground from the networks' block step (blocks_noguide.py, which
run_plates.py now runs BEFORE this):""",
 """every plate never placed, block line, lot line, water pipe and sewer were 0 and all line ink was 'not sorted' (2.43M px
on 90). Such a plate now takes its block lines and ground from the networks' block step (blocks_noguide.py, which
run_plates.py now runs BEFORE this), where that step is the merged one of 21 November 2026 or later: its
unet_data/N_outlines.json carries a 'version' (blocks_noguide.outline_version()). The batch's outlines of 21 Nov have
none: on 90 they are 1 block of 3 lines covering the whole sheet, margin included (sorted from them, 2.43M px of ink
became lot line and 19 px block line). On such a plate nothing is taken from them, the run says to run
blocks_noguide.py N --outlines-only first, and the sorting is as before (ground_from 'none'). A version older than
today's code is used, with a note: on a plate where Ben has edited the lines, the outline step is kept at the version
that made the lines he edited (blocks_noguide.py):"""),
("""For tests: --no-map sorts the plate as if it had never been placed (no street map, no label, no guide); --edges P and
--outlines P read another N_edges.json and outlines.json (the outline step's other outputs, N_outlines.json and
N_mapground.png, are then read from beside P; Ben's edits are not applied to another file's lines, which they are not
keyed to); --save OUT.png writes the bins there and no N_bins.json (--json OUT.json writes the counts beside it).
N_bins.json 'made_from' gives every input file with the start of its sha256 (run_plates.py redoes the sorting when one
of them changes).""",
 """For tests: --no-map sorts the plate as if it had never been placed (no street map, no label, no guide); --edges P and
--outlines P read another N_edges.json and outlines.json (the outline step's other outputs, N_outlines.json and
N_mapground.png, are then read from beside P; Ben's edits are not applied to another file's lines, which they are not
keyed to); --save OUT.png writes the bins there and no N_bins.json (--json OUT.json writes the counts beside it). The
test options (--no-map, --edges, --outlines, --unsure, --no-ben, --rail, --car) need --save: a plate's own N_bins.png is
only ever written by a plain run. An option it does not know is an error.
N_bins.json 'made_from' gives every input file with the start of its sha256, and 'outline_version' the version of the
outline step its lines and ground came from (outlines.py takes its railroad bin only from bins of its own version)."""),
# option check at the start of main()
("""def main():
    N = sys.argv[1]; t0 = time.time()
""",
 """OPTS = {'--win': 4, '--pic': 1, '--no-ben': 0, '--save': 1, '--json': 1, '--no-map': 0, '--edges': 1, '--outlines': 1, '--unsure': 1, '--rail': 1, '--car': 1, '--ticks': 0}
TEST_OPTS = ('--no-map', '--edges', '--outlines', '--unsure', '--no-ben', '--rail', '--car')   # these change the sorting: only with --save


def check_args(argv):
    \"\"\"stop on an option this script does not know, or a test option without --save (it would write the plate's N_bins.png)\"\"\"
    if len(argv) < 2 or argv[1].startswith('--'): sys.exit('usage: ink_bins.py N [options] (see the docstring)')
    k = 2
    while k < len(argv):
        a = argv[k]
        if a not in OPTS: sys.exit(f'ink_bins.py: unknown option or stray argument {a!r} (options: {", ".join(OPTS)})')
        if k + OPTS[a] >= len(argv): sys.exit(f'ink_bins.py: {a} needs {OPTS[a]} value(s)')
        k += 1 + OPTS[a]
    test = [o for o in TEST_OPTS if o in argv]
    if test and '--save' not in argv: sys.exit(f'ink_bins.py: {", ".join(test)} change the sorting; give --save OUT.png too (a plain run writes unet_data/{argv[1]}_bins.png)')
    if '--json' in argv and '--save' not in argv: sys.exit('ink_bins.py: --json goes with --save')


def main():
    check_args(sys.argv)
    N = sys.argv[1]; t0 = time.time()
"""),
# the nets condition
("""    placed = os.path.exists(f'unet_data/{N}_guide.png') and not (nomap or opt('--edges') or opt('--outlines'))
    SRC = 'map' if os.path.exists(smf) and not nomap else ('nets' if not placed and os.path.exists(ef) and os.path.exists(of) else 'label')""",
 """    placed = os.path.exists(f'unet_data/{N}_guide.png') and not (nomap or opt('--edges') or opt('--outlines'))
    rp = json.load(open(od + f'{N}_outlines.json', encoding='utf8')) if os.path.exists(od + f'{N}_outlines.json') else {}   # the outline step's counts, with its version
    SRC = 'map' if os.path.exists(smf) and not nomap else ('nets' if not placed and os.path.exists(ef) and os.path.exists(of) and rp.get('version') else 'label')
    if SRC == 'label' and not placed and os.path.exists(ef) and os.path.exists(of):
        print(f'plate {N}: its outlines ({of}) were made by the outline step before 21 Nov 2026 ({od}{N}_outlines.json has no version): not used. '
              f'Run  blocks_noguide.py {N} --outlines-only  first (run_plates.py does), then this again')
    elif SRC == 'nets':
        sys.path.insert(0, HERE)
        from blocks_noguide import outline_version  # noqa: E402   (no torch)
        if rp['version'] != outline_version():
            print(f'plate {N}: its outlines were made by outline step {rp["version"]}, today\\'s is {outline_version()}'
                  + (' (Ben has edited its lines: the new outlines are in unet_data/' + N + '_new/)' if os.path.exists(f'picks22_guided/22-{N}/edges_ben.json') and not opt('--edges') else
                     f'; blocks_noguide.py {N} --outlines-only makes new ones'))"""),
("""    elif SRC == 'nets':   # the networks' block step: the lines as the editor shows them (with Ben's edits), its blocks less their street holes
        sys.path.insert(0, HERE)
        import street_map  # noqa: E402   (editor_lines: the one function street_map.py uses too)""",
 """    elif SRC == 'nets':   # the networks' block step: the lines as the editor shows them (with Ben's edits), its blocks less their street holes
        import street_map  # noqa: E402   (editor_lines: the one function street_map.py uses too)"""),
("""        SL, _ = street_map.editor_lines(N, W, H, json.load(open(ef, encoding='utf8')), benl); used.update(lines=ef, **({'Ben edits': bf_} if benl else {}), blocks=of)""",
 """        SL, _ = street_map.editor_lines(N, W, H, json.load(open(ef, encoding='utf8')), benl); used.update(lines=ef, **({'Ben edits': bf_} if benl else {}), blocks=of, **{'outline step': od + f'{N}_outlines.json'})"""),
("""        if '--unsure' in sys.argv: UNS = tuple(float(v) for v in opt('--unsure').split(',')) if opt('--unsure') != 'none' else None
        else: UNS = UNSURE
        if UNS:
            rp = json.load(open(od + f'{N}_outlines.json', encoding='utf8')) if os.path.exists(od + f'{N}_outlines.json') else {}
            af = (rp.get('maps') or {}).get('area')""",
 """        if '--unsure' in sys.argv: UNS = tuple(float(v) for v in opt('--unsure').split(',')) if opt('--unsure') != 'none' else None
        else: UNS = UNSURE
        if UNS:
            af = (rp.get('maps') or {}).get('area')"""),
("""    rec = dict(plate=N, size=[W, H], note=note, made=int(time.time()), ground_from=SRC if SRC != 'label' or 'old label' in used else 'none', made_from={k: dict(file=v, sha256=sha16(v)) for k, v in used.items()}, ink_px=tot, ben_rail=bensay,""",
 """    rec = dict(plate=N, size=[W, H], note=note, made=int(time.time()), ground_from=SRC if SRC != 'label' or 'old label' in used else 'none', made_from={k: dict(file=v, sha256=sha16(v)) for k, v in used.items()},
               outline_version=rp.get('version') if SRC == 'nets' else None, ink_px=tot, ben_rail=bensay,"""),
]
for a, b in R:
    assert s.count(a) == 1, a[:120]
    s = s.replace(a, b)
open(p, 'w', encoding='utf8', newline='').write(s)
print('ok')
