"""tiles.py H1 [f] [tile] [ov]: reading tiles of a held-out crop, from the scan only (no finder or words output).
Writes work/<crop>_zoom_RC.jpg at f (default 1.5) with a 50 px grid labelled in full-plate px every 100 px."""
import sys, os, json, cv2
HERE = os.path.dirname(os.path.abspath(__file__)); HO = os.path.dirname(HERE)
ROOT = 'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn'
cid = sys.argv[1]; f = float(sys.argv[2]) if len(sys.argv) > 2 else 1.5
T = int(sys.argv[3]) if len(sys.argv) > 3 else 500; OV = int(sys.argv[4]) if len(sys.argv) > 4 else 25
c = json.load(open(os.path.join(HO, 'crops.json')))[cid]; X0, Y0, X1, Y1 = c['win']
im = cv2.imread(f"{ROOT}/cufp/22-{c['plate']}.jpg")
os.makedirs(os.path.join(HO, 'work'), exist_ok=True)
for r, ty in enumerate(range(Y0, Y1, T)):
    for q, tx in enumerate(range(X0, X1, T)):
        a0, b0, a1, b1 = tx - OV, ty - OV, min(tx + T, X1) + OV, min(ty + T, Y1) + OV
        s = cv2.resize(im[b0:b1, a0:a1], None, fx=f, fy=f, interpolation=cv2.INTER_CUBIC)
        for x in range((a0 // 50 + 1) * 50, a1, 50):
            xx = int((x - a0) * f); col = (255, 90, 0) if x % 100 == 0 else (255, 200, 150)
            cv2.line(s, (xx, 0), (xx, s.shape[0]), col, 1)
            if x % 100 == 0: cv2.putText(s, str(x), (xx + 2, 12), 0, 0.4, (200, 0, 0), 1)
        for y in range((b0 // 50 + 1) * 50, b1, 50):
            yy = int((y - b0) * f); col = (255, 90, 0) if y % 100 == 0 else (255, 200, 150)
            cv2.line(s, (0, yy), (s.shape[1], yy), col, 1)
            if y % 100 == 0: cv2.putText(s, str(y), (2, yy - 2), 0, 0.4, (200, 0, 0), 1)
        # crop window edge in green
        cv2.rectangle(s, (int((X0 - a0) * f), int((Y0 - b0) * f)), (int((X1 - a0) * f), int((Y1 - b0) * f)), (0, 160, 0), 1)
        cv2.imwrite(os.path.join(HO, 'work', f'{cid}_zoom_{r}{q}.jpg'), s, [cv2.IMWRITE_JPEG_QUALITY, 93])
print('ok')
