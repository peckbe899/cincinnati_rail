import sys,os
for f in "bench44 blocks_noguide ink_bins outlines run_plates street_map map_area".split():
    a=open("fresh/tools/sanborn/unet/%s.py"%f,'rb').read(); b=open("../staged/tools/sanborn/unet/%s.py"%f,'rb').read()
    print(f, len(a), len(b), a.count(b'\r\n'), b.count(b'\r\n'), a==b, a.replace(b'\r\n',b'\n')==b.replace(b'\r\n',b'\n'))
d=open("../staged.diff",'rb').read(); print("diff crlf", d.count(b'\r\n'), d.count(b'\n'))
