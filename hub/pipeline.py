"""What the hub recomputes when a record changes, so the three views stay one design:

    deck/layout changed  ->  deck_tie: the Deck run headless (its own export) -> data/deck/rer_routes.geojson ->
                             tools/rer_deck_routes.py (every RER route and Metro line rebuilt on the Deck's pieces and
                             platforms where they drifted; saved profiles moved in the database) -> metro rails table ->
                             Profiles context  ->  then 3d
    alignments/*, config/*, params/metro_structure  ->  3d: tools/station3d/sync.py (both editors run headless on the hub's records) ->
                             snapshots/region in the database (the 3D view redraws) and params/registry

Jobs run one at a time in a worker thread; changes arriving while a job runs are coalesced into one more run.
"""
import glob
import json
import os
import re
import shutil
import subprocess
import sys
import threading
import time

HUB = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HUB)
WORK = os.path.join(HUB, 'work')
DEBOUNCE_S = 4.0
DECK_LAYERS = ('rer_line', 'rer_station', 'rer_platform', 'metro_line', 'metro_station', 'metro_platform')
PY = sys.executable


def trigger_for(path):
    if path == 'deck/layout':
        return 'deck_tie'
    if path.startswith(('alignments/', 'config/')) or path in ('params/metro_structure', 'chronology/segments'):
        return '3d'
    return None


class Pipeline:
    def __init__(self, store, auto=True):
        self.store, self.auto = store, auto
        self.pending = {}            # job -> (due time, reason)
        self.cv = threading.Condition()
        self.current = None
        store.listeners.append(self.on_event)
        threading.Thread(target=self.loop, daemon=True).start()

    # ---- scheduling ----
    def on_event(self, ev):
        if not self.auto or ev.get('t') != 'doc' or ev.get('by') in ('pipeline', 'test'):
            return
        job = trigger_for(ev['p'])
        if job:
            self.schedule(job, f"{ev['p']} changed")

    def schedule(self, job, reason, delay=DEBOUNCE_S):
        with self.cv:
            due = time.time() + delay
            prev = self.pending.get(job)
            self.pending[job] = (max(due, prev[0]) if prev else due, reason)
            self.cv.notify()

    def loop(self):
        while True:
            with self.cv:
                while True:
                    now = time.time()
                    ready = [(t, j) for j, (t, _) in self.pending.items() if t <= now]
                    if ready:
                        # the Deck tie first: the 3D snapshot depends on it
                        job = 'deck_tie' if any(j == 'deck_tie' for _, j in ready) else min(ready)[1]
                        reason = self.pending.pop(job)[1]
                        break
                    self.cv.wait(timeout=min([t - now for t, _ in self.pending.values()] + [3600]))
            self.current = job
            try:
                ok = self.run(job, reason)
                if ok and job == 'deck_tie':
                    self.schedule('3d', 'after the Deck tie', delay=0)
            finally:
                self.current = None

    # ---- running ----
    def run(self, job, reason):
        rid = self.store.run_start(job, reason)
        log = lambda s: self.store.run_log(rid, s if s.endswith('\n') else s + '\n')
        try:
            self.prepare()
            getattr(self, 'job_' + job)(log)
            self.store.run_end(rid, 'ok')
            return True
        except Exception as e:   # the run is marked failed, the hub carries on
            log(f'FAILED: {e!r}')
            self.store.run_end(rid, 'failed')
            return False

    def sh(self, log, args, ok=(0,)):
        log('$ ' + ' '.join(os.path.relpath(a, ROOT) if os.path.isabs(a) and a.startswith(ROOT) else os.path.basename(a) if a == PY else a for a in args))
        p = subprocess.run(args, cwd=ROOT, capture_output=True, text=True)
        out = (p.stdout + p.stderr).strip()
        if out:
            log(out[-6000:])
        if p.returncode not in ok:
            raise RuntimeError(f'{os.path.basename(args[1] if len(args) > 1 else args[0])} exited {p.returncode}')
        return p.returncode

    def prepare(self):
        """the work folder laid out as the Station 3D sync's cache, with the hub's records as the editors' databases"""
        os.makedirs(WORK, exist_ok=True)
        # links where the system allows them; copies otherwise (Windows without Developer Mode), refreshed every run
        def place(target, link):
            if os.path.lexists(link) and (os.path.islink(link) or os.path.isfile(link)):
                os.remove(link)
            elif os.path.isdir(link):
                shutil.rmtree(link)
            try:
                os.symlink(target, link, target_is_directory=os.path.isdir(target))
            except (OSError, NotImplementedError):
                (shutil.copytree if os.path.isdir(target) else shutil.copy2)(target, link)
        dl = os.path.join(WORK, 'deck')
        if not os.path.islink(dl):
            place(os.path.join(HUB, 'sites', 'deck'), dl)
        # the Profiles site: the repo's data/profile, its page as index.html (as published)
        pdir, src = os.path.join(WORK, 'profiles'), os.path.join(ROOT, 'data', 'profile')
        if os.path.islink(pdir):
            os.remove(pdir)
        os.makedirs(pdir, exist_ok=True)
        for name in os.listdir(src) + ['index.html']:
            link, target = os.path.join(pdir, name), os.path.join(src, 'profiles.html' if name == 'index.html' else name)
            if not os.path.islink(link):
                place(target, link)
        js = os.path.join(WORK, 'jsts', 'package', 'dist')
        os.makedirs(js, exist_ok=True)
        if not os.path.exists(os.path.join(js, 'jsts.min.js')):
            shutil.copy(os.path.join(HUB, 'static', 'vendor', 'jsts.min.js'), js)
        for sub, colls in (('profiles_db', ('alignments', 'config')), ('deck_db', ('deck',)), ('params_db', ('params', 'chronology'))):
            for c in colls:
                d = os.path.join(WORK, 'db', sub, c)
                shutil.rmtree(d, ignore_errors=True)
                os.makedirs(d)
                for r in self.store.list(c):
                    json.dump(r['data'], open(os.path.join(d, r['path'].split('/')[-1] + '.json'), 'w'), ensure_ascii=False)

    def job_deck_tie(self, log):
        jf, out = os.path.join(WORK, 'deck_job.json'), os.path.join(WORK, 'deck_out.json')
        json.dump({'lines': [], 'deck': True}, open(jf, 'w'))
        self.sh(log, ['node', os.path.join(ROOT, 'tools', 'station3d', 'harness.js'), WORK, jf, out])
        deck = json.load(open(out))['deck']
        fc = {'type': 'FeatureCollection', 'features': [f for f in deck['features'] if f['properties'].get('layer') in DECK_LAYERS]}
        json.dump(fc, open(os.path.join(ROOT, 'data', 'deck', 'rer_routes.geojson'), 'w'), separators=(',', ':'))
        log(f"Deck export: {len(fc['features'])} route, station and platform features")
        db = os.path.join(WORK, 'db', 'profiles_db', 'alignments')
        tool = os.path.join(ROOT, 'tools', 'rer_deck_routes.py')
        if self.sh(log, [PY, tool, '--db', db], ok=(0, 1)) == 0:
            log('Every route and platform matches the Deck: nothing to move')
            return
        self.sh(log, [PY, tool, '--apply', '--db', db])
        moved = 0
        for f in glob.glob(os.path.join(db, '*.json')):
            p = 'alignments/' + os.path.basename(f)[:-5]
            cur = self.store.get(p)
            new = json.load(open(f))
            if cur is None or cur['data'] != new:
                self.store.set(p, new, by='pipeline', if_version=cur['version'] if cur else None)
                moved += 1
        log(f'{moved} saved profiles moved')
        self.sh(log, [PY, '-c', 'import sys, json; sys.path.insert(0, "tools"); import make_rer_profile_lines as m; '
                      'open("data/profile/rer/metro_rails.json", "w").write(json.dumps(m.metro_rails(), separators=(",", ":")))'])
        self.sh(log, [PY, os.path.join(ROOT, 'tools', 'make_profile_context.py')])
        self.sh(log, [PY, os.path.join(ROOT, 'tools', 'chronology.py')])   # the Chronology view's routes
        self.store.emit({'t': 'files', 'site': 'profiles'})
        self.store.emit({'t': 'files', 'site': 'chronology'})

    def job_3d(self, log):
        out = os.path.join(WORK, 'snapshot.json')
        self.sh(log, [PY, os.path.join(ROOT, 'tools', 'station3d', 'sync.py'), '--cache', WORK, '--out', out])
        dd = os.path.join(WORK, 'db_out')
        meta = json.load(open(os.path.join(dd, 'meta.json')))
        for name in meta['parts']:
            self.store.set('snapshots/region/parts/' + name, json.load(open(os.path.join(dd, name + '.json'))), by='pipeline', quiet=True)
        for p in self.store.paths('snapshots/region/parts/'):
            if p.rsplit('/', 1)[1] not in meta['parts']:
                self.store.delete(p, by='pipeline', quiet=True)
        self.store.set('snapshots/region', meta, by='pipeline')   # last: open 3D views redraw
        snap = json.load(open(out))
        self.store.set('params/registry', registry(snap, self.store), by='pipeline')
        # the Profiles structure type at each Metro station, for the Deck's island default; a change redraws the Deck's
        # platforms, so the 3D map is built once more with them
        # each viaduct a selection of its own on the Deck (its RER A viaducts from the Profiles' elevated stretches)
        self.sh(log, [PY, os.path.join(ROOT, 'tools', 'viaduct_parts.py'), os.path.join(WORK, 'harness_out.json')])
        self.store.emit({'t': 'files', 'site': 'deck'})
        tp = snap.get('tube_points')   # the bored tube along each Metro line, for the Deck's track spacing
        cur = self.store.get('params/tube_points')
        if tp and (cur is None or cur['data'] != tp):
            self.store.set('params/tube_points', tp, by='pipeline')
        st = snap.get('station_types')
        cur = self.store.get('params/station_types')
        if st and (cur is None or cur['data'] != st):
            self.store.set('params/station_types', st, by='pipeline')
            if not getattr(self, '_types_rerun', False):
                self._types_rerun = True
                self.schedule('3d', 'station types changed: the Deck redraws its platforms', delay=0)
                log('Station types changed: the 3D map is built once more')
                return
        self._types_rerun = False
        log(f"Snapshot: {len(meta['parts'])} parts, {len(snap['issues'])} issues")


# ---- the parameter registry: each shared parameter as every view has it ----
def js_object(html, name):
    m = re.search(r'const ' + name + r' = (\{[^;]*\});', html)
    if not m:
        return {}
    return json.loads(re.sub(r'([{,]\s*)([A-Za-z_]\w*)\s*:', r'\1"\2":', m.group(1)))


def deck_platform_lengths():
    """the platform length the Deck draws, per system: the median over its island platforms (centred on the track pair,
    so a curve does not lengthen or shorten them), and how many come out at each whole metre"""
    from collections import Counter
    sys.path.insert(0, os.path.join(ROOT, 'tools'))
    from rer_deck_routes import TO_UTM
    out = {'metro': [], 'rer': []}
    for f in json.load(open(os.path.join(ROOT, 'data', 'deck', 'rer_routes.geojson')))['features']:
        p, g = f['properties'], f['geometry']
        if p.get('layer') not in ('metro_platform', 'rer_platform') or g['type'] != 'Polygon' or p.get('type') != 'island':
            continue
        c = [TO_UTM.transform(*q[:2]) for q in g['coordinates'][0]]
        e = [((c[i][0] - c[i + 1][0]) ** 2 + (c[i][1] - c[i + 1][1]) ** 2) ** 0.5 for i in range(len(c) - 1)]
        if len(e) < 4 or len(e) % 2:
            continue
        # the Deck draws a platform as one long side out and the other back: its two ends are the middle and last edges
        out['metro' if p['layer'] == 'metro_platform' else 'rer'].append((sum(e) - e[len(e) // 2 - 1] - e[-1]) / 2)
    res = {}
    for k, v in out.items():
        v.sort()
        res[k] = round(v[len(v) // 2], 2) if v else None
        res[k + '_counts'] = ', '.join(f'{n} at {m} m' for m, n in Counter(round(x) for x in v).most_common(3))
    return res


def registry(snap, store):
    html = open(os.path.join(ROOT, 'data', 'profile', 'profiles.html'), encoding='utf8').read()
    prof = {'metro': js_object(html, 'METRO_DEFAULTS'), 'rer': js_object(html, 'RER_DEFAULTS')}
    for k, doc in (('metro', 'config/settings'), ('rer', 'config/settings_rer')):
        r = store.get(doc)
        if r:
            prof[k].update(r['data'])
    dr = snap.get('deck_rules') or {}
    dl = deck_platform_lengths()
    rows = []

    def row(name, unit, note=None, **vals):
        v = [x for x in vals.values() if isinstance(x, (int, float))]
        rows.append({'name': name, 'unit': unit, 'values': vals, 'note': note, 'agree': (max(v) - min(v) <= 0.5) if len(v) > 1 else None})
    for k, lab in (('metro', 'Metro'), ('rer', 'RER')):
        row(f'{lab} platform length', 'm', note=f"Deck island platforms: {dl.get(k + '_counts')}", profiles=prof[k].get('platform'), deck=dl.get(k), station3d=(snap.get('platform_m') or {}).get(k))
        row(f'{lab} island platform width', 'm', deck=((dr.get('PW') or {}).get(k) or {}).get('island'))
        row(f'{lab} side platform width', 'm', deck=((dr.get('PW') or {}).get(k) or {}).get('side'))
        row(f'{lab} default station rail depth', 'm', profiles=prof[k].get('defDepth'))
        row(f'{lab} maximum grade', 'per mille', profiles=prof[k].get('maxGrade'))
        row(f'{lab} platform grade limit', 'per mille', profiles=prof[k].get('stationMaxGrade'))
        row(f'{lab} vertical curve radius', 'm', profiles=prof[k].get('vcRadius'))
        row(f'{lab} box wall outside the outer track', 'm', station3d=(snap.get('box_margin') or {}).get(k))
        row(f'{lab} platform top above rail', 'm', station3d=(snap.get('platform_above_rail') or {}).get(k))
    ms = (store.get('params/metro_structure') or {}).get('data') or {}
    if ms:   # one record read by all three views (Metro structure, hub page): the same value in each
        for name, key in (('type A tubes', 'A'), ('type C tubes', 'C'), ('double-track bore', 'bore')):
            v = ms['tubes'][key]['spacing']
            row(f'Metro track centres, {name}', 'm', note='the structure record', profiles=v, deck=v, station3d=v)
        row('Metro track centres, box', 'm', note='the structure record', profiles=ms['box']['spacing'], deck=ms['box']['spacing'], station3d=ms['box']['spacing'])
        row('Metro track centres at an island', 'm', note='the structure record', deck=ms['island_box']['spacing'], station3d=ms['island_box']['spacing'])
        row('Metro clear height under structures in the open', 'm', note='the structure record', profiles=ms['open_clear_height'])
    row('Platform slide limit (Deck)', 'm', deck=dr.get('SLIDE_M'))
    tie = [i for i in snap.get('issues', []) if "off the Deck's pieces" in i or "off their Deck platform" in i]
    # notes to check, not errors: side platforms on bored stretches (Ben, 28 October)
    checks = [{'line': x['line'], 'station': x['station'], 'text': f"side platforms on a bored stretch ({'deep tube' if x['type'] == 'deep' else 'shallow shield'}, {x['tube']} tunnel)"}
              for x in (snap.get('approach') or {}).get('side_bored', [])]
    return {'rows': rows, 'tie_issues': tie, 'checks': checks, 'synced_at': snap.get('synced_at'),
            'note': 'Profiles values are its settings (config/settings, config/settings_rer) over its built-in defaults; Deck values are its constants as its own code has them, and platform lengths measured from the platforms it draws; Station 3D values are sync.py constants.'}
