try: import _ws  # Sanborn paths: tools/sanborn/_ws.py, configs/sanborn_paths.json (was the Topography workspace scratchpad and the chat uploads)
except ImportError: import os as _o, sys as _s; _s.path.append(_o.path.normpath(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..'))); import _ws
# correction of Ben's georeference of 22-35N: a smoothing thin-plate spline through the offsets (Ben's -> today) at crossings of streets that
# survive unchanged. Left out as moved or widened since 1922: Dixmyth (realigned), Riddle at McMicken, Duke, Taylor/Foulke (offsets
# disagree with their neighbours). Leave-one-out test picks the smoothing. Writes cuf/corr.pkl (forward ben->true and inverse true->ben).
import json, pickle, sys, numpy as np
from scipy.interpolate import RBFInterpolator
SP = _ws.DATA
M = [m for m in json.load(open(SP + 'cuf/matches.json')) if m.get('osm')]
DROP = lambda m: 'Dixmyth' in m['a'] + m['b'] or 'Duke' in m['a'] + m['b'] or (('Riddle' in m['a'] + m['b']) and 'McMicken' in m['a'] + m['b']) or (('Taylor' in m['a'] + m['b']) and 'Foulke' in m['a'] + m['b'])
K = [m for m in M if not DROP(m)]
B = np.array([m['ben'] for m in K]); O = np.array([m['osm'] for m in K]); D = O - B; U = 100.0
print('controls', len(K), 'raw rms', round(float(np.sqrt(np.mean(np.sum(D ** 2, 1)))), 2), 'max', round(float(np.hypot(*D.T).max()), 2))
best = None
for sm in (0.05, 0.2, 0.5, 1.0, 2.0, 5.0, 20.0):
    e = []
    for i in range(len(K)):
        j = np.arange(len(K)) != i
        rb = RBFInterpolator(B[j] / U, D[j], kernel='thin_plate_spline', smoothing=sm, degree=1)
        e.append(np.hypot(*(rb(B[i:i + 1] / U)[0] - D[i])))
    e = np.array(e); print('smoothing', sm, 'leave-one-out rms', round(float(np.sqrt(np.mean(e ** 2))), 2), 'max', round(float(e.max()), 2))
    if best is None or np.sqrt(np.mean(e ** 2)) < best[0]: best = (float(np.sqrt(np.mean(e ** 2))), sm)
sm = best[1]
rb = RBFInterpolator(B / U, D, kernel='thin_plate_spline', smoothing=sm, degree=1)
fit = np.hypot(*(rb(B / U) - D).T); print('chosen smoothing', sm, 'fit rms', round(float(np.sqrt(np.mean(fit ** 2))), 2))
inv = RBFInterpolator(O / U, -D, kernel='thin_plate_spline', smoothing=sm, degree=1)
pickle.dump(dict(B=B, O=O, D=D, smooth=sm, U=U, names=[m['a'] + ' / ' + m['b'] for m in K]), open(SP + 'cuf/corr.pkl', 'wb'))
json.dump(dict(controls=len(K), dropped=[m['a'] + ' / ' + m['b'] for m in M if DROP(m)], raw_rms=float(np.sqrt(np.mean(np.sum(D ** 2, 1)))), loo_rms=best[0], smoothing=sm), open(SP + 'cuf/corr_report.json', 'w'), indent=1)
