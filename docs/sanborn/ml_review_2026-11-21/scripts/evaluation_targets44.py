"""How well do the validation targets on 44 (what training watched) agree with Ben's checked map?"""
import json, numpy as np, cv2, evallib as E
T = E.truth('44'); W, H = T['size']
ben_all = [(l['a'], l['b']) for l in T['lines']]; ben_in = [(l['a'], l['b']) for l in T['lines'] if l['kind'] != 'sheet_edge']
res = {}
v = json.load(open(E.U + '44_verified.json'))
for tol in (4.0, 8.0):
    a = E.line_scores(v, ben_all, tol); b = E.line_scores(v, ben_in, tol)
    res[f'verified_json_tol{int(tol)}'] = dict(precision_vs_ben_all=a['precision'], recall_ben_interior=b['recall'], recall_ben_all=a['recall'], verified_len=a['pred_len'])
ed = E.clean(json.load(open(E.U + '44_edges.json', encoding='utf8')))
for st in ('green', 'blue', 'grey', 'orange'):
    s = [(e['a'], e['b']) for e in ed if e['state'] == st]
    if s: r = E.line_scores(s, ben_all, 4.0); res[f'edges_json_{st}_tol4'] = dict(n=len(s), precision=r['precision'], length=r['pred_len'])
r = E.line_scores([(e['a'], e['b']) for e in ed], ben_all, 4.0); res['edges_json_all_tol4'] = dict(precision=r['precision'], recall=r['recall'])
# the verified target as edgenet draws it (3 px) vs Ben's lines drawn 3 px: pixel overlap
def draw(segs, w=3):
    m = np.zeros((H, W), np.uint8)
    for a, b in segs: cv2.line(m, tuple(np.round(a).astype(int)), tuple(np.round(b).astype(int)), 1, w)
    return m > 0
tv = draw(v); tb = draw(ben_all); res['edgenet_target_px'] = int(tv.sum()); res['ben_lines_px_3wide'] = int(tb.sum())
res['target_px_on_ben_within3'] = round(float((cv2.distanceTransform((~tb).astype(np.uint8), cv2.DIST_L2, 5)[tv] <= 3).mean()), 4)
# area label vs Ben's blocks (half size)
lab = cv2.imread(E.U + '44_label.png', 0); h, w = lab.shape
tbk = np.zeros((h, w), np.uint8)
for b in T['blocks']: cv2.fillPoly(tbk, [(np.array(b['ring']) / 2).round().astype(np.int32)], 1)
alpha = cv2.resize(np.load(E.SP + 'cufp/44/png_alpha_s4.npy').astype(np.float32), (w, h)) > 0.5
sc = (lab != 255)
res['label'] = dict(scored_share_of_paper=round(float(sc[alpha].mean()), 4), label_agrees_with_ben_on_scored=round(float(((lab == 1) == (tbk == 1))[sc].mean()), 4),
                    label_street_that_ben_calls_block=int(((lab == 0) & (tbk == 1)).sum()), label_block_that_ben_calls_not_block=int(((lab == 1) & (tbk == 0)).sum()),
                    ben_block_share_of_paper=round(float(tbk[alpha].mean()), 4))
# where is the ignored ground? share of ignored pixels within 10 px (half size) of a Ben line
bl = np.zeros((h, w), np.uint8)
for a, b in ben_all: cv2.line(bl, tuple((np.array(a) / 2).round().astype(int)), tuple((np.array(b) / 2).round().astype(int)), 1, 1)
d = cv2.distanceTransform((bl == 0).astype(np.uint8), cv2.DIST_L2, 5)
ign = (lab == 255) & alpha
res['label']['ignored_within_5px_halfsize_of_ben_line'] = round(float((d[ign] <= 5).mean()), 4)
res['label']['ben_line_px_halfsize_that_are_ignored'] = round(float(ign[bl == 1].mean()), 4)
# edge target as unet.py sees it (N_edge.png)
e = cv2.imread(E.U + '44_edge.png', 0) > 0
res['edge_png_px_within2_of_ben'] = round(float((d[e] <= 2).mean()), 4)
print(json.dumps(res, indent=1)); json.dump(res, open('out/targets44.json', 'w'), indent=1)
