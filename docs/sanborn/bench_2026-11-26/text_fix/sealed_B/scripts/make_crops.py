"""Write sealed_B/truth/crops.json from the chosen targets (annot/selection.json and the lists below). Keeps the
"scope" fields build.py wrote. python -B make_crops.py"""
import os, sys, json
sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from common import INV, jdump

SCALE = {'56': 100, '58': 100, '63': 100, '71': 200, '76': 200, '84': 200, '88': 200, '92': 400}
# block targets in the order drawn (plate, block, centre of the figures found at full size); window = centre +-150 x, +-130 y
BLOCKS = [('56', '16', 647, 5529), ('56', '17', 1985, 5964), ('56', '12', 9030, 1524),
          ('58', '36', 5672, 2330), ('58', '20', 1003, 3128), ('58', '51', 3293, 6368),
          ('63', '15', 8940, 2528), ('63', '18', 2754, 4268), ('63', '21', 7714, 3378),
          ('71', '5', 4900, 700), ('71', '22', 3940, 3520), ('71', '17', 5316, 2649),
          ('76', '57', 2693, 4239), ('76', '82', 4311, 5367), ('76', '5', 2157, 1724),
          ('84', '17', 2685, 5500), ('84', '21', 4575, 5179), ('84', '18', 3180, 5489),
          ('88', '6', 4463, 934), ('88', '27', 4055, 4630), ('88', '13', 5714, 2680),
          ('92', '12', 1319, 4807), ('92', '13', 3847, 4815), ('92', '8', 6130, 3308), ('92', '5', 5475, 3197), ('92', '4', 4605, 3520)]


def main():
    path = os.path.join(INV, 'truth', 'crops.json')
    old = json.load(open(path, encoding='utf8')) if os.path.exists(path) else {}
    sel = json.load(open(os.path.join(INV, 'truth', 'annot', 'selection.json'), encoding='utf8'))
    out = {}
    for i, (p, b, cx, cy) in enumerate(BLOCKS):
        k = f'SB-B{i + 1:02d}'
        out[k] = dict(plate=p, win=[cx - 150, cy - 130, cx + 150, cy + 130], scale_ft_per_inch=SCALE[p], kind='targeted', target='block',
                      scope_pad=25, why=f'block {b} on plate {p}, drawn with random.Random({p!r}) from the plate list (annot/selection.json)')
    dw = json.load(open(os.path.join(INV, 'truth', 'annot', 'ditto_windows.json'), encoding='utf8')) if os.path.exists(os.path.join(INV, 'truth', 'annot', 'ditto_windows.json')) else {}
    for k, v in dw.items():
        out[k] = dict(plate=v['plate'], win=v['win'], scale_ft_per_inch=SCALE[v['plate']], kind='targeted', target='ditto', scope_pad=25,
                      why=f"ditto window {v['draw']} drawn with random.Random('ditto-{v['plate']}') in built-up cells: every ditto mark inside")
    f = sel['full']
    out['SB-F1'] = dict(plate=f['plate'], win=f['win'], scale_ft_per_inch=SCALE[f['plate']], kind='full', line_bridge=4,
                        why="full crop, 1500 x 1000, placed with random.Random('SB-F1') among built-up cells of a 100 ft plate")
    for k in out:
        if k in old and 'scope' in old[k] and old[k]['win'] == out[k]['win']: out[k]['scope'] = old[k]['scope']
    jdump(out, path); print(len(out), 'crops')


if __name__ == '__main__':
    main()
