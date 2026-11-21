"""bench44: cross-check of bench44.py's block and line scores against the earlier review's own scorers (21 Nov 2026).

    python -B xcheck_review_scorers.py      -> xcheck_review_scorers.json

Block PQ: xcheck_pq44_review_copy.py (an unchanged copy of docs/sanborn/ml_review_2026-11-21/scripts/research-maps_pq44.py)
on runs/<tag>/outlines.json. Lines: the review's evaluation_evallib.py line_scores (loaded read-only from docs/, no
bytecode written) on runs/<tag>/44_shown.json, Ben's printed + drawn lines, tol 4 and 5 px, 20 degrees, 2 px step.
"""
import importlib.util, json, os, sys
sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__)).replace('\\', '/') + '/'
DOCS = 'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/docs/sanborn/ml_review_2026-11-21/scripts/'


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path); m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m


if __name__ == '__main__':
    P = load('pq44', HERE + 'xcheck_pq44_review_copy.py'); E = load('evallib', DOCS + 'evaluation_evallib.py')
    gt, ng, shape = P.gt_instances(); T = E.truth('44')
    inter = [(l['a'], l['b']) for l in T['lines'] if l['kind'] in ('printed', 'drawn')]; allb = [(l['a'], l['b']) for l in T['lines']]
    out = {}
    for tag in ('batch', 'guided', 'ub_benarea+batchlines', 'ub_batcharea+benlines', 'ub_benarea+benlines'):
        if not os.path.exists(HERE + f'runs/{tag}/bench44.json'): continue
        pr, npr = P.pred_from_outlines(HERE + f'runs/{tag}/outlines.json', shape); r = P.pq(gt, ng, pr, npr, tag)
        shown = [(e['a'], e['b']) for e in json.load(open(HERE + f'runs/{tag}/44_shown.json')) if e['state'] != 'sheet']
        d = json.load(open(HERE + f'runs/{tag}/bench44.json'))
        o = dict(review_pq44=dict(PQ=r['PQ'], tp=r['tp'], fp=r['fp'], fn=r['fn']), bench44_PQ=d['headline']['all']['PQ'], bench44_matched=d['headline']['all']['matched'], bench44_fp=d['headline']['all']['fp'])
        for tol in (4, 5):
            a = E.line_scores(shown, inter, tol=tol, ang=20, step=2.0); b = E.line_scores(shown, allb, tol=tol, ang=20, step=2.0)
            o[f'review_evallib_tol{tol}'] = dict(recall_interior=a['recall'], precision_vs_all=b['precision'])
        o['bench44_tol4'] = d['lines_shown']['all']['tol_sensitivity']['4px']; o['bench44_tol5'] = dict(recall_interior=d['lines_shown']['all']['recall_interior'], precision=d['lines_shown']['all']['precision'])
        out[tag] = o; print(tag, json.dumps(o), flush=True)
    json.dump(out, open(HERE + 'xcheck_review_scorers.json', 'w'), indent=1)
