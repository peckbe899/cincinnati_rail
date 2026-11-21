"""Census step 1d: the printed scale of every batch plate, as read by eye on 21 Nov 2026 (scale/notes_*.jpg), with the
georeferenced measurements (scale/measured.json) as a check.

Read: the 'SCALE ... FT. TO AN INCH' note on the uncut sheet each plate comes from (scale_find.py crops). A cut plate
(A/B halves, small cut pieces) is given its sheet's note; where a sheet carries an inset at another scale the inset is
listed separately (seen on the 1/8 sheet overviews scale/sheet_46.jpg and sheet_48.jpg).
    python scale_table.py  -> scale/scale_table.json
"""
import json, os
HERE = os.path.dirname(os.path.abspath(__file__))
R100 = '1A 1B 2 3 4 5 6 7 8A 8B 9 10 11 12 13 14 15A 15B 16 17 18A 18B 43 44 51 52 53 54A 54B 55A 55B 56 57 58 62 63'.split()
R400 = '46 47 48 49 50 92 93A 93B 94 95'.split()
R200 = ('19 20 21 22 23 24 25 26A 26B 27 28 29 30 31 32 33 34 35 36 37 38 39 40 41 42 45 59A 59B 60A 60B 61 64A 64B 65 66 67 68 69 70 '
        '71 72 73 74 75 76 77 78 79 80 81 82A 82B 83A 83B 84 85A 85B 86 87 88 89 90 91').split()
INSETS = {'46': '200-ft inset (lower left, about a third of the sheet; note read on scale/sheet_46.jpg)',
          '48': 'three 200-ft sub-plats A, B, C (lower right; notes on scale/sheet_48.jpg)',
          '78': "400-ft inset ('SCALE 1\"=400\\'', left, the Andrew Ferris estate; scale/inset78.jpg)",
          '94': '200-ft sub-plat (upper left; scale/inset94.jpg)'}
# Insets were looked for only on the sheets viewed whole (46, 48, 78, 94 and the 12 worst); a smaller-template search
# (scale_insets.py) found nothing usable, so other sheets may carry insets that are not listed.
HOW = {'57': 'note printed inside the map at the top (scale/crop57_note.jpg); the matcher missed it'}
if __name__ == '__main__':
    meas = json.load(open(HERE + '/scale/measured.json'))
    out = {}
    for ft, L in ((100, R100), (200, R200), (400, R400)):
        for n in L:
            m = meas.get(n) or meas.get(n + ' (png)') or meas.get(n.rstrip('AB')) if n not in ('1A', '1B') else meas.get(n)
            out[n] = dict(ft_per_inch=ft, status='read', how=HOW.get(n, 'sheet note, scale/notes_*.jpg' + ('' if n[-1].isdigit() else '; cut piece given its sheet\'s note')),
                          inset=INSETS.get(n, ''), measured_ft_per_inch=m['ft_per_inch'] if m else None, measured_from=os.path.basename(m['source']) if m else '')
    assert len(out) == 109, len(out)
    bad = {n: v for n, v in out.items() if v['measured_ft_per_inch'] and abs(v['measured_ft_per_inch'] / v['ft_per_inch'] - 1) > 0.1}
    json.dump(out, open(HERE + '/scale/scale_table.json', 'w'), indent=1)
    print('read 100:', len(R100), '200:', len(R200), '400:', len(R400), '| measured on', sum(bool(v['measured_ft_per_inch']) for v in out.values()), 'plates; disagree > 10%:', {n: (v['ft_per_inch'], v['measured_ft_per_inch'], v['measured_from']) for n, v in bad.items()})
