"""Annotated audit crops: the batch's editor lines on the scan, with each error type marked (visual-cut, 21 Nov 2026).
Reads only; writes annotated/N_tag.jpg.

    python annotate.py            all crops below
    python annotate.py N          only plate N's crops

Colours as in view.py (green / orange editor lines, grey dropped short pieces, cyan sheet edge, red dot = line end with
no other end within 25 px, light blue = ground called block, red number = polygon id). Magenta rings = audit notes.
Plate 44: magenta lines = Ben's street map (ground truth).
"""
import json, os, sys
import cv2
from vlib import load, draw, HERE, SP

CROPS = {
    '5': [('alleys_markets', (4000, 2900, 2800, 2000, 0.68), [
        (4700, 3300, 'merged across alley (L\'Hommedieu)'), (4815, 3120, 'stub alley missed'), (4350, 3640, 'spills into street: side missing'),
        (4600, 4180, 'market house in street called block'), (5950, 4150, 'flower market in street called block'), (4650, 4530, 'merged across Thorpe Alley'),
        (5760, 4620, 'N-S alley missed'), (5600, 2960, 'spills into Seventh St'), (4630, 3570, 'broken side')])],
    '60B': [('midblock_alleys', (1550, 950, 1500, 1050, 1.0), [
        (2140, 1450, 'merged across alley'), (1660, 1350, 'merged across alley'), (2950, 1600, 'alley cut only at its ends'), (2170, 1130, 'V-notch at alley mouth, dropped')])],
    '1B': [('river_key_rail', (0, 1200, 3800, 2700, 0.5), [
        (1600, 2600, 'Ohio River and wharf inside one block'), (300, 2130, 'printed KEY box'), (2750, 2250, 'lines along tracks'), (3300, 1600, 'lines along tracks')]),
           ('gasometers', (6200, 4300, 3800, 1800, 0.5), [
        (8130, 4640, 'side bent round gasometers'), (7480, 5100, 'gasometer'), (8150, 5600, 'gasometer'), (9300, 5080, 'line inside Augusta St'), (6650, 4720, 'Maiden Lane: one side only')])],
    '53': [('railfan_viaduct', (5600, 1400, 3800, 2700, 0.5), [
        (6950, 2750, 'rail fan: lines along tracks'), (6250, 2300, 'line along tracks'), (8300, 2750, 'merged across viaduct'), (6600, 2780, 'one lot outlined as block'), (7900, 3350, 'small piece')])],
    '26A': [('river_rail_stubs', (2400, 3100, 3800, 2700, 0.5), [
        (5400, 4200, 'river and wharf called block'), (4700, 4300, 'lines along tracks'), (3270, 5200, 'stub streets not cut'), (3800, 4550, 'side at a skew, orange')])],
    '64A': [('hillside_streets', (500, 2900, 3800, 2700, 0.5), [
        (2600, 3450, 'street not cut'), (3500, 3250, 'street not cut'), (1900, 4850, 'viaduct not cut'), (1000, 4550, 'line along railway')])],
    '2': [('riverfront', (3400, 4200, 3800, 2700, 0.5), [
        (5450, 6100, 'merged across Elm St'), (7000, 6100, 'merged across Race St'), (5100, 4980, 'lines along tracks'), (6000, 4450, 'freight depot wall'), (4500, 4900, 'yard ground: fragments')])],
    '10': [('downtown_alleys', (4400, 1400, 3800, 2700, 0.5), [
        (5940, 2300, 'Dupont Alley missed'), (7060, 2260, 'Lubke Alley missed'), (6250, 2880, 'Kirby Alley missed'), (7800, 1950, 'alley cut part way'), (6400, 2620, 'broken side')])],
    '66': [('residential_200ft', (3900, 400, 2400, 4500, 0.42), [
        (4350, 2650, 'alleys inside block missed'), (5720, 2700, 'lot or drive lines kept'), (5470, 3800, 'stub street found (right)'), (4500, 1400, 'coloured band: no line (right)')])],
    '52': [('mount_adams', (3000, 0, 3800, 2700, 0.5), [
        (4600, 2020, 'Wood Steps not cut'), (4450, 650, 'incline not cut'), (3700, 1100, 'street cut one side only')])],
    '3': [('rail_yard', (3500, 1800, 3800, 2700, 0.5), [
        (5000, 2700, 'yard: lines along tracks'), (5250, 2400, 'spurious small blocks'), (4600, 3200, 'yard fragments'), (5800, 3350, 'yard fragments')])],
    '1A': [('parkway_alley', (0, 900, 3000, 2200, 0.63), [
        (720, 2000, 'parkway median called block'), (2420, 2250, 'alley not cut')])],
    '8B': [('inset', (0, 0, 1800, 1300, 1.0), [(932, 522, 'merged across Clayers Alley'), (764, 690, 'Clinton Ct missed'), (708, 205, 'side dropped at numbers')])],
    '54B': [('inset', (0, 0, 2600, 1400, 0.73), [(830, 410, 'spills into Alma St: side missing'), (1540, 125, 'side dropped under big "56"'), (1300, 760, 'spills into Pueblo St')])],
    '44': [('creek_canal_rail', (5600, 3500, 5168, 3500, 0.37), [
        (7950, 4320, 'creek bank lines'), (6600, 4300, 'creek called block'), (7400, 4900, 'lines along railway'), (7050, 5930, 'canal bank line'), (8800, 4250, 'creek bank')]),
           ('alleys_streets', (500, 300, 4400, 3000, 0.43), [
        (2700, 900, 'merged across alleys'), (1900, 1300, 'merged across Ingot St'), (3150, 1500, 'merged across alleys'), (4400, 1000, 'broken side')])],
}

only = sys.argv[1] if len(sys.argv) > 1 else None
os.makedirs(os.path.join(HERE, 'annotated'), exist_ok=True)
for n, crops in CROPS.items():
    if only and n != only: continue
    D = load(n); EX = []
    if n == '44':
        for l in json.load(open(SP + 'streetmap/22-44.json', encoding='utf8'))['lines']: EX.append((l['a'], l['b'], (255, 0, 255), 9 if l['kind'] != 'sheet_edge' else 3))
    for tag, (x0, y0, w, h, s), marks in crops:
        im = draw(D, x0, y0, w, h, s, grid=500 if s >= 0.4 else 1000, marks=marks, extra=[(a, b, c, t * s) for a, b, c, t in EX])
        f = os.path.join(HERE, 'annotated', f'{n}_{tag}.jpg'); cv2.imwrite(f, im, [cv2.IMWRITE_JPEG_QUALITY, 88]); print(f, im.shape)
