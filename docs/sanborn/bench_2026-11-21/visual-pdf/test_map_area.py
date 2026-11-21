"""Run map_area.py on every uncut PDF sheet (cufp/N/source.json) and write overlays for checking by eye.

    python test_map_area.py [N ...]      -> maparea_check/N_map_area.jpg, N_map_area.json, maparea_check/summary.json

Overlay (1/8 size): off-map greyed, map ground outlined green, KEY and title magenta, scale note and bar blue, compass
rose and its arrow orange, heavy frame lines red, region ids (rN share-of-map) at each island's centroid.
"""
import glob, json, os, sys, time
import numpy as np, cv2
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import map_area as MA  # noqa: E402
D = 'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn/'
OUT = os.path.join(HERE, 'maparea_check'); os.makedirs(OUT, exist_ok=True)

if __name__ == '__main__':
    pl = sys.argv[1:] or sorted([os.path.basename(os.path.dirname(p)) for p in glob.glob(D + 'cufp/*/source.json')], key=lambda s: int(''.join(c for c in s if c.isdigit())))
    sp = os.path.join(OUT, 'summary.json' if not sys.argv[1:] else f'summary_{pl[0]}.json'); summ = json.load(open(sp)) if os.path.exists(sp) else {}
    for n in pl:
        scan = cv2.imread(D + f'cufp/22-{n}.jpg'); ap = D + f'cufp/{n}/png_alpha_s4.npy'
        alpha = np.load(ap) if os.path.exists(ap) else None
        r = MA.map_area(scan, alpha)
        paper_iou = r['paper_iou_vs_alpha']        # map_area's own paper mask against the repo's png_alpha_s4
        rec = {k: v for k, v in r.items() if k not in ('mask', 'mask8', 'frames8', 'furniture8', 'paper8', 'paper')}
        rec.update(plate=n, size=[scan.shape[1], scan.shape[0]], paper_detector_iou_vs_alpha=None if paper_iou is None else round(paper_iou, 4))
        json.dump(rec, open(os.path.join(OUT, f'{n}_map_area.json'), 'w'), indent=1, default=float)
        cv2.imwrite(os.path.join(OUT, f'{n}_mask8.png'), r['mask8'].astype(np.uint8) * 255)      # 1/8-size map ground (255 = map)
        v = MA.overlay(scan, r)
        cv2.putText(v, f"{n}  map {r['map_share_of_paper']:.2f} of paper  {len(r['regions'])} regions  {len(r['frames'])} frames  {r['flags']}", (20, v.shape[0] - 12), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 200), 2)
        cv2.imwrite(os.path.join(OUT, f'{n}_map_area.jpg'), v, [cv2.IMWRITE_JPEG_QUALITY, 80])
        summ[n] = dict(map_share=r['map_share_of_paper'], regions=[g['share_of_map'] for g in r['regions']], frames=len(r['frames']),
                       found={k: sum(e['kind'] == k for e in r['excluded']) for k in ('key', 'title', 'scale_note', 'scale_bar', 'compass_rose')},
                       scores={e['kind'] + str(i): e['score'] for i, e in enumerate(r['excluded'])}, flags=r['flags'], seconds=r['seconds'], paper_iou=rec['paper_detector_iou_vs_alpha'])
        print(n, summ[n], flush=True)
        json.dump(summ, open(sp, 'w'), indent=1)
