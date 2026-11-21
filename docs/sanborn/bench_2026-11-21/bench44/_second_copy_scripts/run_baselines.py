"""bench44: the baselines of the plate-44 benchmark (21 November 2026).

    python run_baselines.py [--reuse]      -> baselines.json (and runs/<tag>/ for each)

Runs bench44.py on:
  batch                  area_ng1 + lines_ng1, the batch's own maps (the benchmark to beat)
  guided                 edge_v1 + lines_v2, the guided chain (the stored picks22_guided/22-44/outlines.json)
  ub_benarea+batchlines  Ben's blocks as the area map (make_oracle_maps.py) + the batch line map
  ub_batcharea+benlines  the batch area map + Ben's lines as the line map
  ub_benarea+benlines    both from Ben: what the outline step and step 4 lose on their own
and puts their headline numbers and the batch chain's step-by-step loss side by side.
"""
import json, os, subprocess, sys, time
HERE = os.path.dirname(os.path.abspath(__file__)).replace('\\', '/') + '/'
U = 'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn/unet_data/'
RUNS = [('batch', U + '44_pred_area_ng1.png', U + '44_lines_lines_ng1.png'),
        ('guided', U + '44_pred_edge_v1.png', U + '44_lines_lines_v2.png'),
        ('ub_benarea+batchlines', HERE + 'maps/44_area_benblocks.png', U + '44_lines_lines_ng1.png'),
        ('ub_batcharea+benlines', U + '44_pred_area_ng1.png', HERE + 'maps/44_lines_benlines.png'),
        ('ub_benarea+benlines', HERE + 'maps/44_area_benblocks.png', HERE + 'maps/44_lines_benlines.png')]

if __name__ == '__main__':
    if not os.path.exists(HERE + 'maps/44_lines_benlines.png'):
        subprocess.run([sys.executable, HERE + 'make_oracle_maps.py'], check=True)
    out = {}
    for tag, area, lines in RUNS:
        t0 = time.time()
        r = subprocess.run([sys.executable, HERE + 'bench44.py', '--tag', tag, '--area', area, '--lines', lines] + (['--reuse'] if '--reuse' in sys.argv else []), capture_output=True, text=True, encoding='utf8', errors='replace')
        if r.returncode: sys.exit(tag + ' failed:\n' + r.stderr[-3000:])
        d = json.loads(r.stdout); out[tag] = dict(headline=d['headline'], stages={k: dict(PQ=v.get('blocks', {}).get('all', {}).get('PQ'), PQ_decided=v.get('blocks_decided', {}).get('all', {}).get('PQ'),
                                                                                         recall_interior=v['lines']['all']['recall_interior'], precision=v['lines']['all']['precision'],
                                                                                         recall_interior_8px=v['lines']['all']['tol_sensitivity']['8px']['recall_interior'], precision_8px=v['lines']['all']['tol_sensitivity']['8px']['precision'])
                                                                                  for k, v in d['stages'].items()},
                                                  blocks=d['blocks'], closure={k: dict(faces=v['faces'], closed=v['closure']['all']['ben_blocks_closed_iou80'], PQ=v['blocks_from_faces']['all']['PQ']) for k, v in d['closure']['faces'].items()},
                                                  rings=d['closure']['outline_rings']['all'], on_print=d['on_print'], workload=d['workload']['all'], sheet=d['sheet']['all'], seconds=round(time.time() - t0, 1), outline_step_seconds=d['meta']['outline_step_seconds'])
        h = d['headline']
        print(f"{tag:24s} PQ {h['all']['PQ']:.3f} (A {h['A']['PQ']:.3f} B {h['B']['PQ']:.3f}) decided {h['all']['PQ_decided']:.3f} | matched {h['all']['matched']} merges {h['all']['merges']} fp {h['all']['fp']} | "
              f"lines R {h['all']['recall_interior']:.3f} P {h['all']['precision']:.3f} green {h['all']['precision_green']} orange {h['all']['precision_orange']} | closed {h['all']['ben_blocks_closed']} rings {h['all']['intact_rings']} | "
              f"delete {h['all']['delete_len']} draw {h['all']['draw_len']} | {time.time() - t0:.0f} s", flush=True)
    json.dump(out, open(HERE + 'baselines.json', 'w', encoding='utf8', newline='\n'), indent=1)
