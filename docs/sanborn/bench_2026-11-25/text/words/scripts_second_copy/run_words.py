"""Words agent prototype, 25 Nov 2026: group a plate's character candidates into strings and words, find which way
up each string is, rectify each string into a horizontal strip, and sort the words into kinds from geometry alone.

    cd data/sanborn
    python -B bench_2026-11-25/text/words/scripts/run_words.py N [--src bins|finder] [--no-strips]

Writes (all in bench_2026-11-25/text/words/out/):
  N_words.json        every phrase (string) with its words, orientation cues, kind and the features the kind came from
  N_glyphlab.png      the glyph labels (3 x 8 bit: B low byte, G middle, R high; label = glyph index + 1)
  N_textmask.png      the ink of every word not called junk (255), for the later stages
  strips/N/pNNNNN.png the rectified strip of every phrase of 2+ glyphs (scan grey; row 0 is the text's top), and
                      pNNNNN_m.png its own ink only
Nothing in the repo is written. Rules only: nothing is trained or fitted."""
import json, os, sys, time
import numpy as np
import cv2
from scipy.spatial import cKDTree
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import wordlib as wl  # noqa: E402
import group_words as gw  # noqa: E402
import context as cx  # noqa: E402
import orient as orx  # noqa: E402

OUT = os.path.join(os.path.dirname(HERE), 'out')
BANK_FLAT = np.sin(np.deg2rad(10))   # bank phrases: within 10 degrees of horizontal
SPLIT2 = 0.03
SHAPE_MIN = 0.015                    # the shapes cue decides when its margin is at least this


def word_arcs(G, I):
    """arc positions (px along the phrase's centre line, chain order) of each glyph centre, and its half width"""
    Qs = wl.resample(I['Q'], 1.0); qt = cKDTree(Qs); s = I['g']
    _, gi = qt.query(G['c'][s]); T = np.gradient(Qs, axis=0); T /= np.maximum(np.hypot(*T.T), 1e-6)[:, None]
    hw = []
    for k, g in enumerate(s):
        a = np.arctan2(T[gi[k]][1], T[gi[k]][0]); hw.append((G['S'][g, wl.kidx(a)] + G['S'][g, wl.kidx(a + np.pi)]) / 2)
    return Qs, gi.astype(float), np.array(hw), T


def run(N, src='bins', strips=True):
    t0 = time.time()
    TAG = N if src == 'bins' else f'{N}_{src}'               # the tag of every output file
    mask, mf = gw.load_candidates(N, src)
    C = cx.load(N)
    G, info, ring, dt = gw.build(N, mask, fill_at=lambda x, y: cx.at(C, C['fill'], x, y))
    lab = G['lab']
    grey = cv2.imread(f'cufp/22-{N}.jpg', cv2.IMREAD_GRAYSCALE)
    print(f'plate {N}: grouped in {dt:.1f} s, context {C["src"]}')
    # ---------- phrase geometry and the rule orientation ----------
    for pid, I in enumerate(info):
        s = I['g']
        if (len(s) >= 2 or I.get('multi_piece')):
            d = I['Q'][-1] - I['Q'][0]; d = d / max(np.hypot(*d), 1e-6)
        else:
            d = I['d0']
        I['d'] = d
        vert = abs(d[0]) < np.sin(np.deg2rad(orx.VERT))
        I['flip_rule'] = bool(d[1] > 0) if vert else bool(d[0] < 0)
        I['vertical'] = bool(vert)
    # ---------- the shapes bank: glyphs of near-horizontal phrases, upright by the rule ----------
    bank, bank_pid = [], []
    for pid, I in enumerate(info):
        if len(I['g']) < 2 or abs(I['d'][1]) > BANK_FLAT or not (12 <= I['h'] <= 70) or I['spaced']: continue
        u = -I['d'] if I['flip_rule'] else I['d']
        for g in I['g']:
            bank.append(orx.vec(orx.patch(lab, g + 1, G['c'][g], u, I['h'], G['box'][g]))); bank_pid.append(pid)
    bank = np.array(bank, np.float32); bank_pid = np.array(bank_pid)
    print(f'  shapes bank: {len(bank)} glyphs from {len(set(bank_pid.tolist()))} near-horizontal phrases')
    half = bank_pid % 2
    # ---------- check of two-piece strings: are the two pieces upright read along the link, or across it? ----------
    # (measured on T4, plate 1A, before this check: 33 of the 40 wrongly directed words of 2+ pieces were two-piece strings;
    # two digits one above the other, or a digit and a stray stroke, get linked). If the pieces look more upright turned a
    # quarter (against the plate's own upright glyphs) by SPLIT2 or more, the string is undone into two lone pieces.
    inbank0 = set(bank_pid.tolist()); new = []; nsplit = 0; remap = {}
    cand2 = [pid for pid, I in enumerate(info) if len(I['g']) == 2 and not I['spaced'] and pid not in inbank0] if len(bank) else []
    rows = []
    for pid in cand2:
        I = info[pid]; u = I['d']; up = np.array([u[1], -u[0]])
        for v in (u, -u, up, -up):
            for g in I['g']: rows.append(orx.vec(orx.patch(lab, g + 1, G['c'][g], v, I['h'], G['box'][g])))
    sim2 = orx.best_sim(np.array(rows, np.float32), bank).reshape(-1, 4, 2).mean(2) if rows else np.zeros((0, 4))
    SC2 = {pid: sim2[k] for k, pid in enumerate(cand2)}
    for pid, I in enumerate(info):
        if pid in SC2:
            sc = SC2[pid]; u = I['d']; up = np.array([u[1], -u[0]])
            if max(sc[2], sc[3]) >= max(sc[0], sc[1]) + SPLIT2:
                nsplit += 1
                for g in I['g']:
                    d = up if sc[2] >= sc[3] else -up
                    new.append(dict(g=[g], h=float(G['s'][g]), Q=np.vstack([G['c'][g] - d * 0.5, G['c'][g] + d * 0.5]), kind='single', rms=0.0, rms_line=0.0,
                                    spaced=False, marks=[], d0=d, multi_piece=False, words=[[0, 1]], gaps=[], d=d, vertical=bool(abs(d[0]) < np.sin(np.deg2rad(orx.VERT))),
                                    flip_rule=False, split2=True))
                continue
        remap[pid] = len(new); new.append(I)
    info = new
    bank_pid = np.array([remap[p] for p in bank_pid.tolist()], int); half = bank_pid % 2   # bank phrases are never undone
    print(f'  two-piece strings undone (pieces upright across the link): {nsplit}')
    # ---------- the shapes test for every phrase of 2+ glyphs (and four turns for lone glyphs) ----------
    for pid, I in enumerate(info):
        s = I['g']; u = I['d']
        if (len(s) >= 2 or I.get('multi_piece')):
            Pf = np.array([orx.vec(orx.patch(lab, g + 1, G['c'][g], u, I['h'], G['box'][g])) for g in s], np.float32)
            Pr = np.array([orx.vec(orx.patch(lab, g + 1, G['c'][g], -u, I['h'], G['box'][g])) for g in s], np.float32)
            I['_P'] = (Pf, Pr)
        else:
            g = s[0]; up = np.array([u[1], -u[0]])
            # two readings of a lone piece: one character read across its long side (height = long side), or several
            # touching characters read along it (height = short side, as 284 or 25.45 printed in one piece)
            ht = float(G['t'][g])
            I['_P'] = tuple(np.array([orx.vec(orx.patch(lab, g + 1, G['c'][g], v, hh, G['box'][g]))], np.float32) for v, hh in ((u, I['h']), (-u, I['h']), (up, ht), (-up, ht)))
    # bank phrases are tested against the other half of the bank (no glyph meets itself); others against all of it
    inbank = set(bank_pid.tolist())
    for part in (0, 1, None):
        ids = [pid for pid in range(len(info)) if (pid in inbank and pid % 2 == part) or (part is None and pid not in inbank)]
        if not ids: continue
        B = bank if part is None else bank[half != part]
        rows = []; owner = []
        for pid in ids:
            for k, P in enumerate(info[pid]['_P']): rows.append(P); owner += [(pid, k)] * len(P)
        T = np.vstack(rows); sim = orx.best_sim(T, B)
        acc = {}
        for (pid, k), v in zip(owner, sim): acc.setdefault((pid, k), []).append(v)
        for pid in ids:
            I = info[pid]; sc = [float(np.mean(acc[(pid, k)])) for k in range(len(I['_P']))]
            I['shape_sc'] = sc
    for I in info: I.pop('_P', None)
    # ---------- decide the reading direction ----------
    for pid, I in enumerate(info):
        s = I['g']
        if (len(s) >= 2 or I.get('multi_piece')):
            mv = orx.mark_vote(I['marks'], False) - orx.mark_vote(I['marks'], True)
            ds = I['shape_sc'][1] - I['shape_sc'][0]               # > 0: reversed looks more upright
            I['mark_vote'] = int(mv); I['shape_margin'] = round(float(ds), 4)
            flip_shape = ds > 0
            # measured 25 Nov on near-horizontal strings (upright by the rule): the shapes cue agrees 96-98% (99% with
            # 3+ glyphs), the marks vote 43-54% (no better than chance), so marks do not decide
            if abs(ds) >= SHAPE_MIN: flip, how = flip_shape, 'shapes'
            else: flip, how = I['flip_rule'], 'rule'
            I['flip'] = bool(flip); I['orient_by'] = how
            I['agree_rule_shape'] = bool(flip_shape == I['flip_rule'])
        else:
            sc = I['shape_sc']; k = int(np.argmax(sc)); u = I['d']; up = np.array([u[1], -u[0]])
            I['single_turn'] = ['d', '-d', 'up', '-up'][k]; I['single_margin'] = round(float(sorted(sc)[-1] - sorted(sc)[-2]), 4)
            I['flip'] = False; I['orient_by'] = 'single'
            I['d_read'] = [u, -u, up, -up][k]
            if k >= 2 and not I.get('multi_piece'): I['h'] = float(G['t'][s[0]]); I['read_along'] = True
    # ---------- words, their marks and features ----------
    tmask = np.zeros(lab.shape, np.uint8)
    os.makedirs(os.path.join(OUT, 'strips', TAG), exist_ok=True)
    if strips:                                              # strips of an earlier run would not match the new phrase ids
        for f in os.listdir(os.path.join(OUT, 'strips', TAG)):
            if f.endswith('.png'): os.remove(os.path.join(OUT, 'strips', TAG, f))
    recs = []
    for pid, I in enumerate(info):
        s = I['g']; h = I['h']
        if (len(s) >= 2 or I.get('multi_piece')):
            Qs, gi, hw, T = word_arcs(G, I)
            L = len(Qs) - 1
            words = []
            for wi, (a, b) in enumerate(I['words']):
                lo = gi[a] - hw[a]; hi = gi[b - 1] + hw[b - 1]
                words.append(dict(glyphs=[int(g) for g in s[a:b]], lo=float(lo), hi=float(hi), marks=[]))
            for m in I['marks']:
                at = m['at']
                dd = [max(w['lo'] - at, at - w['hi'], 0) for w in words]; k = int(np.argmin(dd))
                w = words[k]; pos = 'inside' if w['lo'] <= at <= w['hi'] else ('before' if at < w['lo'] else 'after')
                w['marks'].append(dict(m, pos=pos))
            if I['flip']:                                       # turn to reading order
                for w in words:
                    w['lo'], w['hi'] = L - w['hi'], L - w['lo']; w['glyphs'] = w['glyphs'][::-1]
                    for m in w['marks']:
                        m['place'] = {'high': 'low', 'low': 'high'}.get(m['place'], m['place']); m['pos'] = {'before': 'after', 'after': 'before'}.get(m['pos'], m['pos'])
                        m['off'] = -m['off']
                words = words[::-1]
                Qr = Qs[::-1]
            else:
                Qr = Qs
            u = Qr[-1] - Qr[0]; u = u / max(np.hypot(*u), 1e-6)
        else:
            g = s[0]; u = I['d_read']; Qr = np.vstack([G['c'][g] - u * 0.5, G['c'][g] + u * 0.5])
            words = [dict(glyphs=[int(g)], lo=0.0, hi=1.0, marks=[])]
        ang = float(np.degrees(np.arctan2(-u[1], u[0])))      # reading direction, degrees anticlockwise from east
        # strip
        sp = None
        if strips and (len(s) >= 2 or I.get('multi_piece')):
            ext = max([0.0] + [m['s'] + 0.3 * h for w in words for m in w['marks'] if m['pos'] == 'after'])
            mx, my, Qx, Tx, upx = wl.strip_maps(Qr, h, head=int(0.8 * h) + 4, tail=int(0.8 * h + ext) + 4, half=0.9 * h)
            img = cv2.remap(grey, mx, my, cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=255)
            x0, y0 = max(0, int(mx.min()) - 2), max(0, int(my.min()) - 2)
            sub = np.isin(lab[y0:int(my.max()) + 3, x0:int(mx.max()) + 3], [g + 1 for g in s] + [m['g'] + 1 for m in I['marks']]).astype(np.uint8) * 255
            mm = cv2.remap(sub, mx - x0, my - y0, cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=0)
            cv2.imwrite(os.path.join(OUT, 'strips', TAG, f'p{pid:05d}.png'), img)
            cv2.imwrite(os.path.join(OUT, 'strips', TAG, f'p{pid:05d}_m.png'), mm)
            sp = dict(file=f'strips/{TAG}/p{pid:05d}.png', mask=f'strips/{TAG}/p{pid:05d}_m.png', w=int(img.shape[1]), h=int(img.shape[0]), head=int(0.8 * h) + 4)
        for w in words:
            gl = w['glyphs']; c = G['c'][gl]; cxy = c.mean(0)
            wid = [(G['S'][g, wl.kidx(np.arctan2(u[1], u[0]))] + G['S'][g, wl.kidx(np.arctan2(u[1], u[0]) + np.pi)]) for g in gl]
            nch = int(sum(max(1, int(round(wd / (0.62 * h)))) for wd in wid))
            blk = int(cx.at(C, C['block'], cxy[0], cxy[1])); pap = bool(cx.at(C, C['paper'], cxy[0], cxy[1]))
            dl = float(cx.at(C, C['dist'], cxy[0], cxy[1])); li = int(cx.at(C, C['near'], cxy[0], cxy[1]))
            adiff = float(np.degrees(np.arccos(min(1.0, abs(u @ C['dirs'][li]))))) if li >= 0 else 90.0
            fillf = float(np.mean(cx.at(C, C['fill'], c[:, 0], c[:, 1])))
            # pipe or sewer ink alongside: sample both sides of the word's centre line, 0.6 to 1.8 heights out
            up = np.array([u[1], -u[0]]); a0 = c @ u; t = np.linspace(a0.min() - 0.5 * h, a0.max() + 0.5 * h, 12)
            base = cxy - (cxy @ u) * u
            side = []
            for sg in (1, -1):
                hit = np.zeros(len(t), bool)
                for o in np.linspace(0.6, 1.8, 7):
                    p = base[None] + t[:, None] * u[None] + sg * o * h * up[None]
                    hit |= cx.at(C, C['pipe'], p[:, 0], p[:, 1]) > 0
                side.append(float(hit.mean()))
            mk = w['marks']
            w.update(cx=round(float(cxy[0]), 1), cy=round(float(cxy[1]), 1), n=len(gl), nch=nch, h=round(h, 1), angle=round(ang, 1),
                     block=blk, paper=pap, d_line=round(dl, 1), line_angle_diff=round(adiff, 1), fill=round(fillf, 2), pipe_side=round(max(side), 2),
                     m_high_after=sum(m['place'] == 'high' and m['pos'] == 'after' for m in mk), m_high_in=sum(m['place'] == 'high' and m['pos'] == 'inside' for m in mk),
                     m_low_in=sum(m['place'] == 'low' and m['pos'] == 'inside' for m in mk), m_low_after=sum(m['place'] == 'low' and m['pos'] == 'after' for m in mk),
                     m_mid_in=sum(m['place'] == 'mid' and m['pos'] == 'inside' for m in mk))
        if (len(s) >= 2 or I.get('multi_piece')):
            for k in range(len(words)): words[k]['gap_next'] = round(float((words[k + 1]['lo'] - words[k]['hi']) / h), 3) if k + 1 < len(words) else None
        else:
            words[0]['gap_next'] = None
        recs.append(dict(id=pid, n=len(s), h=round(h, 2), multi_piece=bool(I.get('multi_piece')), angle=round(ang, 1), kind_line=I['kind'], rms=round(float(I['rms']), 4), spaced=I['spaced'],
                         vertical=I['vertical'], orient_by=I['orient_by'], flip=I['flip'], flip_rule=I['flip_rule'],
                         mark_vote=I.get('mark_vote'), shape_margin=I.get('shape_margin'), agree_rule_shape=I.get('agree_rule_shape'),
                         single_turn=I.get('single_turn'), single_margin=I.get('single_margin'), shape_sc=[round(v, 4) for v in I['shape_sc']],
                         centre_line=[[round(float(x), 1), round(float(y), 1)] for x, y in Qr[::max(1, len(Qr) // 24)]] + [[round(float(Qr[-1][0]), 1), round(float(Qr[-1][1]), 1)]],
                         strip=sp, words=words, glyphs=[int(g) for g in s]))
    import classify as cl  # noqa: E402
    cl.classify(recs, C)
    for r in recs:
        for w in r['words']:
            if w['kind'] == 'junk': continue
            ids = w['glyphs'] + [m['g'] for m in w['marks']]
            for g in ids:
                x, y, ww, hh = G['box'][g]; sub = lab[y:y + hh, x:x + ww] == g + 1; tmask[y:y + hh, x:x + ww][sub] = 255
    cv2.imwrite(os.path.join(OUT, f'{TAG}_textmask.png'), tmask)
    cv2.imwrite(os.path.join(OUT, f'{TAG}_glyphlab.png'), np.dstack([(lab & 255), (lab >> 8) & 255, (lab >> 16) & 255]).astype(np.uint8))
    meta = dict(plate=N, tag=TAG, source=mf, context=C['src'], glyphs=int(G['n']), ring_pieces=int(ring.sum()), bank=int(len(bank)),
                params=dict(wordlib=wl.P, word_gap=gw.WORD_GAP, join_gap=gw.JOIN_GAP, spaced=gw.SPACED, vert=orx.VERT),
                note='words agent prototype, 25 Nov 2026: rule-based grouping, orientation and kinds from geometry; not ground truth')
    json.dump(dict(meta=meta, strings=recs), open(os.path.join(OUT, f'{TAG}_words.json'), 'w', encoding='utf8'), default=lambda o: o.tolist() if hasattr(o, 'tolist') else str(o))
    # strings.json for draw.py
    json.dump(dict(plate=N, strings=[dict(id=r['id'], n=r['n'], glyphs=r['glyphs'], marks=[m for w in r['words'] for m in w['marks']],
                                         centres=[[float(G['c'][g][0]), float(G['c'][g][1])] for g in r['glyphs']]) for r in recs]),
              open(os.path.join(OUT, f'{TAG}_strings.json'), 'w', encoding='utf8'))
    json.dump(dict(plate=N, strings=[dict(id=r['id'], kind=r['words'][0]['kind']) for r in recs]), open(os.path.join(OUT, f'{TAG}_kinds.json'), 'w', encoding='utf8'))
    kinds = {}
    for r in recs:
        for w in r['words']: kinds[w['kind']] = kinds.get(w['kind'], 0) + 1
    print(f'  {len(recs)} strings, {sum(len(r["words"]) for r in recs)} words; kinds {dict(sorted(kinds.items(), key=lambda x: -x[1]))}; {time.time() - t0:.0f} s')
    return recs


if __name__ == '__main__':
    N = sys.argv[1]
    run(N, gw.arg('--src', 'bins'), '--no-strips' not in sys.argv)
