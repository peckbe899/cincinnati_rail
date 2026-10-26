"""Run the Rail Profiles page headless on its published files and saved alignments, and read every line's rail level
and structure type along its chainage, plus its stations and platforms, from the page's own functions.

    python3 profiles_headless.py PAGE_HTML FILES_DIR ALIGNMENTS_DIR OUT_JSON [STEP_M]

PAGE_HTML       the Profiles page as published (Artifact read)
FILES_DIR       its published files (lines/, rer/lines/, network.json, rer/canon.json, rer/network.json, rer/metro_rails.json)
ALIGNMENTS_DIR  the alignments collection from its database (ArtifactData list with out_dir), one <Line_id>.json each
OUT_JSON        where to write the extract
STEP_M          sampling step along each line (default 5 m)

A stand-in for window.claude.use('db') serves the saved alignments to the page's own onSnapshot handler, so the
rail levels are the ones the page draws (saved profile, else its defaults). Nothing is written back.
"""
import glob, json, os, sys
from playwright.sync_api import sync_playwright

PAGE, FILES, ALIGN, OUT = sys.argv[1:5]
STEP = float(sys.argv[5]) if len(sys.argv) > 5 else 5.0
ORIGIN = 'http://profiles.local/'

docs = []
for fp in sorted(glob.glob(os.path.join(ALIGN, '*.json'))):
    d = json.load(open(fp)); d = d.get('data', d)
    docs.append({'id': os.path.splitext(os.path.basename(fp))[0], 'data': d})
stub = ('window.__DOCS = ' + json.dumps(docs) + ';\n'
        'window.claude = { use: async (name) => {\n'
        '  if (name === "db") return {\n'
        '    collection: () => ({ onSnapshot: (cb) => { setTimeout(() => cb({ docs: window.__DOCS.map((x) => ({ id: x.id, data: () => JSON.parse(JSON.stringify(x.data)) })), metadata: { hasPendingWrites: false } }), 0); return () => {}; } }),\n'
        '    doc: () => ({ onSnapshot: (cb) => { setTimeout(() => cb({ exists: false, data: () => null }), 0); return () => {}; }, set: async () => {}, update: async () => {} }) };\n'
        '  if (name === "user") return { can: async () => false };\n'
        '  return null; } };\n')
html = open(PAGE, encoding='utf-8').read()
i = html.index('<script>')
html = html[:i] + '<script src="stub.js"></script>' + html[i:]


def handle(route):
    url = route.request.url
    if not url.startswith(ORIGIN): return route.abort()
    path = url[len(ORIGIN):].split('?')[0].split('#')[0]
    if path in ('', 'index.html'): return route.fulfill(status=200, body=html, headers={'content-type': 'text/html'})
    if path == 'stub.js': return route.fulfill(status=200, body=stub, headers={'content-type': 'application/javascript'})
    fp = os.path.join(FILES, path)
    if os.path.isfile(fp): return route.fulfill(status=200, body=open(fp, 'rb').read(), headers={'content-type': 'application/json'})
    return route.fulfill(status=404, body='')


ids = [l['id'] for l in json.load(open(os.path.join(FILES, 'lines/index.json')))] + [l['id'] for l in json.load(open(os.path.join(FILES, 'rer/lines/index.json')))]
SAMPLE = '''(step) => { const P = window.railProfile, a = P.align(), out = { id: P.line(), saved: P.saved(), samples: [], platforms: P.platforms(), align_st: a.st || null };
  const L = Number(document.querySelector('#lineSel').selectedOptions[0].textContent.split('·')[1]) * 1000 || 0;
  return out; }'''
res, errs = {}, []
with sync_playwright() as p:
    b = p.chromium.launch(); pg = b.new_page(viewport={'width': 1400, 'height': 900})
    pg.on('pageerror', lambda e: errs.append(str(e)))
    pg.route('**/*', handle)
    pg.goto(ORIGIN + 'index.html#' + ids[0])
    pg.wait_for_function('window.railProfile && window.railProfile.line && window.railProfile.line()', timeout=120000)
    pg.wait_for_timeout(1500)
    for lid in ids:
        pg.evaluate('(id) => { const s = document.querySelector("#lineSel"); s.value = id; s.dispatchEvent(new Event("change")); }', lid)
        pg.wait_for_function('(id) => window.railProfile.line() === id', arg=lid, timeout=60000)
        pg.wait_for_timeout(300)
        L = json.load(open(os.path.join(FILES, ('rer/lines/' if lid.startswith('RER_') else 'lines/') + lid + '.json')))['length_m']
        r = pg.evaluate('''([L, step]) => { const P = window.railProfile, out = [];
            for (let c = 0; c <= L + 1e-6; c += step) { const z = P.railAt(c); out.push([Math.round(c * 10) / 10, Math.round(z * 100) / 100, P.typeAt(c)]); }
            const a = P.align();
            return { saved: P.saved(), samples: out, platforms: P.platforms(), st: a.st || null, so: a.so || null }; }''', [L, STEP])
        r['length_m'] = L; res[lid] = r
        print(lid, 'saved' if r['saved'] else 'defaults', len(r['samples']), 'samples')
    b.close()
json.dump({'lines': res, 'page_errors': errs, 'step_m': STEP}, open(OUT, 'w'))
print('errors', len(errs), errs[:3])
