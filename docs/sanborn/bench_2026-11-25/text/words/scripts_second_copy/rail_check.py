"""Does taking the text out first stop the false railroad on plate 5? (25 Nov 2026, words agent)

    cd data/sanborn
    python -B bench_2026-11-25/text/words/scripts/rail_check.py [N]

Runs the repo's tick rule (tools/sanborn/unet/ink_bins.railroad, imported, not changed) on plate N's ink three ways:
  all      all the ink (as ink_bins does with --no-ben)
  -bin8    the ink less every bin-8 piece of unet_data/N_bins.png
  -words   the ink less the words agent's text mask (out/N_textmask.png: the pieces of every word not called junk)
  -finder  the ink less the finder agent's text (finder/out/N_finder.png codes 2-4), if it exists
  -words_on_finder  the ink less the words agent's mask made from the finder's candidates (out/N_finder_textmask.png)
Plate 5 has no railroad (Ben's rail_ben.json is complete and holds streetcar only), so every railroad pixel the rule
finds there is false. On a plate with Ben's railroad (44: 28 tracks, complete) it also reports how much of his railroad's
length the rule still finds (within 10 px) with the text taken out, and the railroad px more than 25 px from his tracks
(only 'all', '-finder', '-words_on_finder' there: bin 8 on 44 was sorted after his rail was taken out). The ground ('closed') is picks22_guided/22-N/outlines.json's blocks, as ink_bins' nets ground.
Caveat: unet_data/5_bins.png was sorted with Ben's tracks counting as all the rail, so its bin 8 was not made with the
rule's railroad taken out first; the finder's candidates, made from the raw ink, are the fair test. Writes
out/rail_check_N.json. Nothing in the repo is written."""
import json, os, sys, time
import numpy as np
import cv2
HERE = os.path.dirname(os.path.abspath(__file__)); OUT = os.path.join(os.path.dirname(HERE), 'out')
REPO = os.path.abspath(os.path.join(HERE, *(['..'] * 6)))
sys.path.insert(0, os.path.join(REPO, 'tools', 'sanborn', 'unet'))
import ink_bins as ib  # noqa: E402


def main():
    N = sys.argv[1] if len(sys.argv) > 1 else '5'
    im = cv2.imread(f'cufp/22-{N}.jpg'); H, W = im.shape[:2]
    L = cv2.cvtColor(im, cv2.COLOR_BGR2LAB)[..., 0]; del im
    al = np.load(f'cufp/{N}/png_alpha_s4.npy'); paper = cv2.resize(al, (W, H), interpolation=cv2.INTER_NEAREST) > 0
    ink = (L < ib.INK_L) & paper; del L
    closed = ib.block_ground(json.load(open(f'picks22_guided/22-{N}/outlines.json', encoding='utf8')), H, W)
    b8 = cv2.imread(f'unet_data/{N}_bins.png', 0) == 8
    tm = cv2.imread(os.path.join(OUT, f'{N}_textmask.png'), 0) > 0
    runs = [('all', ink), ('-bin8', ink & ~b8), ('-words', ink & ~tm)]
    ff = f'bench_2026-11-25/text/finder/out/{N}_finder.png'
    if os.path.exists(ff):                    # the finder's text, made from the raw ink with no rail rule run first: the fair test
        fm = cv2.imread(ff, 0); ft = (fm >= 2) & (fm <= 4); runs.append(('-finder', ink & ~ft))
        wf = os.path.join(OUT, f'{N}_finder_textmask.png')
        if os.path.exists(wf): runs.append(('-words_on_finder', ink & ~(cv2.imread(wf, 0) > 0)))
    if N != '5': runs = [x for x in runs if x[0] in ('all', '-finder', '-words_on_finder')]   # bin 8 elsewhere was sorted after the rail
    # Ben's railroad (rail_ben.json): how much of it the rule finds (within 10 px, as ink_bins reports it) and how much
    # railroad px lies more than 25 px from every one of his tracks
    bj = json.load(open(f'picks22_guided/22-{N}/rail_ben.json', encoding='utf8')); BEN = [t for t in bj.get('tracks', []) if t['kind'] == 'railroad']
    benm = ib.ben_masks(BEN, H, W)['railroad']; samp = []
    for t in BEN:
        p = np.array(t['pts'], float)
        for q0, q1 in zip(p[:-1], p[1:]): samp.append(q0[None] + np.linspace(0, 1, max(2, int(np.hypot(*(q1 - q0)) / 5) + 1))[:, None] * (q1 - q0)[None])
    q = np.vstack(samp).round().astype(int) if samp else np.zeros((0, 2), int)
    if len(q): q = q[(q[:, 0] >= 0) & (q[:, 0] < W) & (q[:, 1] >= 0) & (q[:, 1] < H)]
    far = cv2.dilate(benm, np.ones((31, 31), np.uint8)) == 0
    res = {}
    for name, m in runs:
        t0 = time.time(); rr, info = ib.railroad(m, closed, paper)
        found = float(cv2.dilate(rr.astype(np.uint8), np.ones((21, 21), np.uint8))[q[:, 1], q[:, 0]].mean()) if len(q) else None
        n, lab, st, _ = cv2.connectedComponentsWithStats(cv2.dilate(rr.astype(np.uint8), np.ones((15, 15), np.uint8)), connectivity=8)
        res[name] = dict(ink_px=int(m.sum()), railroad_px=int(rr.sum()), pieces=int(n - 1), clear_ticks=int(info['clear']), faint_ticks=int(info['faint']),
                         ticks_in_rows=int(info['chained']), seconds=round(time.time() - t0, 1),
                         ben_railroad_tracks=len(BEN), ben_railroad_found=None if found is None else round(found, 4), railroad_px_far_from_ben=int((rr & far).sum()))
        print(name, res[name], flush=True)
    json.dump(dict(plate=N, note='railroad rule of ink_bins.py on the ink with and without the text taken out first; on plate 5 every railroad px is false',
                   results=res), open(os.path.join(OUT, f'rail_check_{N}.json'), 'w'), indent=1)


if __name__ == '__main__':
    main()
