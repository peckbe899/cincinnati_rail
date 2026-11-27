"""The ditto crops: each is one drawn window (choose/windows.json, plate and rank) that holds one or more ditto marks.
Writes truth/crops.json. (dev_ditto, 26 Nov 2026)

    cd data/sanborn; python -B bench_2026-11-26/text_fix/dev_ditto/scripts/crops_def.py"""
import json, os
HERE = os.path.dirname(os.path.abspath(__file__)); DD = os.path.normpath(os.path.join(HERE, '..'))
SC = json.load(open('scale_table.json'))
W = json.load(open(os.path.join(DD, 'choose', 'windows.json')))
# id: (plate, rank, why)
CROPS = {
    'DD01': ('30', 1, "three small '\"' marks in a row of lots under the street line"),
    'DD02': ('30', 2, 'a row of tiny tick pairs under 26.3 along a row of lots'),
    'DD03': ('30', 3, 'two columns of tiny tick pairs and dots beside rows of lots'),
    'DD04': ('30', 4, 'two columns of tick pairs and blobs under 26 and 20 lot dimensions'),
    'DD05': ('30', 6, 'two columns of tiny tick pairs beside rows of lots, a 6" W.P. pipe label between'),
    'DD06': ('90', 1, "two tiny ':' tick pairs in lots beside rotated 120' dimensions"),
    'DD07': ('90', 6, "one tiny '=' mark (unsure) in a lot right of lot 57"),
    'DD08': ('60B', 1, "one '=' mark in a lot beside 190"),
    'DD09': ('60B', 3, "three '=' marks in lots along a block side"),
    'DD10': ('60B', 4, "three '=' marks beside lots 65, 66 and 26"),
    'DD11': ('60B', 5, "one tick-pair ditto under a lot line between two 40' dimensions"),
    'DD12': ('60B', 6, "one '=' mark beside a rotated 50' dimension"),
    'DD13': ('19', 1, "two slanted '\"' marks above a street line"),
    'DD14': ('19', 2, "three slanted '\"' marks in lot frontages"),
    'DD15': ('19', 3, "four small '\"' marks in a row of lots above a street"),
}
# more crops are added from crops_more.txt (one per line: ID PLATE RANK WHY...), so this file need not be edited again
_more = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'crops_more.txt')
if os.path.exists(_more):
    for _l in open(_more, encoding='utf8'):
        _f = _l.strip().split(None, 3)
        if len(_f) >= 3 and not _l.startswith('#'): CROPS[_f[0]] = (_f[1], int(_f[2]), _f[3] if len(_f) > 3 else '')


def main():
    out = {}
    for k, (p, r, why) in CROPS.items():
        w = W[p]['windows'][r - 1]; assert w['rank'] == r
        out[k] = dict(plate=p, win=w['win'], scale_ft_per_inch=SC[p]['ft_per_inch'], why=why, kind='targeted', target='ditto',
                      scope_pad=25, drawn=dict(seed=W[p]['seed'], rank=r, draw=w['draw']))
    os.makedirs(os.path.join(DD, 'truth'), exist_ok=True)
    json.dump(out, open(os.path.join(DD, 'truth', 'crops.json'), 'w'), indent=1)
    print(len(out), 'crops')


if __name__ == '__main__':
    main()
