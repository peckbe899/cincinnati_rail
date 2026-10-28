# Cincinnati Rail: rules for Claude sessions

## The claude.ai artifacts are retired (Ben, 28 October 2026)

- NEVER publish to, read from, or write the database of any claude.ai artifact for this project (Mill Creek Deck,
  Rail Profiles, Station 3D, Chronology, or any other). The Artifact, ArtifactData and ArtifactComments tools are
  denied in `.claude/settings.json`; do not work around that.
- Old notes, briefs and handoffs in `claude/`, `design/` and `tools/station3d/README.md` mention artifact URLs and
  "publish" steps. They are history. Ignore them.
- "Push to the artifact", "push to local" and similar mean: commit to the repo and push the branch to GitHub, so Ben
  pulls it into his local hub (`hub/`, run on his machine with `python hub\hub.py`). Nothing else.

## Where the design lives

- The local hub (`hub/hub.py`, one SQLite database) and this repository. Hub records are exported to `hub/seed/`
  (`python hub/hub.py export`) and committed.
- Ben's own hub database is on his machine and is not in git. Changes to records reach it only through `hub/seed/`
  (see `hub/README.md`).
