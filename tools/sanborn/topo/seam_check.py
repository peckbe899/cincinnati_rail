"""Seam check: for adjacent finished tiles, the difference of the two I4 surfaces over their 400 m overlap (both covered)."""
import numpy as np, json, glob, cv2
tiles=json.load(open('tiles.json'))
done=[k for k in sorted(tiles) if glob.glob(f'iter_{k}_I4.npy')]
def cov(k):
    s=np.load(f'pilot_{k}_S1912.npz'); return cv2.resize(s['cov'].astype(np.uint8),(1700,1700),interpolation=cv2.INTER_NEAREST).astype(bool)
rows=[]
for i,a in enumerate(done):
    for b in done[i+1:]:
        dx=tiles[b]['cx']-tiles[a]['cx']; dy=tiles[b]['cy']-tiles[a]['cy']
        if (abs(dx)<10 and abs(abs(dy)-3000)<10) or (abs(dy)<10 and abs(abs(dx)-3000)<10):
            ox=int(round(dx/2)); oy=int(round(-dy/2))
            A=np.load(f'iter_{a}_I4.npy'); B=np.load(f'iter_{b}_I4.npy'); ca=cov(a); cb=cov(b)
            ra=slice(max(0,oy),1700+min(0,oy)); rb=slice(max(0,-oy),1700+min(0,-oy))
            qa=slice(max(0,ox),1700+min(0,ox)); qb=slice(max(0,-ox),1700+min(0,-ox))
            d=A[ra,qa]-B[rb,qb]; m=ca[ra,qa]&cb[rb,qb]
            if m.sum()>5000: rows.append((a,b,m.sum()*4/1e6,np.abs(d[m]).mean(),np.percentile(np.abs(d[m]),95)))
for r in rows: print('%s-%s overlap %.2f km2: mean |diff| %.2f m, p95 %.2f m'%r)
