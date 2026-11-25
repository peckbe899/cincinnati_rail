# train_v2: the second blank-guide pair

Made 2026-11-24 15:31:20, 4000 iterations per network. 44: mean over the 6 tile grids of bench44 with the merged outline step (eval_v2.py); paired gain = this pair minus area_ng1 + lines_ng1, grid by grid. 44 was never used to choose a checkpoint. 1A region: the ground right of Elm Street (train_v2/1A/valmask.png). It is NOT a test: the checkpoints were chosen on it, the pseudo-label thresholds were tuned on the whole of 1A, and it holds 9 of Ben's blocks (one block moves its PQ by about 0.1). Ben's 1A lines started from the batch's, so the baseline starts ahead there.

| step | variant | seed | area best it / val IoU street | lines best it / val F1 | 44 PQ (sd over grids) | 44 paired gain PQ (grids up) | 44 recall | 44 precision | 44 merges | 44 fp | 1A region PQ (not a test) | 1A recall | 1A precision |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| baseline | baseline (area_ng1 + lines_ng1) | - | - / - | - / - | 0.511 (0.029) | 0.000 (0/6) | 0.626 | 0.833 | 12.2 | 10.8 | 0.093 | 0.663 | 0.887 |
| V1S1 | V1 | 1 | 3500 / 0.869 | 3750 / 0.766 | 0.368 (0.026) | -0.142 (0/6) | 0.458 | 0.633 | 12.7 | 22.2 | 0.104 | 0.700 | 0.884 |
| V2S1 | V2 | 1 | 3000 / 0.876 | 3750 / 0.787 | 0.438 (0.013) | -0.072 (0/6) | 0.395 | 0.711 | 9.8 | 18.5 | 0.256 | 0.629 | 0.922 |
| V1S2 | V1 | 2 | 3500 / 0.912 | 4000 / 0.768 | 0.470 (0.019) | -0.040 (1/6) | 0.531 | 0.678 | 10.3 | 13.7 | 0.356 | 0.734 | 0.965 |
| V2S2 | V2 | 2 | 3000 / 0.925 | 3000 / 0.760 | 0.482 (0.010) | -0.028 (1/6) | 0.612 | 0.779 | 12.0 | 18.2 | 0.263 | 0.767 | 0.957 |

| variant | seeds | 44 PQ mean | 44 PQ by seed (min, max) | paired gain mean | 1A region PQ mean |
|---|---|---|---|---|---|
| V1 | 2 | 0.419 | 0.368, 0.470 | -0.091 | 0.230 |
| V2 | 2 | 0.460 | 0.438, 0.482 | -0.050 | 0.260 |

## The rule's decision (written down before the run; see train_v2.py)

- noise (largest seed-to-seed spread of 44 PQ): 0.1021
- V2 minus V1 by seed: [0.07, 0.0118] -> V1 (V2 does not beat V1 for both seeds by more than the noise on average: V1, the simpler)
- V1 paired gain over area_ng1 + lines_ng1 by seed: [-0.1421, -0.0401] -> does not ship (V1 does not beat area_ng1 + lines_ng1 on 44 for both seeds by more than the noise on average: the batch pair stays)
- the pair: area_ng1 + lines_ng1 (unchanged)
- 44 chose between V1, V2 and keeping the batch pair, so the shipped pair's 44 numbers are a little optimistic; plate 90, once Ben has checked its lines, is the untouched check
