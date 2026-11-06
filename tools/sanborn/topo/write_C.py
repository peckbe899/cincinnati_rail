try: import _ws  # Sanborn paths: tools/sanborn/_ws.py, configs/sanborn_paths.json (was the Topography workspace scratchpad and the chat uploads)
except ImportError: import os as _o, sys as _s; _s.path.append(_o.path.normpath(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..'))); import _ws
import json
D={
"25":[(341,624),(9515,645),(344,7321),(9501,7272),"5000 W","6000 E","34000 N","26000 N",
      "All borders and labels clear. Diagonal adjacent-sheet notes: (Sheet 24) at TR, (Sheet 36) at BL, (Sheet 22) at BR; none at TL."],
"26":[(356,622),(9535,650),(342,7313),(9513,7270),"5000 W","6000 E","26000 N","18000 N",
      "All clear. Adjacent-sheet notes: (Sheet 37) TL, (Sheet 23) TR, (Sheet 35) BL, (Sheet 21) BR."],
"27":[(328,640),(9519,648),(348,7332),(9508,7276),"5000 W","6000 E","18000 N","10000 N",
      "All clear. Adjacent-sheet notes: (Sheet 36) TL, (Sheet 22) TR, (Sheet 34) BL, (Sheet 20) BR."],
"28":[(348,639),(9516,641),(364,7328),(9527,7252),"5000 W","6000 E","10000 N","2000 N",
      "All clear. Adjacent-sheet notes: (Sheet 35) TL, (Sheet 21) TR, (Sheet 33) BL, (Sheet 19) BR."],
"31":[(304,675),(9462,668),(334,7378),(9475,7295),"16000 W","5000 W","14000 S","22000 S",
      "All clear. West-side sheet: right edge is 5000 W. Adjacent-sheet notes: (Sheet 43) TL, (Sheet 30) TR; none at BL/BR."],
"32":[(302,592),(9524,563),(354,7386),(9554,7283),"16000 W","5000 W","6000 S","14000 S",
      "All clear. Noticeably rotated/skewed scan: left edge drifts +52 px and right edge +30 px in x from top to bottom. Adjacent-sheet notes: (Sheet 42) TL, (Sheet 29) TR, (Sheet 44) BL; none at BR."],
"33":[(320,575),(9566,601),(332,7312),(9558,7243),"16000 W","5000 W","2000 N","6000 S",
      "All clear. Top labelled 2000 N, bottom 6000 S (sheet straddles the zero line). Adjacent-sheet notes: (Sheet 40) TL, (Sheet 28) TR, (Sheet 43) BL, (Sheet 30) BR."],
"34":[(368,602),(9620,645),(374,7367),(9592,7324),"16000 W","5000 W","10000 N","2000 N",
      "All clear. Adjacent-sheet notes: (Sheet 39) TL, (Sheet 27) TR, (Sheet 42) BL, (Sheet 29) BR."],
"35":[(328,556),(9630,570),(333,7358),(9607,7297),"16000 W","5000 W","18000 N","10000 N",
      "All clear. Adjacent-sheet notes: (Sheet 38) TL, (Sheet 26) TR, (Sheet 40) BL, (Sheet 28) BR."],
"36":[(351,600),(9643,634),(412,7412),(9655,7312),"16000 W","5000 W","26000 N","18000 N",
      "All clear, but geometry is unusually distorted: left edge drifts +61 px in x top to bottom while right edge drifts only +12 px, and bottom edge rises 100 px left to right (top falls 34 px). BL corner confirmed at x~412 (both visually and by line profile). Neatline is faint at TL/TR. Adjacent-sheet notes: (Sheet 25) TR, (Sheet 39) BL, (Sheet 27) BR; none at TL."],
"37":[(350,584),(9671,602),(367,7370),(9670,7299),"16000 W","5000 W","34000 N","26000 N",
      "All clear. Adjacent-sheet notes: (Sheet 38) BL, (Sheet 26) BR; none at TL/TR."],
}
out={}
for s,(tl,tr,bl,br,xl,xr,yt,yb,note) in D.items():
    out[s]={"TL":{"px":list(tl),"x":xl,"y":yt},"TR":{"px":list(tr),"x":xr,"y":yt},
            "BL":{"px":list(bl),"x":xl,"y":yb},"BR":{"px":list(br),"x":xr,"y":yb},"note":note}
p=(_ws.DATA + "topo/comp/read_C.json")
json.dump(out,open(p,'w'),indent=1)
print(open(p).read()[:600])
