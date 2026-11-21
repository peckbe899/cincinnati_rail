"""Montage of the 'after' (bottom) panels of thumbs/N_VARIANT.jpg, 4 per image, for the eye check.
    python montage_after.py VARIANT OUTNAME N [N ...]   -> thumbs/OUTNAME_k.jpg"""
import sys, cv2, numpy as np
import os; HERE = os.path.dirname(os.path.abspath(__file__)) + os.sep
v, name, pl = sys.argv[1], sys.argv[2], sys.argv[3:]
tiles = []
for n in pl:
    im = cv2.imread(HERE + f'thumbs/{n}_{v}.jpg'); h = im.shape[0]
    bot = im[(h + 6) // 2:]; bot = cv2.resize(bot, (780, int(bot.shape[0] * 780 / bot.shape[1])), interpolation=cv2.INTER_AREA)
    tiles.append(bot)
H = max(t.shape[0] for t in tiles)
tiles = [np.pad(t, ((0, H - t.shape[0]), (0, 0), (0, 0)), constant_values=255) for t in tiles]
for k in range(0, len(tiles), 4):
    ts = tiles[k:k + 4] + [np.full_like(tiles[0], 255)] * (4 - len(tiles[k:k + 4]))
    cv2.imwrite(HERE + f'thumbs/{name}_{k // 4}.jpg', np.vstack([np.hstack(ts[:2]), np.hstack(ts[2:])]), [cv2.IMWRITE_JPEG_QUALITY, 85])
print('ok')
