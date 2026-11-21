"""merge/v-eye: which exported lines the merged step loses (and adds) against batch, A and B, per plate (21 Nov 2026).

    python -B lost.py [N ...]     -> merge/v-eye/lost.json

A side of variant X is 'lost' when less than half its length lies within TOL px of a line the merged step exports
(staged step 4). Its cause is what the merged step has there instead (by the side's majority, TOL px): a merged side
dropped 'on rail', 'not on a line', 'paper_edge' (off the map ground or along the paper edge / furniture), 'short', or
'nothing' (no merged side at all: the merged blocks differ there). 'gained' is the same test the other way.
On 44 every side is also scored against Ben's street map (streetmap/22-44.json lines, within TOL px): 'on_ben' share.
"""
import json, os, sys
import numpy as np
import cv2
import common as C
import views as V
TOL = 8


def draw(shape, sides, val=1, img=None, w=2 * TOL + 1):
    m = np.zeros(shape, np.uint8) if img is None else img
    for s in sides: cv2.line(m, tuple(np.round(s['a']).astype(int).tolist()), tuple(np.round(s['b']).astype(int).tolist()), val, w)
    return m


def share(m, s):
    a, b = np.array(s['a'], float), np.array(s['b'], float); L = np.hypot(*(b - a)); t = np.linspace(0, 1, max(2, int(L / 4)))
    q = np.round(a + np.outer(t, b - a)).astype(int); q[:, 0] = q[:, 0].clip(0, m.shape[1] - 1); q[:, 1] = q[:, 1].clip(0, m.shape[0] - 1)
    return m[q[:, 1], q[:, 0]]


def L(s): return float(np.hypot(s['b'][0] - s['a'][0], s['b'][1] - s['a'][1]))


def one(n):
    full = V.scan(n); H, W = full.shape[:2]; P = {v: json.load(open(V.src(n, v), encoding='utf8')) for v in ('batch', 'A', 'B', 'merged')}
    EX = {v: [s for s, _ in V.exported(v, P[v])] for v in P}
    mm = draw((H, W), EX['merged'])
    # what the merged step has where it exports nothing: 1 rail, 2 not on a line, 3 paper_edge, 4 short (later wins: rail on top)
    cause = np.zeros((H, W), np.uint8)
    allm = [s for p in P['merged'] for s in p]
    draw((H, W), [s for s in allm if s['state'] == 'short'], 4, cause)
    draw((H, W), [s for s in allm if s.get('paper_edge') and s['state'] != 'short'], 3, cause)
    draw((H, W), [s for s in allm if s['state'] == 'not on a line' and not s.get('paper_edge')], 2, cause)
    draw((H, W), [s for s in allm if s['state'] == 'on rail' and not s.get('paper_edge')], 1, cause)
    names = {0: 'nothing', 1: 'on rail', 2: 'not on a line', 3: 'paper_edge', 4: 'short'}
    ben = None
    if n == '44':
        SM = json.load(open(C.DATA + 'streetmap/22-44.json', encoding='utf8')); ben = draw((H, W), SM['lines'])
    res = dict(plate=n, exported={v: dict(n=len(EX[v]), px=round(sum(L(s) for s in EX[v]))) for v in EX})
    if ben is not None: res['on_ben_px'] = {v: round(sum(L(s) * share(ben, s).mean() for s in EX[v])) for v in EX}
    for v in ('batch', 'A', 'B'):
        lost = []
        for s in EX[v]:
            f = share(mm, s).mean()
            if f < 0.5:
                c = share(cause, s); unc = share(mm, s) == 0; c = c[unc] if unc.any() else c   # the cause where the merged step shows nothing
                k = int(np.bincount(c, minlength=5).argmax())
                r = dict(a=s['a'], b=s['b'], len=round(L(s)), state=s['state'], hole=bool(s.get('hole')), cause=names[k], covered=round(float(f), 2))
                if ben is not None: r['on_ben'] = round(float(share(ben, s).mean()), 2)
                lost.append(r)
        xm = draw((H, W), EX[v]); gained = []
        for s in EX['merged']:
            f = share(xm, s).mean()
            if f < 0.5:
                r = dict(a=s['a'], b=s['b'], len=round(L(s)), state=s['state'], covered=round(float(f), 2), bridge=s.get('bridge'))
                if ben is not None: r['on_ben'] = round(float(share(ben, s).mean()), 2)
                gained.append(r)
        bycause = {}
        for r in lost: bycause.setdefault(r['cause'], [0, 0]); bycause[r['cause']][0] += 1; bycause[r['cause']][1] += r['len']
        res[v] = dict(lost_n=len(lost), lost_px=sum(r['len'] for r in lost), lost_by_cause=bycause, gained_n=len(gained), gained_px=sum(r['len'] for r in gained),
                      lost=sorted(lost, key=lambda r: -r['len']), gained=sorted(gained, key=lambda r: -r['len']))
        if ben is not None:
            res[v]['lost_on_ben_px'] = round(sum(r['len'] * r['on_ben'] for r in lost)); res[v]['gained_on_ben_px'] = round(sum(r['len'] * r['on_ben'] for r in gained))
    V._full.pop(n, None)
    return res


if __name__ == '__main__':
    pl = sys.argv[1:] or C.PLATES
    f = C.ME + 'lost.json'; R = json.load(open(f)) if os.path.exists(f) else {}
    for n in pl:
        R[n] = one(n); r = R[n]
        print(n, 'exported', {v: r['exported'][v]['px'] for v in r['exported']}, r.get('on_ben_px', ''))
        for v in ('batch', 'A', 'B'):
            print('   vs', v, 'lost', r[v]['lost_n'], r[v]['lost_px'], 'px', r[v]['lost_by_cause'], '| gained', r[v]['gained_n'], r[v]['gained_px'], 'px',
                  (f"| lost on Ben {r[v]['lost_on_ben_px']} gained on Ben {r[v]['gained_on_ben_px']}" if n == '44' else ''), flush=True)
        json.dump(R, open(C.must_be_mine(f), 'w'), indent=1)
