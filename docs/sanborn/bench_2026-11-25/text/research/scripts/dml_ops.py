"""Which building blocks of the OCR models run on the AMD GPU through torch-directml (venv torch 2.4.1).
Tests forward and backward of each op on 'dml' and compares to the CPU result. Prints one line per op.
Run with the unet venv python, -B. Writes out/dml_ops.json."""
import json, os, time, warnings
import torch, torch.nn as nn, torch.nn.functional as F
import torch_directml
warnings.simplefilter('always')
dev = torch_directml.device()
torch.manual_seed(0)
O = os.path.join(os.path.dirname(__file__), '..', 'out', 'dml_ops.json')


def run(name, make, inp_shapes):
    res = {'op': name}
    try:
        m = make()
        xs = [torch.randn(*s) for s in inp_shapes]
        with warnings.catch_warnings(record=True) as w:
            mc = m
            yc = mc(*xs)
            yc = yc[0] if isinstance(yc, tuple) else yc
            md = m.to(dev) if isinstance(m, nn.Module) else m
            xd = [x.to(dev).requires_grad_(True) for x in xs]
            t = time.time()
            yd = md(*xd)
            yd = yd[0] if isinstance(yd, tuple) else yd
            yd.sum().backward()
            res['seconds'] = round(time.time() - t, 3)
            res['max_abs_diff_vs_cpu'] = float((yd.detach().cpu() - yc.detach()).abs().max())
            res['warnings'] = [str(x.message)[:160] for x in w]
        res['ok'] = res['max_abs_diff_vs_cpu'] < 1e-2
    except Exception as e:
        res['ok'] = False
        res['error'] = (type(e).__name__ + ': ' + str(e))[:300]
    print(json.dumps(res))
    return res


class Wrap(nn.Module):
    def __init__(self, f):
        super().__init__(); self.f = f
    def forward(self, *a):
        return self.f(*a)


out = []
out.append(run('conv2d+bn+relu (VGG/ResNet/U-net blocks: CRAFT, DB)', lambda: nn.Sequential(nn.Conv2d(3, 16, 3, padding=1), nn.BatchNorm2d(16).eval(), nn.ReLU()), [(2, 3, 64, 64)]))
out.append(run('bidirectional LSTM (CRNN reader: EasyOCR, docTR crnn, Tesseract-like)', lambda: nn.LSTM(64, 128, num_layers=2, bidirectional=True, batch_first=True), [(4, 40, 64)]))
out.append(run('GRU', lambda: nn.GRU(64, 128, batch_first=True), [(4, 40, 64)]))
out.append(run('multi-head attention (ViT: PARSeq, TrOCR, docTR vitstr)', lambda: Wrap(lambda x: nn.functional.scaled_dot_product_attention(x, x, x)), [(2, 4, 50, 32)]))
out.append(run('transformer encoder layer', lambda: nn.TransformerEncoderLayer(64, 4, 128, batch_first=True).eval(), [(2, 50, 64)]))
out.append(run('grid_sample bilinear (deformable attention in DETR spotters: TESTR, DeepSolo, PALETTE, Spotter-v2)', lambda: Wrap(lambda x, g: F.grid_sample(x, g.tanh(), align_corners=False)), [(2, 8, 32, 32), (2, 16, 16, 2)]))
out.append(run('ctc_loss (training a CRNN reader)', lambda: Wrap(lambda x: F.ctc_loss(x.log_softmax(2), torch.tensor([[1,2,3,4,5],[3,3,2,7,9]]), torch.full((2,), 20, dtype=torch.long), torch.full((2,), 5, dtype=torch.long))), [(20, 2, 11)]))
try:
    import torchvision.ops as tvo
    out.append(run('torchvision deform_conv2d', lambda: Wrap(lambda x, off: tvo.deform_conv2d(x, off, torch.ones(8, 8, 3, 3).to(x.device), padding=1)), [(1, 8, 16, 16), (1, 18, 16, 16)]))
    out.append(run('torchvision roi_align (Mask R-CNN: TextFuseNet, Mask TextSpotter)', lambda: Wrap(lambda x: tvo.roi_align(x, [torch.tensor([[0., 0, 0, 8, 8]]).to(x.device)[:, 1:]], 4)), [(1, 8, 16, 16)]))
except Exception as e:
    print('torchvision ops', e)

def lstm_infer():
    r = {'op': 'bidirectional LSTM, inference only (no backward)'}
    try:
        m = nn.LSTM(64, 128, num_layers=2, bidirectional=True, batch_first=True).eval()
        x = torch.randn(4, 40, 64)
        with torch.no_grad():
            yc = m(x)[0]
            yd = m.to(dev)(x.to(dev))[0]
        r['max_abs_diff_vs_cpu'] = float((yd.cpu() - yc).abs().max()); r['ok'] = r['max_abs_diff_vs_cpu'] < 1e-2
    except Exception as e:
        r['ok'] = False; r['error'] = (type(e).__name__ + ': ' + str(e))[:300]
    print(json.dumps(r)); return r
out.append(lstm_infer())
with open(O, 'w') as f:
    json.dump(out, f, indent=1)
