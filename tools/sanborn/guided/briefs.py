"""Reader briefs for the guided passes (14 November 2026).

    python briefs.py N KIND CROPDIR BRIEFDIR [PER]      KIND: trace | ends | review
Writes BRIEFDIR/<N>_<KIND>_<A|B>_<k>.txt; each brief names the output file picks22_guided/22-N/<KIND>_<A|B>_<k>.json.
Readers A and B get the same items and the same crops; each works alone and must not open the other's file.
"""
import json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import streets as S  # noqa: E402
N, KIND, CROPS, BD = sys.argv[1], sys.argv[2], sys.argv[3].rstrip('/') + '/', sys.argv[4].rstrip('/') + '/'
PER = int(sys.argv[5]) if len(sys.argv) > 5 else 25
ROUND = os.environ.get('ROUND', '')
OUT = S.SP.replace('\\', '/') + f'picks22_guided/22-{N}/'; os.makedirs(BD, exist_ok=True)
COMMON = """You are reading a 1922 Sanborn fire-insurance plate of Cincinnati (plate {N}). Each image is a piece of the scan shown enlarged, with a red grid in ORIGINAL plate pixels and the plate coordinates printed along the top (x) and left (y) edges; read positions off that grid to about 5 plate pixels.

On these plates a street is the open strip between two block lines (the lines the lots and house numbers sit against), usually 50-120 plate pixels wide. Lines drawn INSIDE a street are not its edges: water pipes, dashed sewers, car tracks, the street's name, house numbers. A street's centre line is midway between its two block lines. Where a street runs along the edge of the plate and only one block line is drawn, use the printed width or the car tracks to place the centre, and say so in the note. Railroads, sidings, the canal, creeks, cemetery and park drives, lot lines and property boundaries are not streets.

The names given are TODAY's names. The 1922 plate may print an older name, part of a name, or none. Copy what the plate prints on the street in this image into "printed" (as printed, e.g. "BROERMAN AVE."), or leave it empty if nothing is printed on it here.

Work only from the images listed below. Do not open any other file, and do not open any .json file except to write your own.

"""
TRACE = """For each item, the image is centred on a red cross, placed where today's street of that name would run. Find that street on the plate near the cross (the stated direction tells you which way it runs) and mark the point on its centre line nearest the cross. If no street is drawn there (the ground is a block, yard, estate, cemetery, railroad, canal or creek), record found = false and say what is there. Do not move to a different street: if the only street near the cross is plainly another one (it runs the other way, or carries another name), record found = false and say so.

ITEMS:
{items}

OUTPUT: write {out} (plain UTF-8, no byte-order mark): a JSON list with one object per item, in order:
  {{"id": "...", "found": true, "x": 1234, "y": 5678, "sure": "high" | "medium" | "low", "printed": "", "note": ""}}
(for found = false leave x and y out and put what is there in note). Then reply with one line: how many found and how many not."""
ENDS = """For each item, a red cross marks a point on the centre line of the named street. Follow that street from the cross in the stated direction and find where it ends on the plate: where its centre line meets the street it runs into, or stops at a block line, a property line, a railroad, the canal, a creek, or the edge of the plate. If it runs out of the image still going, it has not ended in this image.

ITEMS:
{items}

OUTPUT: write {out} (plain UTF-8, no byte-order mark): a JSON list with one object per item, in order:
  {{"id": "...", "ends": true, "x": 1234, "y": 5678, "at": "what it ends at (e.g. meets Ross Avenue / block line / railroad / plate edge)", "sure": "high" | "medium" | "low", "printed": "", "note": ""}}
or, if it runs out of the image: {{"id": "...", "ends": false, "x": ..., "y": ..., "printed": "", "note": ""}} with x, y the last point of its centre line you can place, near the image edge. Then reply with one line: how many end in the image and how many run on."""
REVIEW = """Each image is one section of the plate at reduced size, with street centre lines already drawn on it: red lines are this plate's streets, blue lines are streets already on the map from other sources. Find what the drawing gets wrong in the section:
1. MISSING: a street printed on the plate (an open strip between block lines, usually with a printed name, house numbers or a printed width) that has no line on it, or a stretch of a street the drawn line stops short of. For each, give its printed name ("" if none) and 3 to 8 points along its centre line from one end to the other (plate coordinates), and what each end meets.
2. WRONG: a drawn line with no street under it, or one that runs more than about half a street's width off the printed street. Give a point on the line and say what is wrong.
Alleys under about 20 ft wide count only if the plate names them. Streets cut by the edge of the section continue in the neighbouring section; report the part in yours.

ITEMS:
{items}

OUTPUT: write {out} (plain UTF-8, no byte-order mark): a JSON object
  {{"missing": [{{"section": "...", "printed": "...", "points": [[x, y], ...], "start_at": "...", "end_at": "...", "sure": "high" | "medium" | "low"}}], "wrong": [{{"section": "...", "x": 0, "y": 0, "what": "..."}}]}}
Then reply with one line: how many missing and how many wrong."""
if KIND == 'trace':
    rows = json.load(open(OUT + 'trace.json', encoding='utf8')); tpl = TRACE; sub = 't'
    item = lambda r: f"{r['id']}: {r['name']}, running {r['runs']} in the image. Image {CROPS}{sub}/{r['id']}.jpg (plate x {r['box'][0]}-{r['box'][2]}, y {r['box'][1]}-{r['box'][3]}); red cross at about ({int(r['pred'][0])}, {int(r['pred'][1])})."
elif KIND == 'ends':
    rows = [r for r in json.load(open(OUT + 'ends.json', encoding='utf8')) if not ROUND or str(r.get('round', 1)) == ROUND]; tpl = ENDS; sub = 'e'
    item = lambda r: f"{r['id']}: {r['name']}, from the red cross at about ({int(r['from_px'][0])}, {int(r['from_px'][1])}) toward the {r['toward']}. Image {CROPS}{sub}/{r['id']}.jpg (plate x {r['box'][0]}-{r['box'][2]}, y {r['box'][1]}-{r['box'][3]})."
else:
    rows = json.load(open(OUT + 'review.json', encoding='utf8')); tpl = REVIEW; sub = 'r'
    item = lambda r: f"section {r['id']}: image {CROPS}{sub}/{r['id']}.jpg (plate x {r['box'][0]}-{r['box'][2]}, y {r['box'][1]}-{r['box'][3]})."
tag = KIND + (ROUND if KIND == 'ends' and ROUND else '')
for R in 'AB':
    for k in range(0, len(rows), PER):
        part = rows[k:k + PER]; b = k // PER + 1
        out = OUT + f'{tag}_{R}_{b}.json'
        t = COMMON.format(N=N) + tpl.format(items='\n'.join(item(r) for r in part), out=out)
        open(BD + f'{N}_{tag}_{R}_{b}.txt', 'w', encoding='utf8', newline='\n').write(t)
print(KIND, len(rows), 'items,', -(-len(rows) // PER), 'briefs per reader')
