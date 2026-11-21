"""merge/v-eye: the trouble-spot crops looked at by eye (21 Nov 2026). Full resolution, 2 x 2 (batch, A / B, merged)
unless 'only' is given. Centres come from lost.json (the longest lines lost against batch, A or B, by cause),
sides_stats.json (bridges, holes, chords) and the thumbnails (map edge of the PDF sheets, 64A's hillside streets).

    python -B crops_list.py [NAME ...]     -> merge/v-eye/crops/N_NAME.jpg
"""
import sys
import views as V

J = [  # name, plate, centre x, centre y, size, variants
    # rail-yard demotion: the longest sides the merged step drops 'on rail' where A, B or the batch had them
    ('rail_a', '90', 9060, 4148, 1000, None), ('rail_b', '90', 5896, 5757, 1000, None), ('rail_c', '90', 4020, 2041, 1000, None),
    ('rail_a', '1B', 6950, 4070, 1400, None), ('rail_b', '1B', 8850, 4080, 1400, None), ('rail_c', '1B', 9848, 4884, 1000, None),
    ('rail_d', '1B', 4684, 2882, 1000, None), ('rail_e', '1B', 3073, 2240, 1000, None),
    ('rail_a', '3', 2560, 4245, 1200, None), ('rail_b', '3', 1300, 2608, 1200, None), ('rail_c', '3', 6760, 2400, 1200, None),
    ('rail_a', '64A', 8700, 1700, 1400, None), ('rail_b', '64A', 9550, 3100, 1400, None),
    ('rail_a', '23', 8100, 5450, 1400, None), ('rail_a', '30', 4500, 1600, 1000, None),
    ('rail_a', '44', 3474, 2991, 1000, None), ('rail_a', '5', 5315, 4012, 800, None),
    # street sides along the map edge of the PDF sheets (and the masked area)
    ('edge_a', '90', 1100, 750, 1400, None), ('edge_b', '90', 6500, 6900, 1400, None), ('edge_c', '90', 1209, 1163, 800, None),
    ('edge_a', '30', 1100, 6650, 1400, None), ('edge_a', '23', 2500, 700, 1400, None), ('edge_b', '23', 5000, 7150, 1400, None),
    ('edge_a', '47', 7000, 6700, 1400, None), ('edge_a', '21', 2000, 3200, 1400, None), ('edge_b', '21', 7500, 6100, 1400, None),
    ('lost_a', '21', 6823, 1061, 1200, None), ('lost_b', '21', 4228, 5181, 1200, None),
    # others
    ('lost_a', '30', 7166, 5283, 1000, None), ('lost_a', '3', 9668, 676, 1000, None), ('lost_b', '3', 9683, 7084, 1400, None),
    ('lost_a', '60B', 873, 3918, 800, None), ('lost_b', '60B', 3776, 1654, 800, None),
    ('lost_a', '5', 2919, 6757, 800, None),
]

if __name__ == '__main__':
    want = set(sys.argv[1:])
    for name, n, cx, cy, S, only in J:
        if want and f'{n}_{name}' not in want and name not in want: continue
        print(V.crop(n, cx - S // 2, cy - S // 2, S, name, only or ('batch', 'A', 'B', 'merged')), flush=True)
