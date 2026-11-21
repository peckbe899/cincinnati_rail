import sys, time, os
sys.argv = [sys.argv[0], '--no-guide', '--area', 'area_ng1']
sys.path.insert(0, 'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/tools/sanborn/unet')
import torch
torch.set_num_threads(6)
import edgenet as E
net = E.UNet(classes=2, in_ch=7); net.load_state_dict(torch.load(E.DATA + 'models/lines_ng1.pt', map_location='cpu', weights_only=False)); net.eval()
x = torch.rand(1, 7, 1024, 1024)
with torch.no_grad():
    t0 = time.time(); net(x); print('1024 tile', round(time.time() - t0, 2), 's')
    t0 = time.time(); net(torch.rand(1, 7, 448, 448)); print('448 tile', round(time.time() - t0, 2), 's')
print('NOGUIDE', E.NOGUIDE, 'AREA', E.AREA)
