try: import _ws  # Sanborn paths: tools/sanborn/_ws.py, configs/sanborn_paths.json (was the Topography workspace scratchpad and the chat uploads)
except ImportError: import os as _o, sys as _s; _s.path.append(_o.path.normpath(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..'))); import _ws
import json, glob, numpy as np
from PIL import Image
Image.MAX_IMAGE_PIXELS=None
base=_ws.ext("/mnt/user-data/uploads/_Cincinnati Rail/Historic_Topo/1912_City_Topographic_Survey/")
V={"30":{"TL":[273,613],"TR":[9525,648],"BL":[280,7365],"BR":[9497,7330]},
"25":{"TL":[341,624],"TR":[9515,645],"BL":[344,7321],"BR":[9501,7272]},
"26":{"TL":[356,622],"TR":[9535,650],"BL":[342,7313],"BR":[9513,7270]},
"27":{"TL":[328,640],"TR":[9519,648],"BL":[348,7332],"BR":[9508,7276]},
"28":{"TL":[348,639],"TR":[9516,641],"BL":[364,7328],"BR":[9527,7252]},
"31":{"TL":[304,675],"TR":[9462,668],"BL":[334,7378],"BR":[9475,7295]},
"32":{"TL":[302,592],"TR":[9524,563],"BL":[354,7386],"BR":[9554,7283]},
"33":{"TL":[320,575],"TR":[9566,601],"BL":[332,7312],"BR":[9558,7243]},
"34":{"TL":[368,602],"TR":[9620,645],"BL":[374,7367],"BR":[9592,7324]},
"35":{"TL":[328,556],"TR":[9630,570],"BL":[333,7358],"BR":[9607,7297]},
"36":{"TL":[351,600],"TR":[9643,634],"BL":[412,7412],"BR":[9655,7312]},
"37":{"TL":[350,584],"TR":[9671,602],"BL":[367,7370],"BR":[9670,7299]}}
R=25
for sid,cs in V.items():
    fn=glob.glob(base+f"Sheet_{int(sid):02d}_*.jpg")[0]
    g=np.asarray(Image.open(fn).convert('L')).astype(float)
    out=[]
    for k,(ex,ey) in cs.items():
        dx=1 if k[1]=='L' else -1   # inward x direction
        dy=1 if k[0]=='T' else -1   # inward y direction
        ys=sorted([ey+dy*30, ey+dy*200]); xs=sorted([ex+dx*30, ex+dx*200])
        colp=g[ys[0]:ys[1], ex-R:ex+R+1].mean(0); vx=ex-R+int(np.argmin(colp))
        rowp=g[ey-R:ey+R+1, xs[0]:xs[1]].mean(1); hy=ey-R+int(np.argmin(rowp))
        out.append(f"{k} vis({ex},{ey}) auto({vx},{hy}) d=({vx-ex},{hy-ey}) contrast v{colp.min()-np.median(colp):.0f} h{rowp.min()-np.median(rowp):.0f}")
    print(sid,' | '.join(out))
