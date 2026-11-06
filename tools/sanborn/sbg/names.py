import re
ORD={'first':'1st','second':'2nd','third':'3rd','fourth':'4th','fifth':'5th','sixth':'6th','seventh':'7th','eighth':'8th','ninth':'9th','tenth':'10th',
     'eleventh':'11th','twelfth':'12th','thirteenth':'13th','fourteenth':'14th','fifteenth':'15th'}
SUF={'street':'','st':'','avenue':'','av':'','ave':'','alley':'al','al':'al','place':'pl','pl':'pl','court':'ct','ct':'ct','lane':'','terrace':'ter','road':'rd','square':'sq'}
def key(name):
    """canonical key for matching: lower, no parenthetical notes, ordinals as digits, suffix reduced, keeps east/west"""
    if not name: return ''
    n=name.lower()
    n=re.sub(r'\(.*?\)','',n)
    n=n.replace("'",'').replace('.',' ').replace(',',' ')
    w=[ORD.get(t,t) for t in n.split()]
    w=[{'w':'west','e':'east','n':'north','s':'south'}.get(t,t) for t in w]
    if w and w[-1] in SUF:
        s=SUF[w[-1]]; w=w[:-1]+([s] if s else [])
    return ' '.join(w).strip()
def base(k):
    """key without east/west/north/south prefix (for OSM matching of streets whose prefix changed)"""
    w=k.split()
    if w and w[0] in ('west','east','north','south') and len(w)>1: w=w[1:]
    return ' '.join(w)
QUAL=('east of','west of','south of','north of','section','roadway',' to ','e.n.','e.s.','leg')
UNNAMED={'','?','al','unnamed al','unnamed','alley','unnamed street'}
def key2(name):
    """identity key for ties and street building: keeps qualifiers that mark a separate (jogged) piece; None if unnamed"""
    if name is None: return None
    k=key(name)
    if k in UNNAMED or name.lower().startswith('unnamed') or '?' in name: return None
    m=re.search(r'\((.*?)\)',name)
    if m:
        q=m.group(1).lower()
        if any(t in q for t in QUAL): return k+' | '+q
    return k
