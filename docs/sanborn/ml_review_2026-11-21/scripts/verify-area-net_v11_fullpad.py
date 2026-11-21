exec(open('v5_cpu.py').read().split("t0 = time.time()\n# (a)")[0])
import json
OUTD = 'C:/Users/peckb/AppData/Local/Temp/claude/8945a8e3044b4e4c/2a2bcb12-80e8-4366-9a59-3be15cce3445/scratchpad/ml_review/verify-area-net/'
t0 = time.time(); tile, pad = 768, 192; step = tile - 2*pad; h, w = X.shape[:2]
im = cv2.copyMakeBorder(X, pad, pad+tile, pad, pad+tile, cv2.BORDER_REFLECT); out = np.zeros((h, w), np.float32)
for y in range(0, h, step):
    for x in range(0, w, step):
        p = P(im[y:y+tile, x:x+tile])[pad:pad+step, pad:pad+step]; out[y:y+step, x:x+step] = p[:min(step, h-y), :min(step, w-x)]
np.save(OUTD + '44_ng1_pad192.npy', out); print('time', round(time.time()-t0))
A = cv2.imread(U + '44_pred_area_ng1.png', 0).astype(np.float32)/255
m = lab != 255; gt = lab == 1
for nm, Q in (('stored 768/64', A), ('768/192', out)):
    pr = Q > .5; print(nm, 'acc %.4f iou_street %.4f' % ((pr[m]==gt[m]).mean(), ((~pr[m])&(~gt[m])).sum()/((~pr[m])|(~gt[m])).sum()))
print('differ', round(float(((A>.5)!=(out>.5)).mean()),4))
