"""bench44: the 'cheap upper bound' maps of plate 44, made from Ben's street map (21 November 2026).

    python make_oracle_maps.py        -> maps/44_area_benblocks.png, maps/44_lines_benlines.png

maps/44_area_benblocks.png  half size (as N_pred_*.png): 255 inside Ben's 55 blocks, 0 on the street ground he decided
                            (bench44.py's decided ground), and the batch's area_ng1 value on ground he did not decide.
                            = a perfect area network wherever there is truth to be perfect against.
maps/44_lines_benlines.png  full size (as N_lines_*.png): every line of his (printed, drawn, sheet_edge) drawn 5 px
                            wide at 255 and blurred (Gaussian 5x5): P > 0.5 about 7 px across, against about 6 px for
                            the batch line map on his printed lines; the peak is on his line, for outlines.py's slide
                            onto the ridge.
"""
import os, sys
import numpy as np
import cv2
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bench44 as B  # noqa: E402

if __name__ == '__main__':
    T = B.load_truth(); os.makedirs(B.HERE + 'maps', exist_ok=True)
    pa = cv2.imread(B.U + '44_pred_area_ng1.png', 0); h, w = pa.shape
    gt = cv2.resize(T['gt'].astype(np.float32), (w, h), interpolation=cv2.INTER_NEAREST) > 0
    dec = cv2.resize(T['decided'].astype(np.uint8), (w, h), interpolation=cv2.INTER_NEAREST) > 0
    area = pa.copy(); area[dec] = 0; area[gt] = 255
    cv2.imwrite(B.HERE + 'maps/44_area_benblocks.png', area)
    ln = np.zeros((B.H, B.W), np.uint8)
    for a, b, k in T['lines']:
        cv2.line(ln, tuple(int(v) for v in np.round(a)), tuple(int(v) for v in np.round(b)), 255, 5, cv2.LINE_AA)
    ln = cv2.GaussianBlur(ln, (5, 5), 0)
    cv2.imwrite(B.HERE + 'maps/44_lines_benlines.png', ln)
    q = ln > 127; dt = cv2.distanceTransform(q.astype(np.uint8), cv2.DIST_L2, 5); r = (dt >= cv2.dilate(dt, np.ones((3, 3)))) & q
    print('area map', area.shape, 'block share %.3f' % (area > 127).mean(), '| line map', ln.shape, 'line share %.4f' % q.mean(), 'ridge width ~%.1f px' % (2 * np.median(dt[r])))
