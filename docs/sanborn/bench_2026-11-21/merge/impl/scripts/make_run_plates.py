"""merge/impl: writes the staged run_plates.py from the repo's (sha 2c6ee4a9): new docstring head and a new main() (21 Nov 2026).
The rest of the file (png_dir, pdf_dir, plates, order, prepare) is the repo's, unchanged."""
import common as C
src = open(C.REPO + 'tools/sanborn/unet/run_plates.py', encoding='utf8').read()
assert __import__('hashlib').sha256(src.encode('utf8')).hexdigest().startswith('2c6ee4a9f9d38720')
head = src[:src.index('import hashlib, json, os, re, subprocess, sys, time')]
NEW_HEAD = open(C.IMPL + 'scripts/run_plates_head.txt', encoding='utf8').read()
NEW_MAIN = open(C.IMPL + 'scripts/run_plates_main.txt', encoding='utf8').read()
s = NEW_HEAD + src[len(head):]
a = "DATA = os.path.join(REPO, 'data', 'sanborn'); INK = os.path.join(HERE, 'ink_bins.py')"
assert a in s; s = s.replace(a, a + "; RULES = ('ink_bins.py', 'street_map.py', 'rail_tracks.py')   # the ink sorting's rules (street_map.editor_lines: its block lines)")
i, j = s.index('def main():'), s.index("if __name__ == '__main__':")
s = s[:i] + NEW_MAIN + s[j:]
open(C.SU + 'run_plates.py', 'w', encoding='utf8', newline='\n').write(s); print('written', len(s))
