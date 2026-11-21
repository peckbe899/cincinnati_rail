import cv2, numpy as np, json
U = 'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn/unet_data/'
SP = 'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn/'
EDGE_W, EDGE_D = 6.0, 4.0
for N in ['82A','80','43','45','44']:
    lab = cv2.imread(U+f'{N}_label.png',0); img = cv2.imread(U+f'{N}_img.jpg'); g = cv2.imread(U+f'{N}_guide.png'); e = cv2.imread(U+f'{N}_edge.png',0)
    alpha = cv2.resize(np.load(SP+f'cufp/{N}/png_alpha_s4.npy').astype(np.float32),(lab.shape[1],lab.shape[0]))>0.5
    m = lab!=255
    st = (lab==0).sum(); bl=(lab==1).sum(); ig=(lab==255).sum()
    d = cv2.distanceTransform((e==0).astype(np.uint8), cv2.DIST_L2, 3)
    wm = 1+EDGE_W*np.exp(-d/EDGE_D)
    # effective weighted share: class weight 3 street, 1 block, times wm
    ws = (3*wm[lab==0]).sum(); wb=(wm[lab==1]).sum()
    print(N, 'shape img',img.shape[:2],'lab',lab.shape,'guide',g.shape[:2],'edge',e.shape, 'pix',lab.size,
          f'ignore {ig/lab.size:.3f} (on paper {((lab==255)&alpha).sum()/alpha.sum():.3f}) street/labelled {st/m.sum():.3f} block/labelled {bl/m.sum():.3f}',
          f'edge px {int((e>0).sum())} wmap>2 share of labelled {(wm[m]>2).mean():.3f} mean w street {wm[lab==0].mean():.2f} block {wm[lab==1].mean():.2f}',
          f'effective street loss share {ws/(ws+wb):.3f}', 'paper share', round(float(alpha.mean()),3), 'h%640',lab.shape[0]%640,'w%640',lab.shape[1]%640)
    # fraction of crops rejected (<20% labelled) at CROP 384
    ii = cv2.integral((m).astype(np.uint8))
    H,W = lab.shape; rng=np.random.default_rng(1); ys=rng.integers(0,H-384,20000); xs=rng.integers(0,W-384,20000)
    fr = (ii[ys+384,xs+384]-ii[ys,xs+384]-ii[ys+384,xs]+ii[ys,xs])/384**2
    print('   crops kept (>=20% labelled)', round(float((fr>=0.2).mean()),3), 'mean labelled frac in kept', round(float(fr[fr>=0.2].mean()),3))
