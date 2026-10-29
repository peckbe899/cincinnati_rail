// The Chronology timeline as Markdown (Ben, 29 October): data/profile/chronology_timeline.md, from the hub's record
// (hub/seed/chronology/segments.json, else data/profile/chronology.json) and the routes (data/profile/chronology_lines.json).
// The hub's Export runs it; the Chronology page's "Timeline (.md)" button gives the same file for the record as it is now.
// Usage: node tools/chronology_timeline.js [record.json] [out.md]
const fs = require('fs'), path = require('path');
const ROOT = path.resolve(__dirname, '..'), C = require(path.join(ROOT, 'hub', 'static', 'chronology_rules.js'));
const recF = process.argv[2] || [path.join(ROOT, 'hub', 'seed', 'chronology', 'segments.json'), path.join(ROOT, 'data', 'profile', 'chronology.json')].find((f) => fs.existsSync(f));
const out = process.argv[3] || path.join(ROOT, 'data', 'profile', 'chronology_timeline.md');
const routes = JSON.parse(fs.readFileSync(path.join(ROOT, 'data', 'profile', 'chronology_lines.json'), 'utf8')).routes;
const md = C.timeline(routes, JSON.parse(fs.readFileSync(recF, 'utf8')));
fs.writeFileSync(out, md);
console.log(`timeline: ${md.split('\n').length} lines -> ${path.relative(ROOT, out)}`);
