"""Folds for blockfix (fix_block_a, 26 Nov 2026). The dev windows are split BY PLATE into two folds, fixed before any
tuning. Block crops: fold A = plates 3, 30, 26A, 74, 49 (DB01-05, DB16-19, DB24-27, DB32-34, DB38-41: 20 crops; 5 at
100 ft, 11 at 200 ft, 4 at 400 ft); fold B = plates 54A, 12, 19, 64A, 60B, 93A, 48 (25 crops; 10 / 11 / 4).
Ditto crops (dev_ditto) and T1-T7 are used as no-harm checks; their plates get the fold of the same plate when it has one,
else the fold below (alternating by sorted plate name, decided here once)."""
FOLD_A = {'3', '30', '26A', '74', '49'}
FOLD_B = {'54A', '12', '19', '64A', '60B', '93A', '48'}
# plates of the ditto set and T1-T7 that are in neither block fold
EXTRA_A = {'2', '57', '86', '90', '44', '5'}
EXTRA_B = {'4', '1A', '47', '94'}


def fold_of(plate):
    if plate in FOLD_A or plate in EXTRA_A: return 'A'
    if plate in FOLD_B or plate in EXTRA_B: return 'B'
    return None
