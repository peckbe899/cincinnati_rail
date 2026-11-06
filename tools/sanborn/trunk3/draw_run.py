try: import _ws  # Sanborn paths: tools/sanborn/_ws.py, configs/sanborn_paths.json (was the Topography workspace scratchpad and the chat uploads)
except ImportError: import os as _o, sys as _s; _s.path.append(_o.path.normpath(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..'))); import _ws
import sys, json, numpy as np, matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
sys.path.insert(0, (_ws.CODE + 'trunk3'))
import draw as D, build as B, north as N
SP = D.SP; FR = N.FR
LA = B.build('A'); LB = B.build('B')
P = lambda s, o: N.FD.at(s, o)[0]
notes = [(P(N.S0 + 250, -40), 'West group (ORR X2, RER B, APEx Dayton): one curve left from s %.0f,\nDayton %.0f m, B %.0f m, X2 %.0f m' % (N.S0, N.R_D, N.R_D - 9, N.R_D - 18), 'right'),
         (P(N.S_IV, -45), 'Ivorydale (B): island west of Dayton;\nX2 steps out round it (as at Mitchell)', 'right'),
         (N.FW.at(N.S_NC0 + 300, 30)[0], 'East group (APEx Norwood, ORR/TV): straight on to s %.0f,\nthen one %.0f m curve onto the Norwood axis' % (N.S_NC0, N.R_N), 'left'),
         (P(N.S_DT + 400, 20), 'X2 drawn to the plan window edge', 'left')]
D.plan(LA, 714900, 716900, 4338150, 4339850, SP + 'trunk3/p_split.png', 'Split north of Mitchell: X2 | B | Dayton left, Norwood | ORR/TV straight on (no crossings)', notes, 14)
D.plan(LA, 714900, 720000, 4337700, 4339850, SP + 'trunk3/p_overview.png', 'North of Mitchell to the borders: Southwest Chief side and the Norwood branch', notes, 16)
fig, axs = plt.subplots(3, 1, figsize=(15, 11), gridspec_kw=dict(height_ratios=[1, 1, 0.9]))
D.strip(LA, 'A', axs[0]); axs[0].set_title('A: ORR at the station\'s 8.25 m gap from the end of the Norwood curve (no S). TV off the shared pair east of Reading Rd, over ORR and APEx onto T10 / T9 (R %.0f m)' % B.TV['A']['R'], fontsize=8)
D.strip(LB, 'B', axs[1]); axs[1].set_title('B: four tracks compact (4.5 m) to the TV crossing, then one S for ORR into T4 / T2 (TV R %.0f m)' % B.TV['B']['R'], fontsize=8)
# profile (option A)
ss = np.arange(2900, 4201, 5.0); bedA = np.polyfit([3000, 4150], [N.gsm(3000, 0), N.gsm(4150, 0)], 1)
import tv_profile as TP
z = TP.profiles('A', ss)
axs[2].plot(ss, z['ground'], color='#8d6e63', lw=0.8, label='ground (corridor centre, LiDAR)')
axs[2].plot(ss, z['tv'], color='#6a1b9a', lw=1.2, label='Transvalley (at ground, the railway formation)')
axs[2].plot(ss, z['low'], color='#111', lw=1.2, label='APEx and ORR (into the trench)')
axs[2].axvspan(z['xa'], z['xb'], color='#e1bee7', alpha=0.5, label='TV over APEx/ORR (7.3 m or more)')
axs[2].set_xlim(2900, 4200); axs[2].set_ylabel('rail level (m)', fontsize=7); axs[2].legend(fontsize=6, loc='upper left'); axs[2].grid(lw=0.2); axs[2].tick_params(labelsize=6)
axs[2].set_xlabel('Norwood frame s (m); throat at 4,150', fontsize=7)
fig.tight_layout(); fig.savefig(SP + 'trunk3/p_tv.png', dpi=150); plt.close(fig)
print('ok')
