# read-only, CPU only: does area_ng1.pt load with weights_only=True; parameter count; what tensors look like
import sys, torch
sys.path.insert(0, r'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/tools/sanborn/unet'); sys.path.insert(0, r'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/tools/sanborn')
import unet as A
M = r'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn/unet_data/models/'
print('torch', torch.__version__, 'torch_directml imported?', 'torch_directml' in sys.modules)
for n in ('area_ng1', 'lines_ng1', 'edge_v1'):
    try: torch.load(M + n + '.pt', map_location='cpu', weights_only=True); print(n, 'weights_only=True OK')
    except Exception as e: print(n, 'weights_only=True FAILED:', type(e).__name__, str(e).splitlines()[0][:200])
sd = torch.load(M + 'area_ng1.pt', map_location='cpu', weights_only=False); v = next(iter(sd.values())); print('loaded weights_only=False; first tensor device', v.device, v.dtype)
print('torch_directml imported after load?', 'torch_directml' in sys.modules)
print('params area', sum(p.numel() for p in A.UNet().parameters()), 'lines', sum(p.numel() for p in A.UNet(classes=2, in_ch=7).parameters()))
import copy
net = A.UNet(); from torch.optim.swa_utils import AveragedModel, get_ema_avg_fn
ema = AveragedModel(net, device='cpu', avg_fn=get_ema_avg_fn(0.999)); ema.update_parameters(net); ema.update_parameters(net); print('AveragedModel on CPU ok, n_averaged', int(ema.n_averaged))
print('EMA weight left on the first snapshot after N updates, decay 0.999: N=1000 ->', round(0.999 ** 1000, 3), ' N=4000 ->', round(0.999 ** 4000, 3), '; decay 0.99 N=1000 ->', round(0.99 ** 1000, 6))
