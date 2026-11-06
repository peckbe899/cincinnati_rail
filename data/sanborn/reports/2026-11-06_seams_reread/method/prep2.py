"""Part 1 regions: 22-67 top (the junction where Hewitt and the MONT. branch leave the avenue), 22-75 bottom edge at Brewster."""
import json, os, sys
from PIL import Image
Image.MAX_IMAGE_PIXELS = None
REPO = r'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D'
sys.path.insert(0, REPO + '/tools/sanborn'); import _ws  # noqa
sys.path.insert(0, _ws.CODE + 'cuf'); import plates as PL  # noqa
HERE = os.path.dirname(os.path.abspath(__file__))
M = json.load(open(HERE + '/regions.json', encoding='utf8'))
NEW = {'t01b_67': ('22-67', [4300, 0, 7300, 1500], ['Gilbert Avenue', 'Woodburn Avenue']),
       't13b_75': ('22-75', [7585, 6126, 9585, 7170], ['Brewster Avenue', 'Montgomery Road'])}
for j, (pid, box, st) in NEW.items():
    im = Image.open(PL.PNGPATH.get(pid[3:], _ws.ext(f'/mnt/user-data/uploads/PNG/{pid[3:]}.png')))
    if im.mode in ('RGBA', 'LA', 'P'):
        im = im.convert('RGBA'); bg = Image.new('RGBA', im.size, (255, 255, 255, 255)); bg.alpha_composite(im); im = bg
    im = im.convert('RGB'); W, H = im.size; box = [max(0, box[0]), max(0, box[1]), min(W, box[2]), min(H, box[3])]
    im.crop(tuple(box)).save(f'{HERE}/regions/{j}.png')
    M[j] = dict(tie=int(j[1:3]), plate=pid, streets=st, box=box, size=[W, H], round=2)
    print(j, pid, box)
json.dump(M, open(HERE + '/regions.json', 'w', encoding='utf8', newline='\n'), indent=1)
