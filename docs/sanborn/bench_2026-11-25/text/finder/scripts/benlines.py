"""Ben's street lines for plates 44, 1A and 5, as a raster (read-only use of the repo's tools; 25 Nov 2026).

44: streetmap/22-44.json (his finished street map). 1A, 5: street_map.editor_lines(N, W, H, unet_data/N_edges.json,
picks22_guided/22-N/edges_ben.json), i.e. what the line editor shows with his edits applied. Kinds kept: printed, drawn,
sheet_edge (no_printed_line has no ink under it and is left out). Also reports how many of his edits found their line."""
import json, os, sys
sys.dont_write_bytecode = True
import numpy as np, cv2
HERE = os.path.dirname(os.path.abspath(__file__))
TOOLS = os.path.normpath(os.path.join(HERE, '..', '..', '..', '..', '..', '..', 'tools', 'sanborn', 'unet'))
KINDS = ('printed', 'drawn', 'sheet_edge')


def lines(N, W, H):
    if N == '44':
        SM = json.load(open('streetmap/22-44.json', encoding='utf8'))
        return [l for l in SM['lines']], dict(source='streetmap/22-44.json')
    sys.path.append(TOOLS); import street_map, edit_server as es
    E = json.load(open(f'unet_data/{N}_edges.json', encoding='utf8')); B = json.load(open(f'picks22_guided/22-{N}/edges_ben.json', encoding='utf8'))
    L, SH = street_map.editor_lines(N, W, H, E, B)
    key = lambda a, b: tuple(round(v) for v in a + b); keys = {key(e['a'], e['b']) for e in es.clean(E) + es.sheet(N, W, H)}
    edits = [l for l in B['lines'] if not l.get('added')]; found = sum(key(l['a0'], l['b0']) in keys for l in edits)
    return L, dict(source=f'editor_lines(unet_data/{N}_edges.json + picks22_guided/22-{N}/edges_ben.json)', edits=len(edits), edits_found=found,
                   added=sum(1 for l in B['lines'] if l.get('added')))


def raster(N, W, H, kinds=KINDS, thick=1):
    L, info = lines(N, W, H); m = np.zeros((H, W), np.uint8); from collections import Counter
    info['kinds'] = dict(Counter(l['kind'] for l in L))
    for l in L:
        if l['kind'] in kinds: cv2.line(m, tuple(np.round(l['a']).astype(int).tolist()), tuple(np.round(l['b']).astype(int).tolist()), 1, thick)
    return m, info


if __name__ == '__main__':
    for N in sys.argv[1:]:
        im = cv2.imread(f'cufp/22-{N}.jpg'); H, W = im.shape[:2]; m, info = raster(N, W, H); print(N, info, int(m.sum()))
