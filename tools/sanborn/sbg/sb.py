"""Sanborn pick helper.
  python3 sb.py render SHEET [x0 y0 x1 y1] OUT.jpg      render a sheet (or a crop, in original page pixels) with a labelled pixel grid
  python3 sb.py check SHEET OUT.jpg                     draw the picks saved in picks/sSHEET.json on the full sheet
  python3 sb.py size SHEET                              print the page size in pixels
Pixel coordinates are always ORIGINAL page pixels (x right, y down from the top-left of the scan)."""
try: import _ws  # Sanborn paths: tools/sanborn/_ws.py, configs/sanborn_paths.json (was the Topography workspace scratchpad and the chat uploads)
except ImportError: import os as _o, sys as _s; _s.path.append(_o.path.normpath(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..'))); import _ws
import sys, os, glob, json
from PIL import Image, ImageDraw, ImageFont
Image.MAX_IMAGE_PIXELS=None
ROOT=_ws.ext("/mnt/user-data/uploads/Documents--_Personal--_Cincinnati Rail/Maps/Sanborn/")
HERE = _ws.data_dir(os.path.dirname(os.path.abspath(__file__)))
def find(sheet):
    if str(sheet).upper() == '22-38':       # 2026-10-20: 1922 plate 38 (Clifton: Ludlow, Clifton Avenue, Jefferson, Vine), Ben's scan, roughly north-up
        return (_ws.DATA + 'cuf/22-38.jpg')
    if str(sheet).upper() == '22-35N':      # 2026-10-20: Ben's georeferenced 1922 plate 35 (north: Clifton Heights, University, Fairview), already north-up in EPSG:3857 pixels
        return (_ws.DATA + 'cuf/22-35N.jpg')
    if str(sheet).upper() in ('22-66','22-67','22-68','22-69','22-70'):   # 2026-10-21: 1922 plates 66-70 (Corryville, Avondale, Woodburn, Evanston), Ben's scans
        return (_ws.DATA + 'cufp/')+str(sheet)+'.jpg'
    if str(sheet).upper() in ('22-82A','22-83A','22-75','22-76','22-26A','22-26B','22-29','22-31','22-33','22-25','22-28','22-39','22-40'):   # 2026-10-23: 1922 plates 82A (central Norwood) and 83A (east Norwood); 2026-10-24: 75, 76; 2026-10-25: 26a, 26b, 29 (Price Hill); Ben's scans
        return (_ws.DATA + 'cufp/')+str(sheet).upper()+'.jpg'
    if str(sheet).startswith('22-'):
        n=int(str(sheet)[3:-1]); h=str(sheet)[-1].upper()
        g=glob.glob(ROOT+f'cincinnati_1922_v1/06645_01_1922-{n:04d}{h}.jpg')
        if g: return g[0]
        raise SystemExit(f'plate {sheet} not found')
    s=int(sheet)
    pats=[f'cincinnati_1904_v1/*_sheet_{s:04d}.jpg', f'cincinnati_1904_v2/*_sheet_{s:04d}.jpg', f'cincinnati_1904_v*/*-{s:04d}.jpg']
    for p in pats:
        g=glob.glob(ROOT+p)
        if g: return g[0]
    raise SystemExit(f'sheet {sheet} not found')
try: FNT=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',14)
except: FNT=ImageFont.load_default()
def render(sheet, box=None, out=None, maxpx=1200):
    im=Image.open(find(sheet)).convert('RGB'); W,H=im.size
    x0,y0,x1,y1=box or (0,0,W,H)
    c=im.crop((x0,y0,x1,y1)); s=min(maxpx/max(c.size),2.0)
    c=c.resize((max(1,int(c.size[0]*s)),max(1,int(c.size[1]*s))),Image.LANCZOS); d=ImageDraw.Draw(c)
    span=max(x1-x0,y1-y0); step=500 if span>2500 else (200 if span>1000 else (100 if span>400 else 50))
    for gx in range((x0//step+1)*step, x1, step):
        X=(gx-x0)*s; major=gx%(step*5)==0
        d.line([(X,0),(X,c.size[1])],fill=(255,0,0) if major else (255,140,140),width=1)
        d.text((X+2,2),str(gx),fill=(200,0,0),font=FNT)
    for gy in range((y0//step+1)*step, y1, step):
        Y=(gy-y0)*s; major=gy%(step*5)==0
        d.line([(0,Y),(c.size[0],Y)],fill=(255,0,0) if major else (255,140,140),width=1)
        d.text((2,Y+2),str(gy),fill=(200,0,0),font=FNT)
    c.save(out,quality=90); print('saved',out,'scale',round(s,3),'page',W,H)
def check(sheet,out,fn=None,box=None):
    im=Image.open(find(sheet)).convert('RGB'); W,H=im.size
    P=json.load(open(fn or (os.path.join(HERE,'picks22',f's{sheet}.json') if str(sheet).startswith('22-') else os.path.join(HERE,'picks',f's{int(sheet)}.json'))))
    ox,oy=0,0
    if box: im=im.crop(box); ox,oy=box[0],box[1]; W,H=im.size      # 2026-10-20: optional picks file and crop box
    s=1400/max(W,H); im=im.resize((int(W*s),int(H*s)),Image.LANCZOS); d=ImageDraw.Draw(im)
    for p in P.get('intersections',[]):
        x,y=(p['x']-ox)*s,(p['y']-oy)*s; d.ellipse([x-6,y-6,x+6,y+6],outline=(255,0,0),width=3); d.text((x+7,y-8),f"{p['a'][:10]}/{p['b'][:10]}",fill=(200,0,0),font=FNT)
    for a in P.get('alleys',[]):
        d.line([((a['x1']-ox)*s,(a['y1']-oy)*s),((a['x2']-ox)*s,(a['y2']-oy)*s)],fill=(0,0,255),width=3)
    for b in P.get('bends',[])+P.get('ends',[]):
        x,y=(b['x']-ox)*s,(b['y']-oy)*s; d.rectangle([x-5,y-5,x+5,y+5],outline=(0,150,0),width=3)
    im.save(out,quality=88); print('saved',out)
if __name__=='__main__':
    cmd=sys.argv[1]
    if cmd=='render':
        sh=sys.argv[2]
        if len(sys.argv)>=8: render(sh,tuple(int(v) for v in sys.argv[3:7]),sys.argv[7])
        else: render(sh,None,sys.argv[3])
    elif cmd=='check': check(sys.argv[2],sys.argv[3],sys.argv[4] if len(sys.argv)>4 else None,tuple(int(v) for v in sys.argv[5:9]) if len(sys.argv)>=9 else None)
    elif cmd=='size': print(Image.open(find(sys.argv[2])).size)
