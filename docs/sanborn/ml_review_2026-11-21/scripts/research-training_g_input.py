# read-only CPU check: area_ng1 on plate 44 fed the way blocks_noguide.py feeds it (fresh INTER_AREA half-size, no JPEG) vs N_img.jpg (training path)
import sys, json, torch, numpy as np, cv2
torch.set_num_threads(8)
sys.argv = ['x', '--no-guide']
sys.path.insert(0, r'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/tools/sanborn/unet'); sys.path.insert(0, r'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/tools/sanborn')
import unet as A
net = A.UNet(); net.load_state_dict(torch.load(A.DATA + 'models/area_ng1.pt', map_location='cpu', weights_only=False)); net.eval()
img, lab = A.load('44'); wm, et = A.load_edge('44', lab)
full = cv2.imread(A._ws.DATA + 'cufp/22-44.jpg'); H, W = full.shape[:2]; im2 = cv2.resize(full, (W // 2, H // 2), interpolation=cv2.INTER_AREA)
print('shapes', img.shape, im2.shape, 'mean |rgb diff|', round(float(np.abs(img[:, :, :3].astype(np.float32) - im2[:, :, ::-1]).mean()), 2))
z = np.zeros(im2.shape[:2], np.uint8); p2 = A.predict_full(net, torch.device('cpu'), np.dstack([im2[:, :, ::-1], z, z]))
saved = cv2.imread(A.DATA + '44_pred_area_ng1.png', 0).astype(np.float32) / 255
print('blocks_noguide input path:', json.dumps(A.score(p2, lab, et, A.predict_full.edge)))
print('training input path (saved):', json.dumps(A.score(saved, lab, et)))
print('share of pixels whose block/street call differs', round(float(((p2 > 0.5) != (saved > 0.5)).mean()), 5))
