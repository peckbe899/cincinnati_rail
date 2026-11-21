"""merge/impl: merge/staged.diff, every staged file against the repo (a/ b/ repo-relative paths, new files included,
PNGs left out), then a check that it applies: fresh copies of the repo files in merge/impl/applytest/, `git apply`
there, and every result compared byte for byte with the staged file (21 Nov 2026).
    python -B make_diff.py   -> merge/staged.diff, merge/impl/applytest/, merge/impl/make_diff.json
"""
import difflib, hashlib, json, os, shutil, subprocess
import common as C
ROOT = C.STAGED; OUT = C.MERGE + 'staged.diff'; AT = C.IMPL + 'applytest/'
NL = '\n'; MARK = '\n\\ No newline at end of file\n'   # git's marker for a file without a last newline (json.dump writes none)
files = sorted(os.path.relpath(os.path.join(d, f), ROOT).replace('\\', '/') for d, _, fs in os.walk(ROOT) for f in fs if not f.lower().endswith('.png') and '__pycache__' not in d)
parts, rec = [], []
for rel in files:
    new = open(ROOT + rel, encoding='utf8', newline='').read(); old_p = C.REPO + rel; exists = os.path.exists(old_p)
    old = open(old_p, encoding='utf8', newline='').read() if exists else ''
    if exists and old == new: rec.append(dict(file=rel, status='same as the repo')); continue
    d = [l if l.endswith(NL) else l + MARK for l in difflib.unified_diff(old.splitlines(True), new.splitlines(True), 'a/' + rel if exists else '/dev/null', 'b/' + rel, n=3)]
    head = f'diff --git a/{rel} b/{rel}' + NL + ('' if exists else 'new file mode 100644' + NL)
    parts.append(head + ''.join(d))
    rec.append(dict(file=rel, status='changed' if exists else 'new', repo_sha256=hashlib.sha256(old.encode('utf8')).hexdigest()[:16] if exists else None,
                    staged_sha256=hashlib.sha256(new.encode('utf8')).hexdigest()[:16], lines_added=sum(1 for l in d if l.startswith('+') and not l.startswith('+++')),
                    lines_removed=sum(1 for l in d if l.startswith('-') and not l.startswith('---'))))
open(OUT, 'w', encoding='utf8', newline='\n').write(''.join(parts))
# apply check on fresh copies of the repo files
shutil.rmtree(AT, ignore_errors=True); os.makedirs(AT)
for r in rec:
    if r['status'] == 'changed': os.makedirs(os.path.dirname(AT + r['file']), exist_ok=True); shutil.copy(C.REPO + r['file'], AT + r['file'])
GENV = dict(os.environ, GIT_CEILING_DIRECTORIES=os.path.dirname(AT.rstrip('/')))   # applytest lies inside the repo's tree: stop git finding the repo, so it applies as a plain patch here
chk = subprocess.run(['git', '-c', 'core.autocrlf=false', 'apply', '--check', '-v', OUT], cwd=AT, capture_output=True, text=True, env=GENV)
app = subprocess.run(['git', '-c', 'core.autocrlf=false', 'apply', OUT], cwd=AT, capture_output=True, text=True, env=GENV)
same = {r['file']: os.path.exists(AT + r['file']) and open(AT + r['file'], 'rb').read() == open(ROOT + r['file'], 'rb').read() for r in rec if r['status'] != 'same as the repo'}
res = dict(diff=OUT, diff_lines=sum(p.count(NL) for p in parts), files=rec, git_apply_check_rc=chk.returncode, git_apply_rc=app.returncode, apply_messages=(chk.stdout + chk.stderr + app.stderr)[-3000:],
           applied_equals_staged=same, all_equal=all(same.values()))
json.dump(res, open(C.IMPL + 'make_diff.json', 'w'), indent=1)
print('git apply --check rc', chk.returncode, '| git apply rc', app.returncode, '| applied files equal the staged ones:', res['all_equal'], '| diff lines', res['diff_lines'])
for r in rec: print(r)
