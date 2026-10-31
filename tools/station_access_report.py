"""Station access at opening for every Metro station (Station_Access_and_Mezzanines_by_Phase, Ben 31 October), from the
Python copy of the Rail Profiles rules: the type (rules or Ben's), year, phase, depth against D_HALL, platform type, the
interchanges at opening and the later stages proposed from them, and the flags.

    python tools/station_access_report.py [--out params/station_access_rule.json] [--seed DIR]

Writes the record the hub keeps as params/station_access_rule (read by the hub's Access page) and prints Ben's report:
the count of each type by phase, the rule 4 stations (an island or interchange shallower than D_HALL), every proposed
later stage with its trigger and year, and the stations with no year.
"""
import argparse
import json
import os
import sys
from collections import Counter

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, ROOT)
from railsim.metro_profile import MetroProfile, ACCESS_TYPES   # noqa: E402

LABEL = {'surface': 'Surface station', 'platform_level': 'Platform level', 'platform_level_xu': 'Platform level, crossunder',
         'end_halls': 'End ticket halls', 'mezzanine': 'Mezzanine', 'mezzanine_full': 'Full-length mezzanine',
         'mined_hall': 'Street hall, mined station', 'deep': 'Deep station'}


def proposed_stages(a, mp):
    """later stages from the document's triggers: another Metro line opening at the station later (above or below), a
    TRI line opening there; accessibility (no year) at platform-level stations"""
    out = []
    for m in a['later']:
        if m.get('sys') == 'rer' or str(m.get('line', '')).startswith('RER_'):
            out.append({'year': m['year'], 'trigger': f"a TRI line opens here ({m['line']})", 'proposed': 'a hall level for TRI, joined to the Metro access', 'source': 'rule'})
        else:
            out.append({'year': m['year'], 'trigger': f"another Metro line opens here ({m['line']} {m['station']})",
                        'proposed': ('halls at this level beside the box, over the new line (they are its mezzanine)' if a['type'] in ('platform_level', 'platform_level_xu')
                                     else 'the new line gets its own access type, plus stairs between the two platform levels'), 'source': 'rule'})
    if a['type'] in ('platform_level', 'platform_level_xu'):
        out.append({'year': None, 'trigger': 'accessibility', 'proposed': 'one street elevator per platform side; no mezzanine', 'source': 'rule'})
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', default=None, help='the params/station_access_rule record (JSON); default: print only')
    ap.add_argument('--seed', default=os.path.join(ROOT, 'hub', 'seed', 'alignments'))
    a = ap.parse_args()
    prof = os.path.join(ROOT, 'data', 'profile')
    ids = [l['id'] for l in json.load(open(os.path.join(prof, 'lines', 'index.json')))]
    rec, rows = {}, []
    for lid in ids:
        al = os.path.join(a.seed, lid + '.json')
        mp = MetroProfile.load(os.path.join(prof, 'lines', lid + '.json'), al if os.path.exists(al) else None, os.path.join(prof, 'settings.json'))
        if mp.is_rer or not mp.ms:
            continue
        rec[lid] = {}
        for s in mp.stations:
            x = mp.station_access(s)
            x['proposed'] = proposed_stages(x, mp)
            x['line'] = lid
            x['c'] = round(float(s['c']), 1)
            rec[lid][s['name']] = x
            rows.append(x)
    if a.out:
        os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
        json.dump(rec, open(a.out, 'w'), separators=(',', ':'), ensure_ascii=False)
    by = Counter((r['phase'], r['type']) for r in rows)
    print(f"{len(rows)} Metro stations")
    for ph in ('1', '2', '3', 'later'):
        n = sum(v for (p, t), v in by.items() if p == ph)
        if n:
            print(f"  Phase {ph}: {n}: " + ', '.join(f"{LABEL[t]} {v}" for (p, t), v in sorted(by.items(), key=lambda kv: -kv[1]) if p == ph))
    tot = Counter(r['type'] for r in rows)
    print('  all: ' + ', '.join(f"{LABEL[t]} {tot[t]}" for t in ACCESS_TYPES if tot[t]) + f" (sum {sum(tot.values())})")
    r4 = [r for r in rows if r['rule'] == 'platform_level_xu']
    print(f"rule 4, an island or interchange shallower than D_HALL ({len(r4)}): " + '; '.join(f"{r['line']} {r['station']} {r['depth']} m {'island' if r['island'] else 'side'}" for r in r4[:40]) + (' ...' if len(r4) > 40 else ''))
    st = [(r, p) for r in rows for p in r['proposed'] if p['year'] is not None]
    print(f"proposed later stages ({len(st)}): " + '; '.join(f"{r['line']} {r['station']} {p['year']}: {p['trigger']}" for r, p in st[:40]) + (' ...' if len(st) > 40 else ''))
    ny = [r for r in rows if r['year'] is None and r['type'] != 'surface']
    print(f"no opening year ({len(ny)}): " + ', '.join(f"{r['line']} {r['station']}" for r in ny[:40]) + (' ...' if len(ny) > 40 else ''))
    errs = [(r, f) for r in rows for f in r['flags'] if f['sev'] == 'error']
    print(f"errors ({len(errs)}): " + '; '.join(f"{r['line']} {r['station']}: {f['kind']}" for r, f in errs[:20]))


if __name__ == '__main__':
    main()
