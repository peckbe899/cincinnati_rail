exec(open('v5_cpu.py').read().split("t0 = time.time()\n# (a)")[0])
full = cv2.imread(SP + 'cufp/22-44.jpg'); H, W = full.shape[:2]
d = cv2.resize(full, (W // 2, H // 2), interpolation=cv2.INTER_AREA)[:, :, ::-1]
diff = np.abs(d.astype(int) - img.astype(int)); print('shape', d.shape, img.shape, 'mean |diff| %.3f p99 %.1f' % (diff.mean(), np.percentile(diff, 99)))
ok, enc = cv2.imencode('.jpg', d[:, :, ::-1].copy(), [cv2.IMWRITE_JPEG_QUALITY, 92]); rt = cv2.imdecode(enc, 1)[:, :, ::-1]
print('round-trip equals stored N_img.jpg exactly:', bool((rt == img).all()), 'max diff', int(np.abs(rt.astype(int)-img.astype(int)).max()))
Xd = np.dstack([d, z, z])
for yy, xx in [(1900, 1000), (300, 4200), (2600, 2200)]:
    a = P(X[yy:yy+768, xx:xx+768]); b = P(Xd[yy:yy+768, xx:xx+768])
    print(f'tile {yy},{xx}: mean|dP| {np.abs(a-b).mean():.4f} flips {((a>.5)!=(b>.5)).mean():.4f}')
