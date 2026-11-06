"""Render the 1912 survey for a window with markers: blue = 1922 position, red = current 1904 deck position."""
try: import _ws  # Sanborn paths: tools/sanborn/_ws.py, configs/sanborn_paths.json (was the Topography workspace scratchpad and the chat uploads)
except ImportError: import os as _o, sys as _s; _s.path.append(_o.path.normpath(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..'))); import _ws
import json, sys, numpy as np
SP=_ws.DATA
sys.path.insert(0,_ws.CODE+'sbg'); sys.path.insert(0,_ws.CODE+'lph')
import r12
from ref22 import ref
from fit22 import pair
from PIL import Image, ImageDraw
def deckpts(sheets, tfpath=SP+'deck/sheet_tf.json'):
    TF=json.load(open(tfpath)); out=[]
    def ap(p,x,y):
        if len(p)==6: return p[0]*x+p[1]*y+p[4], p[2]*x+p[3]*y+p[5]
        a,c,tx,ty=p; return a*x+c*y+tx, c*x-a*y+ty
    for s in sheets:
        try: d=json.load(open(SP+f'sbg/picks/s{s}.json'))
        except FileNotFoundError: continue
        for p in d['intersections']:
            E,N=ap(TF[s],p['x'],p['y']); out.append(dict(E=E,N=N,a=p['a'],b=p['b']))
    return out
if __name__=='__main__':
    E0,N0,E1,N1=map(float,sys.argv[1:5]); out=sys.argv[5]; sheets=sys.argv[6].split(',') if len(sys.argv)>6 else []
    r12.render(E0,N0,E1,N1,out)
    im=Image.open(out); dr=ImageDraw.Draw(im)
    px=lambda E,N: ((E-E0)/(E1-E0)*im.size[0],(N1-N)/(N1-N0)*im.size[1])
    for k,v in ref().items():
        for q in v:
            if E0<q[0]<E1 and N0<q[1]<N1:
                X,Y=px(*q); dr.ellipse([X-7,Y-7,X+7,Y+7],outline=(0,0,255),width=3); dr.text((X+8,Y+2),'/'.join(w[:8] for w in k),fill=(0,0,200),font=r12.FNT)
    for p in deckpts(sheets):
        if E0<p['E']<E1 and N0<p['N']<N1:
            X,Y=px(p['E'],p['N']); dr.line([X-7,Y-7,X+7,Y+7],fill=(230,0,0),width=3); dr.line([X-7,Y+7,X+7,Y-7],fill=(230,0,0),width=3)
    im.save(out,quality=90)
