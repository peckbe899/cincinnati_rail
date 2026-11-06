"""Corrected sheet mapping = Coons base + per-sheet polynomial residual from run2."""
import numpy as np, json
from geo import Sheet, S, FT, loc2utm
from icp import basis
class CSheet:
    def __init__(self,sid,deg=1,tag='r2'):
        self.b=Sheet(sid,coons=True); self.sid=sid
        if deg is None: self.r=None
        else: self.r=json.load(open(f'boldx/{tag}_{deg}_{sid}.json'))
    def R(self,u,v):
        if self.r is None: return np.zeros_like(u),np.zeros_like(v)
        r=self.r; P=basis((u/2-r['u0'])/r['W'],(v/2-r['v0'])/r['H'],r['deg'])
        return 2*(P@np.array(r['X'])),2*(P@np.array(r['Y']))
    def p2g(self,u,v):
        u=np.asarray(u,float).ravel(); v=np.asarray(v,float).ravel(); du,dv=self.R(u,v)
        return self.b.p2g(u+du,v+dv)
    def p2utm(self,u,v):
        gx,gy=self.p2g(u,v); E,N=loc2utm.transform(gx*FT,gy*FT); return np.asarray(E),np.asarray(N)
