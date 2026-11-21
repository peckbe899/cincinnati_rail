"""outline-quality: open line ends in what the editor shows on plate 44, for finished bench runs.
    python open_ends44.py TAG [TAG ...]
An end is open when no other shown line or sheet-outline piece passes within 10 px (plates_check.indicators). Reads
runs/TAG/44_shown.json (shown lines + sheet outline, as bench44 writes it) and runs/TAG/bench44.json; prints, per run,
open ends, delete/draw counts and a rough editor-time ESTIMATE with visual-cut's per-operation guesses (tally.py:
delete 3 s, draw a side 8 s, close an open end 3 s; ends of lines Ben draws are not counted twice). Writes open_ends44.json."""
import json, os, sys
import numpy as np
sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__)).replace('\\', '/') + '/'
sys.path.insert(0, HERE)
import plates_check as PC  # noqa: E402
out = {}
for tag in sys.argv[1:]:
    sh = json.load(open(HERE + f'runs/{tag}/44_shown.json')); b = json.load(open(HERE + f'runs/{tag}/bench44.json'))
    SH = [e for e in sh if e['state'] == 'sheet']; shown = [e for e in sh if e['state'] != 'sheet']
    ind = PC.indicators([], shown, SH, dict(alpha=np.ones((2, 2), bool)), None)
    w = b['workload']['all']; est = (w['delete_n'] * 3 + w['draw_n'] * 8 + ind['open_ends'] * 3) / 60
    out[tag] = dict(open_ends=ind['open_ends'], open_ends_per_line=ind['open_ends_per_line'], editor_lines=ind['editor_lines'], faces_snap1_5=ind['faces_snap1.5'],
                    delete_n=w['delete_n'], draw_n=w['draw_n'], est_minutes=round(est, 1))
    print(tag, json.dumps(out[tag]))
json.dump(out, open(HERE + 'open_ends44.json', 'w'), indent=1)
