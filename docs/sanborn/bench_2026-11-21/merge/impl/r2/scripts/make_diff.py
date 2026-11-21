"""merge/impl/r2: merge/staged.diff, every staged file against the repo, then a check that it applies (21 Nov 2026).

    python -B make_diff.py   -> merge/staged.diff, merge/impl/r2/applytest/, merge/impl/r2/make_diff.json

Text files: unified diffs (a/ b/ repo-relative paths, new files included), made with difflib as in round 1. PNG files:
git binary patches (git diff --no-index --binary), so the 9 map_area templates travel in the diff; the plate-44 tile-grid
maps (data/sanborn/bench44_maps/grid*/44_*.png, 12 files, 4-11 MB each) are left out and are copied by hand (see the
report). The check: fresh copies of the changed repo files in merge/impl/r2/applytest/, `git apply` there (outside any
repository, core.autocrlf off), and every staged file (map PNGs aside) compared byte for byte with the result.
"""
import difflib, hashlib, json, os, shutil, subprocess
import common as C
ROOT = C.STAGED; OUT = C.MERGE + 'staged.diff'; AT = C.IMPL + 'applytest/'
NL = '\n'; MARK = '\n\\ No newline at end of file\n'   # git's marker for a file without a last newline (json.dump writes none)
GENV = dict(os.environ, GIT_CEILING_DIRECTORIES=C.MERGE.rstrip('/'))   # never find the repo: plain patches here
is_map = lambda rel: rel.startswith('data/sanborn/bench44_maps/') and rel.endswith('.png')
files = sorted(os.path.relpath(os.path.join(d, f), ROOT).replace('\\', '/') for d, _, fs in os.walk(ROOT) for f in fs if '__pycache__' not in d)
parts, rec = [], []
for rel in files:
    if is_map(rel): rec.append(dict(file=rel, status='left out (tile-grid map; copy by hand)', staged_sha256=hashlib.sha256(open(ROOT + rel, 'rb').read()).hexdigest()[:16])); continue
    old_p = C.REPO + rel; exists = os.path.exists(old_p)
    if rel.lower().endswith('.png'):
        if exists and open(old_p, 'rb').read() == open(ROOT + rel, 'rb').read(): rec.append(dict(file=rel, status='same as the repo')); continue
        assert not exists, f'{rel}: a changed binary file in the repo is not expected'
        g = subprocess.run(['git', 'diff', '--no-index', '--binary', '--', '/dev/null', rel], cwd=ROOT, capture_output=True, env=GENV)
        assert g.returncode == 1 and g.stdout.startswith(f'diff --git a/{rel} b/{rel}'.encode()), (rel, g.returncode, g.stderr[:300])
        parts.append(g.stdout.decode('ascii')); rec.append(dict(file=rel, status='new (binary)', staged_sha256=hashlib.sha256(open(ROOT + rel, 'rb').read()).hexdigest()[:16])); continue
    new = open(ROOT + rel, encoding='utf8', newline='').read()
    old = open(old_p, encoding='utf8', newline='').read() if exists else ''
    if exists and old == new: rec.append(dict(file=rel, status='same as the repo')); continue
    d = [l if l.endswith(NL) else l + MARK for l in difflib.unified_diff(old.splitlines(True), new.splitlines(True), 'a/' + rel if exists else '/dev/null', 'b/' + rel, n=3)]
    head = f'diff --git a/{rel} b/{rel}' + NL + ('' if exists else 'new file mode 100644' + NL)
    parts.append(head + ''.join(d))
    rec.append(dict(file=rel, status='changed' if exists else 'new', repo_sha256=hashlib.sha256(old.encode('utf8')).hexdigest()[:16] if exists else None,
                    staged_sha256=hashlib.sha256(new.encode('utf8')).hexdigest()[:16], lines_added=sum(1 for l in d if l.startswith('+') and not l.startswith('+++')),
                    lines_removed=sum(1 for l in d if l.startswith('-') and not l.startswith('---'))))
open(OUT, 'w', encoding='utf8', newline='\n').write(''.join(parts))
shutil.rmtree(AT, ignore_errors=True); os.makedirs(AT)
for r in rec:
    if r['status'] == 'changed': os.makedirs(os.path.dirname(AT + r['file']), exist_ok=True); shutil.copy(C.REPO + r['file'], AT + r['file'])
chk = subprocess.run(['git', '-c', 'core.autocrlf=false', 'apply', '--check', '-v', OUT], cwd=AT, capture_output=True, text=True, env=GENV)
app = subprocess.run(['git', '-c', 'core.autocrlf=false', 'apply', OUT], cwd=AT, capture_output=True, text=True, env=GENV)
same = {r['file']: os.path.exists(AT + r['file']) and open(AT + r['file'], 'rb').read() == open(ROOT + r['file'], 'rb').read() for r in rec if r['status'] in ('changed', 'new', 'new (binary)')}
res = dict(diff=OUT, diff_bytes=os.path.getsize(OUT), diff_sha256=hashlib.sha256(open(OUT, 'rb').read()).hexdigest()[:16], files=rec, git_apply_check_rc=chk.returncode, git_apply_rc=app.returncode,
           apply_messages=(chk.stdout + chk.stderr + app.stderr)[-3000:], applied_equals_staged=same, all_equal=all(same.values()), files_in_diff=len(same))
json.dump(res, open(C.IMPL + 'make_diff.json', 'w'), indent=1)
print('git apply --check rc', chk.returncode, '| git apply rc', app.returncode, '| applied files equal the staged ones:', res['all_equal'], f'({len(same)} files) | diff', res['diff_bytes'], 'bytes')
for r in rec: print(r)
