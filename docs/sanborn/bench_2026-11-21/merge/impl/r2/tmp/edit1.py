import sys
p = sys.argv[1]; s = open(p, encoding='utf8', newline='').read()
R = [
("""_thin = getattr(getattr(cv2, 'ximgproc', None), 'thinning', None)                     # opencv-contrib (the networks' venv has it); else thin() below, the same pixels""",
 """_thin = getattr(getattr(cv2, 'ximgproc', None), 'thinning', None)                     # opencv-contrib (the networks' venv has it); else thin() above, the same pixels"""),
("""if not ARG.out: os.makedirs(SP + f'picks22_guided/22-{N}', exist_ok=True)
json.dump(polys, open(F_POLYS, 'w', encoding='utf8', newline='\\n'))
rep = dict(plate=N, area=AREA, lines=LINES, version=outline_version(), blocks=nblocks, sides=cnt['sides'], on_printed_line=cnt['on_printed_line'], on_detected_line=cnt['on_detected_line'], short_pieces=cnt['short_pieces'],""",
 """if not ARG.out: os.makedirs(SP + f'picks22_guided/22-{N}', exist_ok=True)
if mask8 is not None: cv2.imwrite(F_MAP, mask8.astype(np.uint8) * 255)   # the map ground first, N_outlines.json (with the version) last: ink_bins.py reads all three
elif os.path.exists(F_MAP): os.remove(F_MAP)             # no map ground this time: an older one would be read as this run's
json.dump(polys, open(F_POLYS, 'w', encoding='utf8', newline='\\n'))
rep = dict(plate=N, area=AREA, lines=LINES, version=VER, blocks=nblocks, sides=cnt['sides'], on_printed_line=cnt['on_printed_line'], on_detected_line=cnt['on_detected_line'], short_pieces=cnt['short_pieces'], open_outlines=OPEN[0],"""),
("""json.dump(rep, open(F_REP, 'w', encoding='utf8', newline='\\n'), indent=1)
cv2.imwrite(F_JPG, cv2.resize(vis, None, fx=0.5, fy=0.5, interpolation=cv2.INTER_AREA), [cv2.IMWRITE_JPEG_QUALITY, 85])
cv2.imwrite(F_MASK, cv2.resize(block * 255, (W // 2, H // 2), interpolation=cv2.INTER_NEAREST))
if mask8 is not None: cv2.imwrite(F_MAP, mask8.astype(np.uint8) * 255)
if ARG.out: cv2.imwrite(O + f'{N}_blockinst.png', cv2.resize(inst.astype(np.uint16), (W // 2, H // 2), interpolation=cv2.INTER_NEAREST))
""",
 """cv2.imwrite(F_JPG, cv2.resize(vis, None, fx=0.5, fy=0.5, interpolation=cv2.INTER_AREA), [cv2.IMWRITE_JPEG_QUALITY, 85])
cv2.imwrite(F_MASK, cv2.resize(block * 255, (W // 2, H // 2), interpolation=cv2.INTER_NEAREST))
if ARG.out: cv2.imwrite(O + f'{N}_blockinst.png', cv2.resize(inst.astype(np.uint16), (W // 2, H // 2), interpolation=cv2.INTER_NEAREST))
json.dump(rep, open(F_REP + '.tmp', 'w', encoding='utf8', newline='\\n'), indent=1); os.replace(F_REP + '.tmp', F_REP)
"""),
]
for a, b in R:
    assert s.count(a) == 1, a[:80]
    s = s.replace(a, b)
open(p, 'w', encoding='utf8', newline='').write(s)
print('ok')
