import cv2, numpy as np, json
U = 'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn/unet_data/'
SP = 'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn/'
O = 'C:/Users/peckb/AppData/Local/Temp/claude/8945a8e3044b4e4c/2a2bcb12-80e8-4366-9a59-3be15cce3445/scratchpad/ml_review/area-net/'
N='44'
img = cv2.imread(U+f'{N}_img.jpg'); lab = cv2.imread(U+f'{N}_label.png',0); p = cv2.imread(U+f'{N}_pred_area_ng1.png',0)>127
m = lab!=255; gt = lab==1
vis = (img*0.6).astype(np.uint8)
vis[m & ~gt & p] = (0,0,255)      # street called block: red
vis[m & gt & ~p] = (255,0,0)      # block called street: blue
vis[~m] = (vis[~m]*0.5).astype(np.uint8)
d = json.load(open(SP+'streetmap/22-44.json',encoding='utf8'))
for b in d['blocks']:
    cv2.polylines(vis,[(np.array(b['ring'])/2).round().astype(np.int32)],True,(0,255,0),3)
for y in range(640, vis.shape[0], 640): cv2.line(vis,(0,y),(vis.shape[1],y),(0,255,255),1)
for x in range(640, vis.shape[1], 640): cv2.line(vis,(x,0),(x,vis.shape[0]),(0,255,255),1)
cv2.imwrite(O+'44_errors.jpg', cv2.resize(vis,(vis.shape[1]//3, vis.shape[0]//3), interpolation=cv2.INTER_AREA), [cv2.IMWRITE_JPEG_QUALITY, 85])
