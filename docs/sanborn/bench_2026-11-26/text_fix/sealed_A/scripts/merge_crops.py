"""Merge the crop lists into truth/crops.json (sealed builder A, 26 Nov 2026).
    cd data/sanborn/bench_2026-11-26/text_fix/sealed_A; python -B scripts/merge_crops.py
Inputs: truth/annot/crops_blocks.json (SA-B##, written by hand from the block draw), truth/annot/crops_ditto.json
(SA-D##, written by gen_ditto.py), truth/annot/crops_full.json (SA-F1, window from builtup.py full)."""
import json, os
A = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'truth')
out = {}
for f in ('crops_blocks.json', 'crops_ditto.json', 'crops_full.json'):
    out.update(json.load(open(os.path.join(A, 'annot', f), encoding='utf8')))
json.dump(out, open(os.path.join(A, 'crops.json'), 'w', encoding='utf8', newline='\n'), indent=1, ensure_ascii=False)
print(len(out), 'crops')
