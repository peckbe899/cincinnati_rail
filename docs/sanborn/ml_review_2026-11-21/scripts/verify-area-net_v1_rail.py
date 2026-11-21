import cv2, numpy as np, json
U = 'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn/unet_data/'
SP = 'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn/'
OUT = 'C:/Users/peckb/AppData/Local/Temp/claude/8945a8e3044b4e4c/2a2bcb12-80e8-4366-9a59-3be15cce3445/scratchpad/ml_review/verify-area-net/'
lab = cv2.imread(U+'44_label.png',0); h,w = lab.shape
g = cv2.imread(U+'44_guide.png'); rough = g[:,:,0] > 127   # BGR read: channel 0 written = rough*255 -> B
p = cv2.imread(U+'44_pred_area_ng1.png',0) > 127
pe = cv2.imread(U+'44_pred_edge_v1.png',0) > 127
alpha = cv2.resize(np.load(SP+'cufp/44/png_alpha_s4.npy').astype(np.float32),(w,h)) > 0.5
d = json.load(open(SP+'picks22_guided/22-44/rail_ben.json',encoding='utf8'))
R = np.zeros((h,w),np.uint8)
for t in d['tracks']:
    if t['kind'] != 'railroad': continue
    cv2.polylines(R,[(np.array(t['pts'],float)/2).round().astype(np.int32)],False,1,1)
sm = json.load(open(SP+'streetmap/22-44.json',encoding='utf8'))
B = np.zeros((h,w),np.uint8)
for b in sm['blocks']: cv2.fillPoly(B,[(np.array(b['ring'])/2).round().astype(np.int32)],1)
print('Ben blocks share of paper', round(float(B[alpha].mean()),3), ' label block share of paper', round(float((lab[alpha]==1).mean()),3))
m = lab != 255; gt = lab == 1; err = m & (p != gt); erre = m & (pe != gt)
print('area_ng1 acc', round(1-err.sum()/m.sum(),4), 'edge_v1 stored acc', round(1-erre.sum()/m.sum(),4))
dr = cv2.distanceTransform((R==0).astype(np.uint8), cv2.DIST_L2, 3)
for rad in (10,20,30):
    z = (dr<=rad) & (B==0) & alpha
    zm = z & m
    print(f'rad {rad}: px {int(z.sum())}; label block {float((lab[z]==1).mean()):.3f} street {float((lab[z]==0).mean()):.3f} ign {float((lab[z]==255).mean()):.3f}; rough parcels {float(rough[z].mean()):.3f}; ng1 block {float(p[z].mean()):.3f}; ev1 block {float(pe[z].mean()):.3f}; share of ng1 errors {err[z].sum()/err.sum():.3f}; acc w/o {1-(err&~zm).sum()/(m&~zm).sum():.4f}; share of edge_v1 errs {erre[z].sum()/erre.sum():.3f}')
# where are the remaining errors
z = (dr<=20)&(B==0)
print('errors inside Ben blocks share', round(float(err[B>0].sum()/err.sum()),3), 'outside Ben blocks & >20 from rail', round(float(err[(B==0)&~z].sum()/err.sum()),3))
# error type in rail band
zm = z & m
print('in band: label block & pred street', int((zm & gt & ~p).sum()), 'label street & pred block', int((zm & ~gt & p).sum()))
# visual: rail band on the image
img = cv2.imread(U+'44_img.jpg')
vis = (img*0.6).astype(np.uint8)
vis[(lab==1)] = (vis[(lab==1)]*0.6 + np.array([0,120,0])*0.4).astype(np.uint8)
vis[B>0] = (vis[B>0]*0.7 + np.array([120,0,0])*0.3).astype(np.uint8)
vis[R>0] = (0,0,255)
cv2.imwrite(OUT+'44_rail_label.jpg', cv2.resize(vis,(w//3,h//3),interpolation=cv2.INTER_AREA), [cv2.IMWRITE_JPEG_QUALITY,85])
