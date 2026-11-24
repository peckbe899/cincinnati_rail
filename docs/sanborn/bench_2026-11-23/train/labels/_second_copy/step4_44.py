# 44's editor lines from the merged outline step on the batch's maps (blocks_noguide.step4), into my folder only
import json, sys
sys.path.insert(0, '../../tools/sanborn/unet'); sys.path.insert(0, '../../tools/sanborn')
from blocks_noguide import step4
d = 'bench_2026-11-23/train/labels/batch44/'
e = step4(json.load(open(d + 'outlines.json', encoding='utf8')))
json.dump(e, open(d + '44_edges.json', 'w', encoding='utf8', newline='\n'))
print(len(e), sum(x['state'] == 'green' for x in e))
