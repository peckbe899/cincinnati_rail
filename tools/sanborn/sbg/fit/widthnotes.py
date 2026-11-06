"""Positional width notes on the Sanborn width picks ("40' north of West 5th", "printed 50' east of McLean",
"the part north of Harrison is 40'", "printed 50' between Liberty and Wade") turned into conditions on a crossing street.
Returns (main_condition or None, [(ft, condition), ...]); a condition is ('north'|'south'|'east'|'west', street) or
('between', street1, street2). Notes about market spaces or ranges ("Broadway to the bend east of Ludlow") give nothing."""
try: import _ws  # Sanborn paths: tools/sanborn/_ws.py, configs/sanborn_paths.json (was the Topography workspace scratchpad and the chat uploads)
except ImportError: import os as _o, sys as _s; _s.path.append(_o.path.normpath(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..', '..'))); import _ws
import re
SIDE = r'(north|south|east|west)'
NAME = r"([A-Z][A-Za-z0-9\.' ]*?)"
END = r"(?=\s*(?:[;,()]|$| is | and | along | the | for |\s+\(|$))"
def ft_of(t):
    m = re.match(r"(\d+(?:\.\d+)?)'(?:\s*(\d+)\")?", t)
    return float(m.group(1)) + (float(m.group(2)) / 12 if m.group(2) else 0) if m else None
def parse(note, ft=None):
    if not note or 'market' in note.lower() or ' to the ' in note or 'bend' in note.lower(): return None, []
    main = None; extra = []
    clauses = [c.strip() for c in re.split(r';', note) if c.strip()]
    for ci, c in enumerate(clauses):
        m = re.search(r"printed\s+(\d+(?:\.\d+)?'(?:\s*\d+\")?)\s+between\s+" + NAME + r"\s+and\s+" + NAME + END, c)
        if m: extra.append((ft_of(m.group(1)), ('between', m.group(2).strip(), m.group(3).strip()))); continue
        m = re.search(SIDE + r" of " + NAME + r" is (?:printed |labelled )?(\d+(?:\.\d+)?'(?:\s*\d+\")?)", c)
        if m: extra.append((ft_of(m.group(3)), (m.group(1), m.group(2).strip()))); continue
        m = re.search(r"(\d+(?:\.\d+)?'(?:\s*\d+\")?)[^;]*?\b" + SIDE + r" of " + NAME + END, c)
        if m and not re.search(r'\bfrom\b', c[:m.start(2)]):
            f = ft_of(m.group(1)); cond = (m.group(2), m.group(3).strip())
            if ci == 0 and c.startswith(m.group(1)) and ft is not None and abs(f - ft) < 0.01: main = cond
            extra.append((f, cond)); continue
        m = re.match(SIDE + r" of " + NAME + END, c)
        if m and ci == 0: main = (m.group(1), m.group(2).strip())
    return main, extra
if __name__ == '__main__':
    import json, glob
    for fn in sorted(glob.glob((_ws.DATA + 'sbg/picks/s*.json'))):
        d = json.load(open(fn))
        for w in d.get('widths', []):
            mn, ex = parse(w.get('note', ''), w.get('ft'))
            if mn or ex: print(d['sheet'], w['street'], w['ft'], '| main', mn, '| extra', ex, '|', w.get('note', '')[:80])
