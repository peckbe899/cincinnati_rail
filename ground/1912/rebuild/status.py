"""Update ground/1912/STATUS.json (SPEC section 7). The commit field is the last pushed commit, filled by the caller."""
import json, subprocess, sys
from datetime import datetime, timezone
from pathlib import Path

STATUS = Path(__file__).resolve().parent.parent / 'STATUS.json'


def update(stage, note, done=False, blocked_on=None, commit=None):
    s = json.loads(STATUS.read_text()) if STATUS.exists() else {'notes': ''}
    if commit is None:
        commit = subprocess.run(['git', 'rev-parse', 'HEAD'], capture_output=True, text=True,
                                cwd=STATUS.parent).stdout.strip()
    notes = [n for n in (s.get('notes') or '').split('\n') if n]
    if note:
        notes.append(f"{stage}: {note}")
    s.update(stage=stage, commit=commit, updated=datetime.now(timezone.utc).isoformat(timespec='seconds'),
             done=bool(done), blocked_on=blocked_on, notes='\n'.join(notes))
    STATUS.write_text(json.dumps(s, indent=1) + '\n')
    return s


if __name__ == '__main__':
    stage, note = sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else ''
    print(json.dumps(update(stage, note, done=(stage == 'done')), indent=1))
