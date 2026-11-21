import cv2, numpy as np, json
U = 'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn/unet_data/'
SP = 'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn/'
d = json.load(open(SP+'streetmap/22-44.json',encoding='utf8'))
lab = cv2.imread(U+'44_label.png',0); h,w = lab.shape
alpha = cv2.resize(np.load(SP+'cufp/44/png_alpha_s4.npy').astype(np.float32),(w,h))>0.5
print('size', d['size'], 'half', (h,w))
B = np.zeros((h,w),np.uint8)
for b in d['blocks']:
    cv2.fillPoly(B,[(np.array(b['ring'])/2).round().astype(np.int32)],1)
L = np.zeros((h,w),np.uint8)
for l in d['lines']:
    if l['kind'] in ('printed','drawn'):
        cv2.line(L, tuple((np.array(l['a'])/2).round().astype(int)), tuple((np.array(l['b'])/2).round().astype(int)), 1, 1)
Lall = np.zeros((h,w),np.uint8)
for l in d['lines']:
    cv2.line(Lall, tuple((np.array(l['a'])/2).round().astype(int)), tuple((np.array(l['b'])/2).round().astype(int)), 1, 1)
k = np.ones((7,7),np.uint8)
Bin = cv2.erode(B,k)>0            # block interior, 3 half-px in from Ben's sides
dl = cv2.distanceTransform((Lall==0).astype(np.uint8),cv2.DIST_L2,3)
# street proxy: on paper, outside Ben's closed blocks, 3..30 half-px from a Ben line
S = alpha & (B==0) & (dl>3) & (dl<30)
print('Ben blocks cover', round(float(B[alpha].mean()),3), 'of paper; label block share of paper', round(float((lab[alpha]==1).mean()),3))
print('label inside Ben blocks (interior): block', round(float((lab[Bin]==1).mean()),4), 'street', round(float((lab[Bin]==0).mean()),4), 'ignore', round(float((lab[Bin]==255).mean()),4))
print('label in street proxy: block', round(float((lab[S]==1).mean()),4), 'street', round(float((lab[S]==0).mean()),4), 'ignore', round(float((lab[S]==255).mean()),4))
lb = (lab==1)
print('label block px outside Ben blocks (on paper) share of label block', round(float((lb & (B==0) & alpha).sum()/lb.sum()),4))
for m in ['area_ng1','edge_v1']:
    p = cv2.imread(U+f'44_pred_{m}.png',0)>127
    bnd = cv2.morphologyEx(p.astype(np.uint8),cv2.MORPH_GRADIENT,np.ones((3,3),np.uint8))>0
    db = cv2.distanceTransform((~bnd).astype(np.uint8),cv2.DIST_L2,3)
    on = L>0
    res = {f'within{t}': round(float((db[on]<=t).mean()),4) for t in (1.5,3,6)}
    print(m, 'Ben block interior called block', round(float(p[Bin].mean()),4), '| street proxy called street', round(float((~p[S]).mean()),4), '| Ben printed/drawn line length with predicted boundary', res)
    # spurious boundary: predicted boundary pixels inside Ben block interior far from any line
    far = Bin & (dl>10)
    print('    predicted boundary px inside Ben blocks >10 half-px from his lines', int((bnd & far).sum()), 'vs on/near lines', int((bnd & (dl<=3)).sum()))
# label's own boundary vs Ben lines
lab_e = cv2.imread(U+'44_edge.png',0)>0
dlab = cv2.distanceTransform((~lab_e).astype(np.uint8),cv2.DIST_L2,3)
print('verified edge (N_edge.png) covers Ben printed/drawn length within 3 half-px:', round(float((dlab[L>0]<=3).mean()),4))
print('verified edge px within 3 half-px of a Ben line (precision of N_edge):', round(float((dl[lab_e]<=3).mean()),4))
