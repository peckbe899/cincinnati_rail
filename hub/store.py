"""The hub's one database: every record the three views keep (the Deck's layout, the Rail Profiles' saved profiles and
settings, the Station 3D snapshot and views) plus the hub's own (parameters, roadmap, pipeline runs), in one SQLite
file. Records are addressed as the pages address them in their artifact databases: "collection/doc" paths such as
deck/layout, alignments/Line_1, snapshots/region/parts/lines-0."""
import json
import os
import sqlite3
import sys
import threading
import time

HISTORY_KEEP = 50                 # earlier versions kept per record (undo, audit)
NO_HISTORY = ('snapshots/',)      # derived records: no history


def coll_of(path):
    return path.rsplit('/', 1)[0] if '/' in path else ''


class Store:
    def __init__(self, path):
        self.path = path
        self.lock = threading.RLock()
        self.db = sqlite3.connect(path, check_same_thread=False)
        self.db.execute('pragma journal_mode=wal')
        self.db.executescript('''
            create table if not exists docs (path text primary key, coll text not null, data text not null,
                version integer not null, updated real not null, by text);
            create index if not exists docs_coll on docs(coll);
            create table if not exists history (path text not null, version integer not null, data text not null,
                updated real not null, by text, primary key (path, version));
            create table if not exists seed_base (path text primary key, data text not null);
            create table if not exists runs (id integer primary key autoincrement, job text not null, state text not null,
                started real, finished real, reason text, log text);
        ''')
        self.listeners = []   # callables(event dict)

    # ---- records ----
    def get(self, path):
        with self.lock:
            r = self.db.execute('select data, version, updated, by from docs where path=?', (path,)).fetchone()
        return None if r is None else {'path': path, 'data': json.loads(r[0]), 'version': r[1], 'updated': r[2], 'by': r[3]}

    def list(self, coll):
        with self.lock:
            rows = self.db.execute('select path, data, version, updated, by from docs where coll=? order by path', (coll,)).fetchall()
        return [{'path': p, 'data': json.loads(d), 'version': v, 'updated': u, 'by': b} for p, d, v, u, b in rows]

    def paths(self, prefix=''):
        with self.lock:
            return [r[0] for r in self.db.execute('select path from docs where path like ? order by path', (prefix + '%',))]

    def set(self, path, data, by='page', if_version=None, quiet=False):
        """replace a record; returns its new version (None if if_version no longer matches)"""
        text = json.dumps(data, separators=(',', ':'), ensure_ascii=False)
        with self.lock:
            cur = self.db.execute('select data, version, updated, by from docs where path=?', (path,)).fetchone()
            if if_version is not None and (cur[1] if cur else 0) != if_version:
                return None
            if cur and cur[0] == text:
                return cur[1]
            v = (cur[1] if cur else 0) + 1
            now = time.time()
            if cur and not path.startswith(NO_HISTORY):
                self.db.execute('insert or replace into history values (?,?,?,?,?)', (path, cur[1], cur[0], cur[2], cur[3]))
                self.db.execute('delete from history where path=? and version<=?', (path, cur[1] - HISTORY_KEEP))
            self.db.execute('insert or replace into docs values (?,?,?,?,?,?)', (path, coll_of(path), text, v, now, by))
            self.db.commit()
        if not quiet:
            self.emit({'t': 'doc', 'p': path, 'v': v, 'by': by})
        return v

    def update(self, path, data, by='page'):
        """merge keys into a record; the read and the write under one lock, so two saves at once cannot lose one"""
        with self.lock:
            cur = self.get(path)
            merged = dict(cur['data']) if cur else {}
            for k, val in data.items():
                if isinstance(val, dict) and val.get('__delete__') is True:
                    merged.pop(k, None)
                else:
                    merged[k] = val
            return self.set(path, merged, by)

    def delete(self, path, by='page', quiet=False):
        with self.lock:
            cur = self.db.execute('select data, version, updated, by from docs where path=?', (path,)).fetchone()
            if not cur:
                return False
            if not path.startswith(NO_HISTORY):
                self.db.execute('insert or replace into history values (?,?,?,?,?)', (path, cur[1], cur[0], cur[2], cur[3]))
            self.db.execute('delete from docs where path=?', (path,))
            self.db.commit()
        if not quiet:
            self.emit({'t': 'doc', 'p': path, 'v': None, 'by': by})
        return True

    def history(self, path):
        with self.lock:
            rows = self.db.execute('select version, updated, by from history where path=? order by version desc', (path,)).fetchall()
        return [{'version': v, 'updated': u, 'by': b} for v, u, b in rows]

    def restore(self, path, version, by='hub'):
        with self.lock:
            r = self.db.execute('select data from history where path=? and version=?', (path, version)).fetchone()
        return None if r is None else self.set(path, json.loads(r[0]), by)

    # ---- pipeline runs ----
    def run_start(self, job, reason):
        with self.lock:
            c = self.db.execute('insert into runs (job, state, started, reason, log) values (?,?,?,?,?)', (job, 'running', time.time(), reason, ''))
            self.db.commit()
            rid = c.lastrowid
        self.emit({'t': 'run', 'id': rid, 'job': job, 'state': 'running'})
        return rid

    def run_log(self, rid, text):
        with self.lock:
            self.db.execute('update runs set log = log || ? where id=?', (text, rid))
            self.db.commit()

    def run_end(self, rid, state):
        with self.lock:
            self.db.execute('update runs set state=?, finished=? where id=?', (state, time.time(), rid))
            self.db.commit()
            job = self.db.execute('select job from runs where id=?', (rid,)).fetchone()[0]
        self.emit({'t': 'run', 'id': rid, 'job': job, 'state': state})

    def runs(self, n=20):
        with self.lock:
            rows = self.db.execute('select id, job, state, started, finished, reason, substr(log, -4000) from runs order by id desc limit ?', (n,)).fetchall()
        return [dict(zip(('id', 'job', 'state', 'started', 'finished', 'reason', 'log'), r)) for r in rows]

    # ---- events ----
    def emit(self, ev):
        for f in list(self.listeners):
            try:
                f(ev)
            except Exception as e:   # a listener's fault is reported, not hidden; the others still hear the event
                print(f'hub: listener failed on {ev}: {e!r}', file=sys.stderr)

    # ---- seed and export (the git-tracked copy of the records) ----
    def load_dir(self, root, by='seed'):
        """every root/<collection path>/<doc>.json as a record (skips records already present)"""
        n = 0
        for dirpath, _, files in os.walk(root):
            for f in sorted(files):
                if not f.endswith('.json'):
                    continue
                rel = os.path.relpath(os.path.join(dirpath, f), root)[:-5].replace(os.sep, '/')
                if self.get(rel) is None:
                    self.set(rel, json.load(open(os.path.join(dirpath, f), encoding='utf8')), by, quiet=True)
                    n += 1
        return n

    # the seed as this database last saw it (taken in or exported): the common base for merging a newer seed
    def _base_get(self, path):
        with self.lock:
            r = self.db.execute('select data from seed_base where path=?', (path,)).fetchone()
        return None if r is None else json.loads(r[0])

    def _base_set(self, path, data):
        with self.lock:
            self.db.execute('insert or replace into seed_base values (?,?)', (path, json.dumps(data, separators=(',', ':'), ensure_ascii=False)))
            self.db.commit()

    def _seed_history(self, path):
        """earlier versions of a record written from the seed (newest first): candidate bases"""
        with self.lock:
            rows = self.db.execute("select data from history where path=? and by='seed' order by version desc", (path,)).fetchall()
        return [json.loads(r[0]) for r in rows]

    def merge_dir(self, root, git_versions=None):
        """take a newer seed (pulled from git) into this database without losing local edits.
        Per record: missing here -> added; unchanged here since the seed it came from -> replaced by the new seed;
        changed here and not in the seed -> kept; changed on both sides -> merged key by key (two levels deep, e.g.
        the Deck layout's streets/blocks/stations edits), a key changed differently on both sides keeps the local value
        and is listed as a conflict. The base is the seed this database last took in or exported, else an earlier
        seed version in the record's history, else a git version of the seed file that this database once held.
        Returns {added, updated, merged, kept, conflicts: [{path, keys}]}."""
        rep = {'added': [], 'updated': [], 'merged': [], 'kept': [], 'conflicts': []}
        same = lambda a, b: json.dumps(a, sort_keys=True) == json.dumps(b, sort_keys=True)

        def merge(l, s_, b, at, out):
            if same(l, b):
                return s_
            if same(s_, b) or same(l, s_):
                return l
            if isinstance(l, dict) and isinstance(s_, dict) and isinstance(b, dict) and at < 2:
                m = {}
                for k in set(l) | set(s_):
                    v = merge(l.get(k), s_.get(k), b.get(k), at + 1, out)
                    if v is not None:
                        m[k] = v
                return m
            out.append(at)
            return l

        for dirpath, _, files in os.walk(root):
            for f in sorted(files):
                if not f.endswith('.json'):
                    continue
                path = os.path.relpath(os.path.join(dirpath, f), root)[:-5].replace(os.sep, '/')
                try:
                    seed = json.load(open(os.path.join(dirpath, f), encoding='utf8'))
                except (ValueError, OSError) as e:   # e.g. git conflict markers after a pull: skip it, keep the record here
                    rep['conflicts'].append({'path': path, 'keys': [f'the seed file could not be read ({e.__class__.__name__}: {str(e)[:80]}); look for <<<<<<< in hub/seed/{path}.json']})
                    continue
                cur = self.get(path)
                if cur is None:
                    self.set(path, seed, 'seed', quiet=True)
                    rep['added'].append(path)
                    self._base_set(path, seed)
                    continue
                local = cur['data']
                if same(local, seed):
                    self._base_set(path, seed)
                    continue
                base = self._base_get(path)
                if base is None:
                    cands = ([local] if cur['by'] == 'seed' else []) + self._seed_history(path)
                    if not cands and git_versions:   # a git version of the seed file this record once was
                        hist = [local] + [json.loads(r[0]) for r in self.db.execute('select data from history where path=?', (path,))]
                        cands = [g for g in git_versions(path) if any(same(g, h) for h in hist)]
                    base = cands[0] if cands else None
                if base is None:   # reported once: this seed version becomes the base, so it is listed again only if the seed changes
                    rep['conflicts'].append({'path': path, 'keys': ['no common base: local kept, the seed version saved for review']})
                    self._base_set(path, seed)
                    continue
                if same(local, base):
                    self.set(path, seed, 'seed', quiet=True)
                    rep['updated'].append(path)
                elif same(seed, base):
                    rep['kept'].append(path)
                else:
                    out = []
                    m = {}
                    keys = []
                    for k in set(local) | set(seed) if isinstance(local, dict) and isinstance(seed, dict) else []:
                        o = []
                        v = merge(local.get(k), seed.get(k), (base or {}).get(k), 1, o)
                        if o:
                            keys.append(k)
                        if v is not None:
                            m[k] = v
                    if not isinstance(local, dict):
                        keys, m = ['whole record'], local
                    self.set(path, m, 'seed', quiet=True)
                    rep['merged'].append(path)
                    if keys:
                        rep['conflicts'].append({'path': path, 'keys': keys})
                self._base_set(path, seed)
        return rep

    def export_dir(self, root, skip=NO_HISTORY):
        """write every record (but the derived ones) to root/<path>.json; removes files of deleted records"""
        keep = set()
        for p in self.paths():
            if p.startswith(skip):
                continue
            f = os.path.join(root, *p.split('/')) + '.json'
            os.makedirs(os.path.dirname(f), exist_ok=True)
            data = self.get(p)['data']
            with open(f, 'w', encoding='utf8') as fh:
                json.dump(data, fh, ensure_ascii=False, indent=1)
            self._base_set(p, data)
            keep.add(os.path.abspath(f))
        for dirpath, _, files in os.walk(root):
            for f in files:
                full = os.path.abspath(os.path.join(dirpath, f))
                if f.endswith('.json') and full not in keep:
                    os.remove(full)
        return len(keep)
