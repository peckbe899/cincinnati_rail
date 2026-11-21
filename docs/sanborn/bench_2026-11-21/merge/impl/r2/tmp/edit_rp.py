import sys
p = sys.argv[1]; s = open(p, encoding='utf8', newline='').read()
R = [
("""    python tools\\\\sanborn\\\\unet\\\\run_plates.py --redo          run every step again on the plates asked for
""",
 """    python tools\\\\sanborn\\\\unet\\\\run_plates.py --redo          run every step again on the plates asked for
    (also --pdf DIR: where the uncut plates' PDFs are; any other option stops it, so a slip never starts a run)
"""),
("""  - the outline step alone (blocks_noguide.py N --outlines-only, on the saved maps) where its version changed
    (outline: blocks_noguide.outline_version(), a short hash of outlines.py, blocks_noguide.py and map_area.py);
  - the ink sorting and the tracks where the rules changed (rules: a short hash of ink_bins.py, street_map.py and
    rail_tracks.py) or where what the bins are made from changed (bins_from: the start of the sha256 of the street map,
    N_edges.json, edges_ben.json, outlines.json, N_mapground.png, the old label and rail_ben.json, each or none).
  On a plate where Ben has edited the lines (edges_ben.json), the block step leaves N_edges.json as it is: his edits
  are keyed to its lines (blocks_noguide.py writes N_edges.new.json instead).""",
 """  - the outline step alone (blocks_noguide.py N --outlines-only, on the saved maps) where its version changed
    (outline: blocks_noguide.outline_version(), a short hash of outlines.py, blocks_noguide.py, map_area.py with its
    templates and ink_bins.py);
  - the ink sorting and the tracks where the rules changed (rules: a short hash of ink_bins.py, street_map.py,
    rail_tracks.py and edit_server.py's clean() and sheet(), which make the editor's lines) or where what the bins are
    made from changed (bins_from: the start of the sha256 of the street map, N_edges.json, edges_ben.json,
    outlines.json, N_outlines.json, N_mapground.png, the old label and rail_ben.json, each or none).
  On a plate where Ben has edited the lines (edges_ben.json), the block step leaves the plate's outlines and lines as
  they are: his edits are keyed to its lines (blocks_noguide.py writes the new ones into unet_data/N_new/), so its bins
  stay as they are too.
  A placed plate (43, 44, 45, 80, 82A) sorted by the rules of before 21 Nov 2026 (LEGACY_RULES) is not sorted again
  for the new rules alone: they changed only how a plate never placed is sorted, and on the five placed plates the new
  rules give the same bins pixel for pixel and the same tracks (merge/v-batch sandbox; merge/impl/r2 placed5.py). It is
  sorted again when one of its inputs (street map, label, rail_ben.json, edges_ben.json) is newer than its N_bins.png."""),
("""DATA = os.path.join(REPO, 'data', 'sanborn'); INK = os.path.join(HERE, 'ink_bins.py'); RULES = ('ink_bins.py', 'street_map.py', 'rail_tracks.py')   # the ink sorting's rules (street_map.editor_lines: its block lines)""",
 """DATA = os.path.join(REPO, 'data', 'sanborn'); INK = os.path.join(HERE, 'ink_bins.py'); RULES = ('ink_bins.py', 'street_map.py', 'rail_tracks.py')   # the ink sorting's rules (street_map.editor_lines: its block lines)
RULES_FN = {'edit_server.py': ('sheet', 'clean')}   # and the editor's own functions that make those lines (not the rest of the editor's server)
LEGACY_RULES = {'de9b79144123'}   # ink_bins.py alone, before 21 Nov 2026: a placed plate sorted by these is up to date (see the docstring)
OPTS = {'--list': 0, '--redo': 0, '--pdf': 1}"""),
("""def bins_from(n):
    \"\"\"what the ink sorting of plate n reads for its block lines, ground and rail (the start of each file's sha256, or None)\"\"\"
    U, G = os.path.join(DATA, 'unet_data'), os.path.join(DATA, 'picks22_guided', f'22-{n}')
    fs = dict(streetmap=os.path.join(DATA, 'streetmap', f'22-{n}.json'), edges=os.path.join(U, f'{n}_edges.json'), edges_ben=os.path.join(G, 'edges_ben.json'),
              outlines=os.path.join(G, 'outlines.json'), mapground=os.path.join(U, f'{n}_mapground.png'), label=os.path.join(U, f'{n}_label.png'), rail_ben=os.path.join(G, 'rail_ben.json'))
    return {k: sha16(f) for k, f in fs.items()}


def plan(n, s, rules, outver, nets, netid, redo):""",
 """def rules_hash():
    \"\"\"the ink sorting's rules: the files in RULES, and the functions in RULES_FN read as source (ast), not imported\"\"\"
    import ast
    h = hashlib.sha256(b''.join(open(os.path.join(HERE, f), 'rb').read() for f in RULES))
    for f, names in RULES_FN.items():
        src = open(os.path.join(HERE, f), encoding='utf8').read(); tree = ast.parse(src); got = {}
        for node in tree.body:
            if isinstance(node, ast.FunctionDef) and node.name in names: got[node.name] = ast.get_source_segment(src, node)
        for k in names: h.update(f'{f}:{k}\\0'.encode() + (got.get(k) or 'missing').encode('utf8') + b'\\0')
    return h.hexdigest()[:12]


def bins_inputs(n):
    U, G = os.path.join(DATA, 'unet_data'), os.path.join(DATA, 'picks22_guided', f'22-{n}')
    return dict(streetmap=os.path.join(DATA, 'streetmap', f'22-{n}.json'), edges=os.path.join(U, f'{n}_edges.json'), edges_ben=os.path.join(G, 'edges_ben.json'),
                outlines=os.path.join(G, 'outlines.json'), outline_step=os.path.join(U, f'{n}_outlines.json'), mapground=os.path.join(U, f'{n}_mapground.png'),
                label=os.path.join(U, f'{n}_label.png'), rail_ben=os.path.join(G, 'rail_ben.json'))


def bins_from(n):
    \"\"\"what the ink sorting of plate n reads for its block lines, ground and rail (the start of each file's sha256, or None)\"\"\"
    return {k: sha16(f) for k, f in bins_inputs(n).items()}


def legacy_ok(n, s):
    \"\"\"a placed plate sorted by LEGACY_RULES, none of whose inputs (street map, label, Ben's rail and lines) is newer than its bins\"\"\"
    U = os.path.join(DATA, 'unet_data'); b = os.path.join(U, f'{n}_bins.png')
    if s.get('rules') not in LEGACY_RULES or s.get('bins_from') or not os.path.exists(os.path.join(U, f'{n}_guide.png')) or not os.path.exists(b): return False
    f = bins_inputs(n); return all(os.path.getmtime(f[k]) <= os.path.getmtime(b) for k in ('streetmap', 'label', 'rail_ben', 'edges_ben') if os.path.exists(f[k]))


def plan(n, s, rules, outver, nets, netid, redo):"""),
("""    elif s.get('rules') != rules: why = f"rules {s.get('rules')} -> {rules}"
    elif blocks: why = 'after the block step, if its lines change'""",
 """    elif legacy_ok(n, s): why = None
    elif s.get('rules') != rules: why = f"rules {s.get('rules')} -> {rules}"
    elif blocks: why = 'after the block step, if its lines change'"""),
("""    argv = sys.argv[1:]; args = [a for i, a in enumerate(argv) if not a.startswith('--') and (i == 0 or argv[i - 1] != '--pdf')]; redo = '--redo' in argv; only_list = '--list' in argv""",
 """    argv = sys.argv[1:]; args = [a for i, a in enumerate(argv) if not a.startswith('--') and (i == 0 or argv[i - 1] != '--pdf')]; redo = '--redo' in argv; only_list = '--list' in argv
    bad_opt = [a for i, a in enumerate(argv) if a.startswith('--') and a not in OPTS]
    if bad_opt or ('--pdf' in argv and argv.index('--pdf') + 1 >= len(argv)): sys.exit(f'run_plates.py: unknown option {" ".join(bad_opt) or "--pdf without a folder"} (options: {", ".join(OPTS)}); nothing was run')"""),
("""    rules = hashlib.sha256(b''.join(open(os.path.join(HERE, f), 'rb').read() for f in RULES)).hexdigest()[:12]; outver = outline_version()""",
 """    rules = rules_hash(); outver = outline_version()"""),
]
for a, b in R:
    assert s.count(a) == 1, a[:120]
    s = s.replace(a, b)
open(p, 'w', encoding='utf8', newline='').write(s)
print('ok')
