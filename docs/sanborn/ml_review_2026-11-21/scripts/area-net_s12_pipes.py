import cv2, numpy as np
U = 'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn/unet_data/'
lab = cv2.imread(U+'44_label.png',0); h,w = lab.shape; p = cv2.imread(U+'44_pred_area_ng1.png',0)>127
bins = cv2.imread(U+'44_bins.png', cv2.IMREAD_UNCHANGED)
def half(mask): return cv2.resize(mask.astype(np.uint8),(w,h),interpolation=cv2.INTER_AREA)>0
pipe = half((bins==6)|(bins==7)); blkline = half(bins==1)
# predicted boundary pixels that lie in labelled street (street called block region edge inside the street)
bnd = cv2.morphologyEx(p.astype(np.uint8),cv2.MORPH_GRADIENT,np.ones((3,3),np.uint8))>0
ds = cv2.distanceTransform((lab!=1).astype(np.uint8),cv2.DIST_L2,3)   # distance to labelled block
inside_street = bnd & (lab==0) & (ds>4)                                  # predicted boundary >4 px into labelled street
near_pipe = cv2.dilate(pipe.astype(np.uint8),np.ones((5,5),np.uint8))>0
near_bl = cv2.dilate(blkline.astype(np.uint8),np.ones((5,5),np.uint8))>0
allb = bnd & (lab!=255)
print('pred boundary px >4px into labelled street:', int(inside_street.sum()), '| on pipe/sewer ink (+-2px):', round(float(near_pipe[inside_street].mean()),3), '| on rule block-line ink:', round(float(near_bl[inside_street].mean()),3))
print('baseline: share of all street px near pipe/sewer ink', round(float(near_pipe[lab==0].mean()),3))
