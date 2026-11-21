import sys, time, torch
torch.set_num_threads(6)
sys.argv = ['x', '--no-guide']   # unet.py reads NOGUIDE from argv at import
sys.path.insert(0, r'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/tools/sanborn/unet'); sys.path.insert(0, r'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/tools/sanborn')
import unet as A
net = A.UNet(); net.load_state_dict(torch.load(A.DATA + 'models/area_ng1.pt', map_location='cpu')); net.eval()
x = torch.rand(1, 5, 768, 768)
with torch.no_grad():
    for i in range(2):
        t = time.time(); net(x); print('768 tile cpu s', round(time.time() - t, 2))
print(sum(p.numel() for p in net.parameters()) / 1e6, 'M params')
