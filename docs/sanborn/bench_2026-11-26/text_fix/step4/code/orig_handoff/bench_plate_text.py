"""bench_plate_text.py (text_v1/handoff, 26 Nov 2026): tools/sanborn/unet/bench_plate.py (imported, read only: its setup()
and make_truth()) with the outline step pointed at the hand-off copy (outline_hook.py -> outlines_text.py, mask from
HANDOFF_TEXT_MASK / HANDOFF_TEXT_DROP) and the hand-off step 4 (step4_text.py). bench_plate.main() has no --outlines or
--step4, so this is its main() with those two added to bench44's argv; everything else (truth, folds, decided ground,
scores, bench_plate.json) is bench_plate's own. Writes only inside text_v1/handoff.

    cd data/sanborn
    python -B bench_2026-11-25/text_v1/handoff/code/bench_plate_text.py --plate 5 --truth T.json --area A.png --lines L.png
           [--region MASK.png] --tag NAME --runs DIR
    python -B bench_2026-11-25/text_v1/handoff/code/bench_plate_text.py --make-truth N OUT.json
"""
import argparse, contextlib, io, json, os, sys, time
HERE = os.path.dirname(os.path.abspath(__file__)); SAFE = os.path.normcase(os.path.normpath(os.path.join(HERE, '..')))
TOOLS = os.path.normpath(os.path.join(HERE, '..', '..', '..', '..', '..', '..', 'tools', 'sanborn', 'unet'))
sys.path.insert(0, TOOLS); sys.path.insert(0, os.path.join(TOOLS, '..'))
import bench_plate as BP  # noqa: E402


def inside(p):
    if not os.path.normcase(os.path.abspath(p)).startswith(SAFE + os.sep): sys.exit(f'bench_plate_text.py: refusing to write outside {SAFE}: {p}')


def main():
    ap = argparse.ArgumentParser(allow_abbrev=False)
    ap.add_argument('--make-truth', nargs=2, metavar=('N', 'OUT'))
    ap.add_argument('--plate'); ap.add_argument('--truth'); ap.add_argument('--area'); ap.add_argument('--lines'); ap.add_argument('--region')
    ap.add_argument('--tag'); ap.add_argument('--runs'); ap.add_argument('--reuse', action='store_true')
    a = ap.parse_args()
    if a.make_truth:
        inside(a.make_truth[1]); print(json.dumps(BP.make_truth(a.make_truth[0], a.make_truth[1]))); return
    inside(a.runs)
    plate = a.plate.upper(); truth = os.path.abspath(a.truth); region = os.path.abspath(a.region) if a.region else None
    import bench44 as B
    t0 = time.time(); sm, M = BP.setup(B, plate, truth, region)
    tag = a.tag
    argv = [B.__file__, '--area', os.path.abspath(a.area), '--lines', os.path.abspath(a.lines), '--tag', tag, '--runs', os.path.abspath(a.runs), '--no-pic',
            '--outlines', os.path.join(HERE, 'outline_hook.py'), '--step4', os.path.join(HERE, 'step4_text.py')]
    if a.reuse: argv.append('--reuse')
    sys.argv = argv
    with contextlib.redirect_stdout(io.StringIO()): B.main()
    run = B.RUNS + f'{tag}/'; res = json.load(open(run + 'bench44.json', encoding='utf8'))
    T = B.load_truth(); inA = T['isA']
    res['meta'].update(plate=plate, truth=f'{truth} (sha256 {BP.sha(truth)}; {len(sm["blocks"])} blocks, {len(sm["lines"])} lines)', truth_source=sm.get('source'), truth_saved_at=sm.get('source_saved_at'),
                       folds=(f'A: inside the region {region} (sha256 {BP.sha(region)}), B: outside' if region else 'no region: every block and line in A'),
                       region=dict(file=region, share_of_plate=round(float(M.mean()), 4), truth_blocks_in=int(inA.sum()), truth_blocks_out=int((~inA).sum())),
                       wrapper=dict(file=os.path.abspath(__file__), bench_plate=BP.__file__, bench_plate_sha256=BP.sha(BP.__file__), bench44=B.__file__, bench44_sha256=BP.sha(B.__file__)),
                       text_mask=os.environ.get('HANDOFF_TEXT_MASK', ''), text_drop=os.environ.get('HANDOFF_TEXT_DROP', ''), wrapper_seconds=round(time.time() - t0, 1))
    res['region_headline'] = dict(region=res['headline']['A'], outside=res['headline']['B'], all=res['headline']['all'])
    json.dump(res, open(run + 'bench_plate.json', 'w', encoding='utf8', newline='\n'), indent=1)
    print(json.dumps(dict(tag=tag, run=run, region_blocks=int(inA.sum()), headline=res['region_headline'])))


if __name__ == '__main__':
    main()
