"""Measured summary of the held-out crops H3 and H4: python -B stats.py  ->  heldout-b/stats.json
Pixel counts by mask value, words by kind and flag, words touching a line, care from hand CARE boxes against care
from shared ink, and the agreement of the mask's ink with the ink layer of unet_data/N_bins.png (only ink against
paper is compared; the bins themselves are not read)."""
import os, json
from collections import Counter
import numpy as np, cv2
from hcommon import CROPS, OUT, KEYDIR, ROOT


def main():
    res = {}
    for cid, cr in CROPS.items():
        d = json.load(open(os.path.join(OUT, f'{cid}_words.json'), encoding='utf8'))
        m = cv2.imread(os.path.join(OUT, f'{cid}_mask.png'), 0)
        X0, Y0, X1, Y1 = cr['win']
        box = np.zeros(m.shape, bool)
        for b in d['boxes']:
            if b['op'] == 'CARE':
                x0, y0, x1, y1 = b['box']
                box[max(0, y0 - Y0):max(0, y1 - Y0), max(0, x0 - X0):max(0, x1 - X0)] = True
        bins = cv2.imread(os.path.join(ROOT, 'unet_data', f"{cr['plate']}_bins.png"), 0)
        agree = float(((bins[Y0:Y1, X0:X1] > 0) == (m > 0)).mean()) if bins is not None else None
        ws = d['words']
        scored = int(((m == 1) | (m == 2)).sum())
        res[cid] = dict(
            plate=cr['plate'], win=cr['win'], scale_ft=cr['scale_ft'], words=len(ws),
            px={'paper': int((m == 0).sum()), 'nontext': int((m == 1).sum()), 'text': int((m == 2).sum()),
                'care': int((m == 3).sum())},
            text_share_of_scored_ink=round(int((m == 2).sum()) / scored, 4),
            care_share_of_ink=round(int((m == 3).sum()) / int((m > 0).sum()), 4),
            care_in_hand_care_boxes=int(((m == 3) & box).sum()), care_shared_ink=int(((m == 3) & ~box).sum()),
            hand_care_box_area=int(box.sum()),
            kinds=dict(Counter(w['kind'] for w in ws)),
            flags=dict(Counter(f.split(':')[0] for w in ws for f in w['flags'])),
            touches_line=sum(w['touches_line'] for w in ws),
            readable_words=sum(1 for w in ws if not set(w['flags']) & {'unsure', 'partial', 'run'}),
            words_under_20px=sum(1 for w in ws if w['text_px'] < 20),
            hand_ops=dict(Counter(b['op'] for b in d['boxes'])),
            ink_agreement_with_bins=agree)
    json.dump(res, open(os.path.join(KEYDIR, 'stats.json'), 'w'), indent=1)
    print(json.dumps(res, indent=1))


if __name__ == '__main__':
    main()
