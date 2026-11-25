"""Sort the words of finished runs into kinds again with today's classify.py, without grouping again (the kinds read
only the word features stored in out/TAG_words.json). The text mask does not change unless the junk rule changes, and
it is rewritten here from the stored glyph labels in case it does.

    cd data/sanborn
    python -B bench_2026-11-25/text/words/scripts/reclassify.py TAG [TAG ...]      (e.g. 44 5 1A 90 44_finder)"""
import json, os, sys
import numpy as np
import cv2
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE); OUT = os.path.join(os.path.dirname(HERE), 'out')
import classify as cl  # noqa: E402


def main():
    for T in sys.argv[1:]:
        f = os.path.join(OUT, f'{T}_words.json'); J = json.load(open(f, encoding='utf8'))
        cl.classify(J['strings'], None)
        L = cv2.imread(os.path.join(OUT, f'{T}_glyphlab.png'))
        lab = L[..., 0].astype(np.int32) | (L[..., 1].astype(np.int32) << 8) | (L[..., 2].astype(np.int32) << 16)
        keep = np.zeros(lab.max() + 1, bool)
        for r in J['strings']:
            for w in r['words']:
                if w['kind'] != 'junk':
                    for g in w['glyphs'] + [m['g'] for m in w['marks']]: keep[g + 1] = True
        keep[0] = False
        cv2.imwrite(os.path.join(OUT, f'{T}_textmask.png'), keep[lab].astype(np.uint8) * 255)
        J['meta']['reclassified'] = True
        json.dump(J, open(f, 'w', encoding='utf8'))
        json.dump(dict(plate=J['meta']['plate'], strings=[dict(id=r['id'], kind=r['words'][0]['kind']) for r in J['strings']]), open(os.path.join(OUT, f'{T}_kinds.json'), 'w', encoding='utf8'))
        k = {}
        for r in J['strings']:
            for w in r['words']: k[w['kind']] = k.get(w['kind'], 0) + 1
        print(T, dict(sorted(k.items(), key=lambda x: -x[1])))


if __name__ == '__main__':
    main()
