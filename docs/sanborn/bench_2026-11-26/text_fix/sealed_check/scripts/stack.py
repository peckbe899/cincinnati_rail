"""Stack pictures into one sheet (sealed cross-check helper). python -B stack.py OUT.png IN1.png IN2.png ... [--cols N]"""
import sys, numpy as np, cv2
a = [x for x in sys.argv[1:] if not x.startswith('--')]; cols = int(next((x.split('=')[1] for x in sys.argv if x.startswith('--cols=')), 1))
ims = [cv2.imread(p) for p in a[1:]]
rows = [ims[i:i + cols] for i in range(0, len(ims), cols)]
W = max(sum(i.shape[1] + 10 for i in r) for r in rows); H = sum(max(i.shape[0] for i in r) + 10 for r in rows)
out = np.full((H, W, 3), 255, np.uint8); y = 0
for r in rows:
    x = 0
    for i in r: out[y:y + i.shape[0], x:x + i.shape[1]] = i; x += i.shape[1] + 10
    y += max(i.shape[0] for i in r) + 10
cv2.imwrite(a[0], out); print(a[0], W, 'x', H)
