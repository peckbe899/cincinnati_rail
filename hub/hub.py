"""The Cincinnati Rail hub: the Mill Creek Deck, the Rail Profiles and Station 3D as three views of one local database,
kept in step by a pipeline. Standard library only (plus what the repo's tools already need).

    python hub/hub.py                 # http://localhost:8765
    python hub/hub.py --port 9000 --no-auto
    python hub/hub.py export          # write every record to hub/seed (the git-tracked copy), then commit it

See hub/README.md.
"""
import argparse
import json
import mimetypes
import os
import queue
import shutil
import subprocess
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

HUB = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HUB)
sys.path.insert(0, HUB)
from store import Store          # noqa: E402
from pipeline import Pipeline, trigger_for    # noqa: E402

SITES = {   # url prefix -> (folder, its page)
    'deck': (os.path.join(HUB, 'sites', 'deck'), 'index.html'),
    'profiles': (os.path.join(ROOT, 'data', 'profile'), 'profiles.html'),
    '3d': (os.path.join(ROOT, 'tools', 'station3d', 'page'), 'index.html'),
    'chronology': (os.path.join(HUB, 'sites', 'chronology'), 'index.html'),
}
SHIM = '<script src="/hub/shim.js"></script>'
VENDOR = {   # the pages' CDN libraries served from hub/static/vendor (the hub works offline)
    'https://cdn.jsdelivr.net/npm/three@0.147.0/build/three.min.js': '/hub/vendor/three.min.js',
    'https://cdn.jsdelivr.net/npm/three@0.147.0/examples/js/controls/OrbitControls.js': '/hub/vendor/OrbitControls.js',
    'https://cdn.jsdelivr.net/npm/three@0.147.0/examples/js/exporters/GLTFExporter.js': '/hub/vendor/GLTFExporter.js',
    'https://cdn.jsdelivr.net/npm/jsts@2.12.1/dist/jsts.min.js': '/hub/vendor/jsts.min.js',
}
mimetypes.add_type('image/webp', '.webp')
mimetypes.add_type('application/json', '.json')


def fill_missing(cur, dflt):
    """add keys the default has and the record lacks, recursively; True if any were added"""
    added = False
    for k, v in dflt.items():
        if k not in cur:
            cur[k] = v
            added = True
        elif isinstance(v, dict) and isinstance(cur[k], dict):
            added = fill_missing(cur[k], v) or added
    return added


def git_seed_versions(path, n=40):
    """the seed file's earlier committed versions, newest first (bases for merging a pulled seed)"""
    rel = 'hub/seed/' + path + '.json'
    try:
        revs = subprocess.check_output(['git', 'log', '--format=%H', '-n', str(n), '--', rel], cwd=ROOT, text=True).split()
        out = []
        for r in revs:
            try:
                out.append(json.loads(subprocess.check_output(['git', 'show', f'{r}:{rel}'], cwd=ROOT, stderr=subprocess.DEVNULL)))
            except Exception:
                pass
        return out
    except Exception:
        return []


def write_timeline():
    """the Chronology timeline (data/profile/chronology_timeline.md) from the exported record"""
    try:
        r = subprocess.run(['node', os.path.join(ROOT, 'tools', 'chronology_timeline.js')], cwd=ROOT, capture_output=True, text=True, timeout=60)
        print((r.stdout or r.stderr).strip())
    except Exception as e:
        print('timeline not written:', e)


def seed_report(store, rep):
    """print what a pulled seed changed here; save the seed versions of conflicting records for review"""
    lines = []
    for k, lab in (('added', 'added'), ('updated', 'updated from the seed'), ('merged', 'merged with your edits'), ('kept', 'kept (your edits, seed unchanged)')):
        if rep[k]:
            lines.append(f"{lab}: {', '.join(rep[k])}")
    cdir = os.path.join(HUB, 'work', 'seed_conflicts')
    for c in rep['conflicts']:
        lines.append(f"CONFLICT {c['path']}: {', '.join(c['keys'])} (your value kept; the seed's is in hub/work/seed_conflicts)")
        f = os.path.join(cdir, *c['path'].split('/')) + '.json'
        os.makedirs(os.path.dirname(f), exist_ok=True)
        try:
            shutil.copyfile(os.path.join(HUB, 'seed', *c['path'].split('/')) + '.json', f)
        except OSError:
            pass
    text = 'hub/seed taken in:\n' + '\n'.join(lines) + '\n'
    print(text)
    rid = store.run_start('seed', 'records from hub/seed (git pull)')
    store.run_log(rid, text)
    store.run_end(rid, 'failed' if rep['conflicts'] else 'ok')


class Hub:
    def __init__(self, db_path, auto=True):
        self.store = Store(db_path)
        rep = self.store.merge_dir(os.path.join(HUB, 'seed'), git_versions=git_seed_versions)
        changed = rep['added'] + rep['updated'] + rep['merged']
        self.subs = set()
        self.store.listeners.append(self.broadcast)
        self.pipeline = Pipeline(self.store, auto=auto)
        ms_def = json.load(open(os.path.join(ROOT, 'data', 'profile', 'metro_structure.json'), encoding='utf8'))
        cur = self.store.get('params/metro_structure')
        if cur is None:   # the shared Metro structure record, from its default file
            self.store.set('params/metro_structure', ms_def, 'seed', quiet=True)
        elif fill_missing(cur['data'], ms_def):   # fields added to the default since (Ben's values kept)
            self.store.set('params/metro_structure', cur['data'], 'seed', quiet=True)
        ch_f = os.path.join(ROOT, 'data', 'profile', 'chronology.json')
        if self.store.get('chronology/segments') is None and os.path.exists(ch_f):   # opening years and phases (the Chronology view)
            self.store.set('chronology/segments', json.load(open(ch_f, encoding='utf8')), 'seed', quiet=True)
        st_f = os.path.join(ROOT, 'data', 'profile', 'station_types.json')
        if self.store.get('params/station_types') is None and os.path.exists(st_f):   # the Profiles type at each Metro station
            self.store.set('params/station_types', json.load(open(st_f, encoding='utf8')), 'seed', quiet=True)
        if changed or rep['conflicts']:
            seed_report(self.store, rep)
            if any(p == 'deck/layout' for p in changed):
                self.pipeline.schedule('deck_tie', 'records taken in from hub/seed (git pull)', delay=2)
            elif any(trigger_for(p) for p in changed):
                self.pipeline.schedule('3d', 'records taken in from hub/seed (git pull)', delay=2)
        if self.store.get('snapshots/region') is None:   # first start: build the 3D snapshot
            self.pipeline.schedule('3d', 'first start: no 3D snapshot yet', delay=1)

    def broadcast(self, ev):
        msg = json.dumps(ev)
        for q in list(self.subs):
            q.put(msg)


def make_handler(hub):
    class H(BaseHTTPRequestHandler):
        protocol_version = 'HTTP/1.1'

        def log_message(self, fmt, *a):
            pass

        def send(self, code, body=b'', ctype='application/json', extra=None):
            if isinstance(body, (dict, list)) or body is None:
                body = json.dumps(body).encode()
            elif isinstance(body, str):
                body = body.encode()
            self.send_response(code)
            self.send_header('Content-Type', ctype)
            self.send_header('Content-Length', str(len(body)))
            self.send_header('Cache-Control', 'no-store')
            for k, v in (extra or {}).items():
                self.send_header(k, v)
            self.end_headers()
            if self.command != 'HEAD':
                self.wfile.write(body)

        def body(self):
            n = int(self.headers.get('Content-Length') or 0)
            return json.loads(self.rfile.read(n) or b'null')

        def q(self):
            return {k: v[0] for k, v in parse_qs(urlparse(self.path).query).items()}

        # ---- reads ----
        def do_GET(self):
            u = urlparse(self.path).path
            s = hub.store
            if u == '/api/doc':
                r = s.get(self.q()['p'])
                return self.send(200, r)
            if u == '/api/coll':
                return self.send(200, s.list(self.q()['c']))
            if u == '/api/history':
                return self.send(200, s.history(self.q()['p']))
            if u == '/api/runs':
                return self.send(200, {'runs': s.runs(), 'current': hub.pipeline.current, 'pending': sorted(hub.pipeline.pending)})
            if u == '/api/events':
                return self.events()
            if u in ('/', '/index.html'):
                return self.file(os.path.join(HUB, 'static', 'home.html'))
            if u.startswith('/hub/'):
                return self.file(os.path.join(HUB, 'static', u[5:]))
            parts = u.strip('/').split('/', 1)
            if parts[0] in SITES:
                if u == '/' + parts[0]:
                    return self.send(301, b'', extra={'Location': u + '/'})
                folder, page = SITES[parts[0]]
                rel = parts[1] if len(parts) > 1 and parts[1] else page
                if rel == 'index.html':
                    rel = page
                return self.file(os.path.join(folder, rel), inject=rel == page)
            return self.send(404, b'not found', 'text/plain')

        do_HEAD = do_GET

        def file(self, f, inject=False):
            f = os.path.abspath(f)
            if not os.path.isfile(f) or not (f.startswith(ROOT) or f.startswith(os.path.realpath(ROOT))):
                return self.send(404, b'not found', 'text/plain')
            data = open(f, 'rb').read()
            if inject:
                html = data.decode('utf8')
                for cdn, local in VENDOR.items():
                    html = html.replace(cdn, local)
                i = html.find('<head>')
                data = (html[:i + 6] + SHIM + html[i + 6:] if i >= 0 else SHIM + html).encode('utf8')
            ctype = mimetypes.guess_type(f)[0] or 'application/octet-stream'
            if ctype.startswith('text/') or ctype in ('application/json', 'application/javascript'):
                ctype += '; charset=utf-8'
            return self.send(200, data, ctype)

        def events(self):
            q = queue.Queue()
            hub.subs.add(q)
            self.send_response(200)
            self.send_header('Content-Type', 'text/event-stream')
            self.send_header('Cache-Control', 'no-store')
            self.send_header('Connection', 'keep-alive')
            self.end_headers()
            try:
                self.wfile.write(b': hello\n\n')
                self.wfile.flush()
                while True:
                    try:
                        msg = q.get(timeout=20)
                        self.wfile.write(f'data: {msg}\n\n'.encode())
                    except queue.Empty:
                        self.wfile.write(b': ping\n\n')
                    self.wfile.flush()
            except (BrokenPipeError, ConnectionResetError, OSError):
                pass
            finally:
                hub.subs.discard(q)
                self.close_connection = True

        # ---- writes ----
        def do_PUT(self):
            u = urlparse(self.path).path
            if u == '/api/doc':
                v = hub.store.set(self.q()['p'], self.body(), by=self.headers.get('X-By', 'page'))
                return self.send(200, {'version': v})
            return self.send(404, None)

        def do_PATCH(self):
            if urlparse(self.path).path == '/api/doc':
                v = hub.store.update(self.q()['p'], self.body(), by=self.headers.get('X-By', 'page'))
                return self.send(200, {'version': v})
            return self.send(404, None)

        def do_DELETE(self):
            if urlparse(self.path).path == '/api/doc':
                hub.store.delete(self.q()['p'], by=self.headers.get('X-By', 'page'))
                return self.send(204, b'')
            return self.send(404, None)

        def do_POST(self):
            u = urlparse(self.path).path
            if u == '/api/run':
                job = self.q()['job']
                if job not in ('deck_tie', '3d'):
                    return self.send(400, {'error': 'unknown job'})
                hub.pipeline.schedule(job, 'run from the hub page', delay=0)
                return self.send(200, {'scheduled': job})
            if u == '/api/restore':
                q = self.q()
                return self.send(200, {'version': hub.store.restore(q['p'], int(q['v']))})
            if u == '/api/export':
                n = hub.store.export_dir(os.path.join(HUB, 'seed'))
                write_timeline()
                return self.send(200, {'records': n})
            return self.send(404, None)
    return H


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('command', nargs='?', default='serve', choices=('serve', 'export'))
    ap.add_argument('--port', type=int, default=8765)
    ap.add_argument('--db', default=os.path.join(HUB, 'hub.db'))
    ap.add_argument('--no-auto', action='store_true', help='do not run the pipeline on changes (run it from the hub page)')
    ap.add_argument('--no-browser', action='store_true', help='do not open the hub page in the browser')
    a = ap.parse_args()
    if a.command == 'export':
        n = Store(a.db).export_dir(os.path.join(HUB, 'seed'))
        print(f'{n} records written to hub/seed')
        write_timeline()
        return
    hub = Hub(a.db, auto=not a.no_auto)
    srv = ThreadingHTTPServer(('127.0.0.1', a.port), make_handler(hub))
    srv.daemon_threads = True
    print(f'Cincinnati Rail hub on http://localhost:{a.port}  (Deck /deck/, Profiles /profiles/, 3D /3d/)')
    if not a.no_browser:
        import webbrowser
        threading.Timer(0.5, lambda: webbrowser.open(f'http://localhost:{a.port}/')).start()
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == '__main__':
    main()
