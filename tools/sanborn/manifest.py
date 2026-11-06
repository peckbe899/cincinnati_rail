"""data/sanborn/manifest.json: every file of the Sanborn pipeline by path, size and sha256.

    python tools/sanborn/manifest.py build     write the manifest (repo files and Ben's input scans)
    python tools/sanborn/manifest.py check     compare Ben's input scans (and with --all the repo files) to it;
                                               exit 1 on any changed or missing file, so a changed scan stops a build

Two lists:
- "files": every file brought in from the Topography export (Maps/Topography_Export, 31 October 2026) under
  tools/sanborn, data/sanborn and docs/sanborn, with its workspace path, export group and zip, and the export's
  sha256 where the repo copy differs (the scripts, repointed; the notes' workspace paths). "category" is a filename
  rule (CATEGORY below), "in_git" false for the inverse grids (rebuilt by the fit, kept on disk only).
- "inputs": the files the scripts read on Ben's machine (scans, GeoTIFFs, OSM and topo sources), found from the
  scripts' /mnt/user-data paths (configs/sanborn_paths.json maps them), the 1904 sheets of every frame in the
  transform files, the 1922 plates and halves; folders the scripts read whole are listed with their file count.
"""
import csv, glob, hashlib, json, os, re, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _ws  # noqa: E402

REPO = _ws.REPO.replace('\\', '/')
D, T = _ws.DATA.rstrip('/'), _ws.CODE.rstrip('/')
DOCS = REPO + '/docs/sanborn'
OUT = D + '/manifest.json'
EXPORT_CSV = DOCS + '/export/MANIFEST.csv'

CATEGORY = [   # first match wins; path is the workspace path
    ('inverse_grid', r'\.npz$'),
    ('judged', r'^sbg/picks(12|22)?/|(^|/)config\.json$|^cufp/strips\.json$|removed|rejected|^sbg/osmchk/(corrections|pick_fix|cuts|additions)\.json$'
               r'|^cuf/ben_georef\.json$|(^|/)area(_\w+)?\.json$|^basin/aoi\.json$|^lph/sheets_\w+\.json$|frames_(all|under)'
               r'|^lph/wb_picks\.json$|/png2tif\.json$'),
    ('model', r'(^|/)fwd\w*\.pkl$|(^|/)matches\w*\.json$|(^|/)tf(_|22|\.)[\w.]*json$|(^|/)tps\w*\.pkl$|(^|/)corr\.pkl$|(^|/)x1904\.json$'),
    ('report', r'report|\.log$|\.out$|(^|/)review_\d+\.txt$|(^|/)diag'),
    ('page_snapshot', r'^dbread\d*/|^deckpage/|^plots/db_\w+\.json$'),
    ('input', r'\.(geojson|kml|kmz|xlsx|tsv)$|^(kmz\w*|cskmz|cvgkmz|spankmz)/|(^|/)osm\w*\.(pkl|json)$'),
    ('script', r'\.(py|sh|js)$'),
    ('note', r'\.(md|txt)$'),
]


def sha(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()


def category(ws):
    for c, rx in CATEGORY:
        if re.search(rx, ws):
            return c
    return 'other'


def export_rows():
    return {r['path']: r for r in csv.DictReader(open(EXPORT_CSV, newline='', encoding='utf8'))}


RENAMED = {   # paths that cannot sit side by side on Windows (names differing only in case)
    'cvg/_gp_C.json': 'data/sanborn/cvg/_gp_C_upper.json',   # beside cvg/_gp_c.json; no script names either
}


def repo_path(ws):
    if ws in RENAMED:
        return RENAMED[ws]
    if ws.endswith(('.py', '.sh', '.js')):
        return 'tools/sanborn/' + ws
    if ws.endswith('.md'):
        if ws == 'Relief_Maps_Log.md':
            return 'docs/sanborn/Relief_Maps_Log.md'
        return 'docs/sanborn/' + ('PROCESS_1922.md' if ws == 'cufp/PROCESS_1922.md' else 'workspace_notes/' + ws)
    return 'data/sanborn/' + ws


def files():
    out = []
    for ws, r in sorted(export_rows().items()):
        rp = repo_path(ws)
        p = REPO + '/' + rp
        e = dict(path=rp, workspace=ws, group=r['group'], zip=r['zip'], category=category(ws),
                 in_git=not ws.endswith('.npz'))
        if os.path.exists(p):
            e.update(size=os.path.getsize(p), sha256=sha(p))
            if e['sha256'] != r['sha256']:
                e['export_sha256'] = r['sha256']
        else:
            e['missing'] = True
        out.append(e)
    for ws, src in sorted(NOT_EXPORTED.items()):
        rp = repo_path(ws)
        p = REPO + '/' + rp
        e = dict(path=rp, workspace=ws, group='not exported', zip=None, category=category(ws), in_git=True, source=src)
        if os.path.exists(p):
            e.update(size=os.path.getsize(p), sha256=sha(p))
        else:
            e['missing'] = True
        out.append(e)
    for ws, (rp, z, size, sha_) in sorted(LATER_ZIPS.items()):
        p = REPO + '/' + rp
        e = dict(path=rp, workspace=ws, group=z.split('.')[0], zip=z, category=category(ws), in_git=True)
        if os.path.exists(p):
            e.update(size=os.path.getsize(p), sha256=sha(p))
            if e['sha256'] != sha_:
                e['export_sha256'] = sha_
        else:
            e['missing'] = True
        out.append(e)
    return out


# Workspace files the scripts import that the export left out (found 6 November by the scripts' imports against
# export/TREE.txt). A source starting "LOST" has no copy anywhere (the Topography workspace was reset; extras_03).
NOT_EXPORTED = {
    'sbg/names.py': 'Maps/Basin_Street_Map/sanborn1904_scripts.zip (names.py, 1743 bytes, 11 Oct 21:42: the size and time '
                    'export/TREE.txt lists for the workspace copy); imported by 33 scripts (key, base, key2)',
    'arcs/fitarcs.py': 'LOST: 14820 bytes, 15 Oct 06:00 in export/TREE.txt; imported by rer1023/apply.py and transit/build_transit.py. '
                       'The surviving fitter is the Deck page\'s FA.fit (tools/sanborn/arcs/fitarcs_deck_port.js, from extras_03)',
    'arcs/fitarcs.js': 'LOST: 14407 bytes (docs/sanborn/EXTRAS_03_README.md); the workspace\'s JS copy of fitarcs.py',
    'deck/xs.py': 'LOST: 749 bytes, 10 Oct 18:09 in export/TREE.txt; imported by lph/solve_all.py',
    'deck/xs_v1.json': 'LOST: the output of deck/xs.py (docs/sanborn/EXTRAS_03_README.md)',
}

# Files from zips added to Maps/Topography_Export after its MANIFEST.csv (31 October): workspace path ->
# (repo path, zip, size and sha256 in the zip)
LATER_ZIPS = {
    'arcs/fitarcs_deck_port.js': ('tools/sanborn/arcs/fitarcs_deck_port.js', 'extras_03.zip', 15507,
                                  'eb1e70d9f536bae44688e7f67b5223b957b6f0d3729e79b6787537cfce9f3f41'),
    'EXTRAS_03_README.md': ('docs/sanborn/EXTRAS_03_README.md', 'extras_03.zip', 1359,
                            'a1cb289100b462f29d7780dbf792a64f9aeb05f50e1841a88b1880d102433727'),
}


def _sheet_file(root, s):
    """the 1904 / 1922 scan of a frame id, as sbg/sb.py find() looks it up"""
    s = str(s)
    if s.startswith('22-'):
        n, h = re.match(r'22-(\d+)([A-Z]?)', s.upper()).groups()
        return glob.glob(root + f'cincinnati_1922_v1/06645_01_1922-{int(n):04d}{h}.jpg')[:1]
    m = re.match(r'(\d+)', s)
    if not m:
        return []
    n = int(m.group(1))
    for p in (f'cincinnati_1904_v1/*_sheet_{n:04d}.jpg', f'cincinnati_1904_v2/*_sheet_{n:04d}.jpg', f'cincinnati_1904_v*/*-{n:04d}.jpg'):
        g = glob.glob(root + p)
        if g:
            return g[:1]
    return []


def inputs():
    refs = {}   # local path -> set of reasons
    add = lambda p, why: refs.setdefault(p.replace('\\', '/').rstrip('/'), set()).add(why)
    # 1. /mnt/user-data paths written in the scripts (plain literals) and in the data files
    lit = re.compile(r'_ws\.ext\(\s*[\'"](/mnt/user-data/[^\'"{}*]+)[\'"]\s*\)')
    for p in glob.glob(T + '/**/*.py', recursive=True):
        for m in lit.findall(open(p, encoding='utf8').read()):
            add(_ws.ext(m), 'named in ' + os.path.relpath(p, T).replace('\\', '/'))
    for f in ('sbg/fit/sizes.json',):
        for k, v in json.load(open(D + '/' + f)).items():
            add(_ws.ext(v[1]), f)
    cfg = json.load(open(D + '/cufp/config.json'))
    # 2. the 1922 plates fitted from Ben's PNGs (cufp/<N>/png2tif.json, or a png in cufp/config.json)
    plates = sorted({os.path.basename(os.path.dirname(p)) for p in glob.glob(D + '/cufp/*/report.json')})
    for n in plates:
        png = cfg.get(n, {}).get('png') or f'/mnt/user-data/uploads/PNG/{n}.png'
        add(_ws.ext(png), f'1922 plate {n} (cufp)')
    # 3. the 1904 sheets of every frame the transforms place, and the vol. 1 1922 halves
    root = _ws.ext('/mnt/user-data/uploads/Documents--_Personal--_Cincinnati Rail/Maps/Sanborn/')
    frames = set()
    for f in ('sbg/fit/tf.json', 'lph/tf_all.json', 'lph/tf_all_te.json', 'lph/tf_all_ma.json', 'lph/tf_all_v3.json'):
        if os.path.exists(D + '/' + f):
            frames |= {str(k) for k in json.load(open(D + '/' + f))}
    for s in sorted(frames):
        for p in _sheet_file(root, s):
            add(p, '1904 frame ' + s)
    for h in sorted(os.path.basename(p) for p in glob.glob(D + '/cuf_cw/*') if re.fullmatch(r'\d+[LR]', os.path.basename(p))):
        for p in _sheet_file(root, '22-' + h[:-1] + h[-1]):
            add(p, '1922 vol. 1 half ' + h)
    out = []
    for p, why in sorted(refs.items()):
        e = dict(path=p, why=sorted(why)[:5] + ([f'... {len(why) - 5} more'] if len(why) > 5 else []))
        if os.path.isfile(p):
            e.update(size=os.path.getsize(p), sha256=sha(p))
        elif os.path.isdir(p):
            fs = [q for q in glob.glob(p.rstrip('/') + '/*') if os.path.isfile(q)]
            e.update(folder=True, files=len(fs), size=sum(os.path.getsize(q) for q in fs))
        else:
            e['missing'] = True
        out.append(e)
    return out


def build():
    m = dict(about=__doc__.strip().split('\n')[0], made_by='tools/sanborn/manifest.py build', config='configs/sanborn_paths.json',
             category_rules=CATEGORY, files=files(), inputs=inputs())
    json.dump(m, open(OUT, 'w', encoding='utf8'), indent=1)
    return m


def check(all_files=False):
    m = json.load(open(OUT, encoding='utf8'))
    bad = []
    for e in m['inputs']:
        p = e['path']
        if e.get('missing') or e.get('folder'):
            if not e.get('missing') and not os.path.isdir(p):
                bad.append(('folder gone', p))
            continue
        if not os.path.isfile(p):
            bad.append(('missing', p))
        elif os.path.getsize(p) != e['size'] or sha(p) != e['sha256']:
            bad.append(('changed', p))
    if all_files:
        for e in m['files']:
            p = REPO + '/' + e['path']
            if e.get('missing'):
                continue
            if not os.path.isfile(p):
                bad.append(('missing', e['path']))
            elif os.path.getsize(p) != e['size'] or sha(p) != e['sha256']:
                bad.append(('changed', e['path']))
    for b in bad:
        print(*b)
    print(f"{len(m['inputs'])} inputs" + (f", {len(m['files'])} repo files" if all_files else '') + f': {len(bad)} changed or missing')
    return not bad


if __name__ == '__main__':
    cmd = sys.argv[1] if len(sys.argv) > 1 else 'check'
    if cmd == 'build':
        m = build()
        miss = [e['path'] for e in m['inputs'] if e.get('missing')]
        print(len(m['files']), 'repo files;', len(m['inputs']), 'inputs,', len(miss), 'not on this machine')
        for p in miss:
            print('  not found:', p)
    else:
        sys.exit(0 if check('--all' in sys.argv) else 1)
