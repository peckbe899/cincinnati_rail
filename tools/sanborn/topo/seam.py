import numpy as np, json, sys
from icp import run
from geo import S
pairs=[('29','19'),('28','20'),('27','21'),('33','29'),('35','27'),('40','34'),('34','28'),('43','32')]
for A,B in pairs:
    ra=run(A,deg=0,arange=(0.8,1.0)); rb=run(B,deg=0,arange=(0.0,0.2))
    fa=(S[A]['x_e']-S[A]['x_w'])/np.hypot(*np.subtract(S[A]['corners']['TR'],S[A]['corners']['TL']))
    fb=(S[B]['x_e']-S[B]['x_w'])/np.hypot(*np.subtract(S[B]['corners']['TR'],S[B]['corners']['TL']))
    ea=(ra['centre'][0]*fa,-ra['centre'][1]*fa); eb=(rb['centre'][0]*fb,-rb['centre'][1]*fb)
    print(f"{A}|{B}  A-east n{ra['n']:6d} R{ra['R']:.2f} shift ft E{ea[0]:6.1f} N{ea[1]:6.1f}   B-west n{rb['n']:6d} R{rb['R']:.2f} shift ft E{eb[0]:6.1f} N{eb[1]:6.1f}   diff E{ea[0]-eb[0]:6.1f} N{ea[1]-eb[1]:6.1f}",flush=True)
