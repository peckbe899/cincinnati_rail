exec(open('c2_common.py').read())
SP = 'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn/'
full = cv2.imread(SP + 'cufp/22-44.jpg'); H, W = full.shape[:2]
direct = cv2.resize(full, (W // 2, H // 2), interpolation=cv2.INTER_AREA)[:, :, ::-1]     # what blocks_noguide.py:38-39 feeds
stored = img                                                                              # 44_img.jpg (make_labels.py:28 then JPEG q92 at :307)
print('shapes', direct.shape, stored.shape, 'mean |diff|', round(float(np.abs(direct.astype(int) - stored.astype(int)).mean()), 3), 'p99', np.percentile(np.abs(direct.astype(int) - stored.astype(int)), 99))
z = np.zeros(direct.shape[:2], np.uint8); Xd = np.dstack([direct, z, z])
with torch.no_grad():
    for (yy, xx) in [(1280, 2560), (640, 1280)]:
        a = F.softmax(net(norm(X[None, yy:yy + 768, xx:xx + 768]))[:, :2], 1)[0, 1].numpy()
        b = F.softmax(net(norm(Xd[None, yy:yy + 768, xx:xx + 768]))[:, :2], 1)[0, 1].numpy()
        print(f'tile {yy},{xx}: jpg vs direct resize mean|dP| {np.abs(a - b).mean():.4f} flips {((a > .5) != (b > .5)).mean():.4f}')
