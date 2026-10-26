"""Run the Mill Creek Deck page headless on its published files and a saved deck/layout, and read the platform and
track design back out of the page's own functions.

    python3 deck_headless.py PAGE_HTML FILES_DIR LAYOUT_JSON JSTS_JS OUT_JSON

PAGE_HTML   the Deck page as published (Artifact read)
FILES_DIR   its published data files (deck.json, context.json, sheets.json, tiles_n/index.json, relief.json,
            tracks.json, structures.json, hwy.json, norwood.json, airport.json, basin.json)
LAYOUT_JSON the deck/layout document from the page's database (ArtifactData get)
JSTS_JS     jsts 2.12.1 dist/jsts.min.js (npm), since the page loads it from a CDN
OUT_JSON    where to write the extract

The page is served from a fake origin through Playwright routing. A stand-in for window.claude.use('db') hands the
saved layout to the page's own onSnapshot handler, so every Metro, RER and CVG Express platform and track pair comes
from the same code the page draws with. Nothing is written back to the artifact.
"""
import json, os, re, sys
from playwright.sync_api import sync_playwright

PAGE, FILES, LAYOUT, JSTS, OUT = sys.argv[1:6]
ORIGIN = 'http://deck.local/'

html = open(PAGE, encoding='utf-8').read()
html = html.replace('https://cdn.jsdelivr.net/npm/jsts@2.12.1/dist/jsts.min.js', 'jsts.min.js')
html = html.replace('<script src="jsts.min.js" async></script>', '<script src="stub.js"></script><script src="jsts.min.js"></script>', 1)
EXPOSE = ('window.__D = { currentFeatures, transitFeatures, trackPair, stopRings, stopBands, stopType, stopOff, stopLive, '
          'stopFrame, stopEdit, stDeleted, liveLines, baseH, hAt, H0, EDGE, PW, TAPER, H_TUBE, H_BOX, SLIDE_M, geomOf, '
          'frameAt, projectOn, featLabel, utmToLL, CVX, chainOf, resampleLine, lineCoords };')
html, n = re.subn(r'indexLayers\(\); if \(/\[\?&\]debug', 'indexLayers(); ' + EXPOSE + ' if (/[?&]debug', html, count=1)
assert n == 1, 'boot hook not found'

layout = json.load(open(LAYOUT))
layout = layout.get('data', layout)
stub = ('window.__LAYOUT = ' + json.dumps(layout) + ';\n'
        'window.__SNAP = 0;\n'
        'window.claude = { use: async (name) => {\n'
        '  if (name === "db") return { doc: () => ({ onSnapshot: (cb) => { setTimeout(() => { cb({ metadata: { hasPendingWrites: false }, exists: true, data: () => window.__LAYOUT }); window.__SNAP++; }, 0); return () => {}; }, set: async () => {}, update: async () => {} }) };\n'
        '  if (name === "user") return { can: async () => false };\n'
        '  return null; } };\n')

TYPES = {'.json': 'application/json', '.js': 'application/javascript', '.html': 'text/html'}


def handle(route):
    url = route.request.url
    if not url.startswith(ORIGIN):
        return route.abort()
    path = url[len(ORIGIN):].split('?')[0].split('#')[0]
    if path in ('', 'index.html'):
        return route.fulfill(status=200, body=html, headers={'content-type': 'text/html'})
    if path == 'stub.js':
        return route.fulfill(status=200, body=stub, headers={'content-type': 'application/javascript'})
    if path == 'jsts.min.js':
        return route.fulfill(status=200, body=open(JSTS, 'rb').read(), headers={'content-type': 'application/javascript'})
    fp = os.path.join(FILES, path)
    if os.path.isfile(fp):
        return route.fulfill(status=200, body=open(fp, 'rb').read(), headers={'content-type': TYPES.get(os.path.splitext(fp)[1], 'application/octet-stream')})
    return route.fulfill(status=404, body='')


EXTRACT = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'extract.js'), encoding='utf-8').read()

with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_page(viewport={'width': 1200, 'height': 800})
    errs = []
    pg.on('pageerror', lambda e: errs.append(str(e)))
    pg.route('**/*', handle)
    pg.goto(ORIGIN + 'index.html?debug')
    pg.wait_for_function('window.__D && window.__S && window.__SNAP > 0 && window.__S.ver > 0', timeout=120000)
    pg.wait_for_timeout(500)
    res = pg.evaluate(EXTRACT)
    res['page_errors'] = errs
    res['layout_updated'] = layout.get('updated')
    b.close()

json.dump(res, open(OUT, 'w'), indent=1)
print('stations', len(res['stations']), 'lines', len(res['lines']), 'errors', len(errs))
