"""verify-outline-quality: open line ends (no other shown line or sheet line within 10 px) in what the editor shows on
plate 44, from my runs' 44_shown.json, with my own brute-force code (crops.open_ends). Independent of open_ends44.py."""
import json, sys
sys.argv = sys.argv[:1]; sys.dont_write_bytecode = True
import crops  # noqa: E402  (no arguments: only defines functions)
for t in ('v_batch', 'v_proposed', 'v_abc_keepall'):
    sh = json.load(open(f'runs/{t}/44_shown.json')); SH = [e for e in sh if e['state'] == 'sheet']; shown = [e for e in sh if e['state'] != 'sheet']
    print(t, 'shown lines', len(shown), 'open ends', len(crops.open_ends(shown, SH)))
