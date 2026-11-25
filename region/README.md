# The new hub: Ben's runbook

The new hub is the program in `region/`. It keeps the design as versioned records in one SQLite database in a folder
called `var`, and serves its web app at **http://127.0.0.1:8766**. The old hub (`hub/`, `python hub\hub.py`) keeps
running exactly as before at **http://127.0.0.1:8765**, with its own database `hub\hub.db`. The two never share a
database file, so you can run either one, or both at once.

Every command below is `crhub <command>`. On Windows you type `.\crhub` in PowerShell, from the repo folder (it runs
`crhub.cmd`, which works under any execution policy). On Linux you type `./crhub`. With no command, `crhub` serves.

The architecture is in `claude/Hub_Region_Architecture.md`; the conventions every package follows are in
`region/core/README.md`.

## What you need once per machine

- **Python 3.12, 64-bit**, from python.org (you have 3.12.10). Doctor accepts 3.12 or later.
- **Node 24 LTS**, or Node 22.18 or later, from nodejs.org. npm comes with it.
- **git**.
- **uv** is optional. Install it only once you decide to (9.21): `winget install --id astral-sh.uv -e`. Without uv,
  everything below works through `.venv` and pip.

## First run on Windows, step by step

Do these in order, in a PowerShell window opened in the repo folder (step 8 uses a second one). Stop the old hub
(Ctrl+C in its window) before step 4: setup installs packages into the repo's `.venv`, which the old hub runs from,
and Windows refuses to replace a package file a running program has loaded (pip then fails with `[WinError 5]
Access is denied`). Setup checks this and says so. Restart the old hub after step 4 if you want it; from then on it
can run beside the new hub, which never touches `hub\`, `hub\hub.db` or port 8765. Each step shows what it prints when
it works; if a step prints something else, stop there and send it back (see "What to send back" under "When doctor
fails").

**1. Get the branch.**

```powershell
git fetch
git switch hub_region
git pull
```

It ends with `Already up to date.` or a list of the files it pulled. `git status` then says `On branch hub_region`.

**2. Check Python and Node.**

```powershell
py -3.12 --version
node --version
```

The first prints `Python 3.12.10`; the second `v24.` something, or `v22.18` or later.

**3. Make sure `.venv` exists.** Without uv, `.\crhub` runs the hub with the Python in the repo's `.venv`. If the
repo already has `.venv\Scripts\python.exe`, skip this step. Otherwise:

```powershell
py -3.12 -m venv .venv
.venv\Scripts\python -m pip install -r requirements.lock -e .
```

The second command ends with `Successfully installed ...`.

**4. Set up.**

```powershell
.\crhub setup
```

It takes a few minutes the first time and prints, step by step:

```text
crhub setup: <the repo folder>
[1/6] python   <repo>\.venv\Scripts\python.exe -m pip install -r requirements.lock -e .
...                                    (pip's lines, ending "Successfully installed ...")
[2/6] npm      <...>\npm.CMD ci
added 193 packages, and audited 196 packages in 13s
...                                    (npm's audit note about vulnerabilities is usual; nothing to do)
[3/6] build    <...>\npm.CMD run build -w app
...
✓ built in 1.10s
[4/6] migrate  create or migrate var/region.db (a checked backup first)
      created C:\Users\<you>\AppData\Local\CincinnatiRail\hub\region.db at schema 2
[5/6] imports  the first imports
  importer       layer               created   updated unchanged   deleted conflicts
  registry       import:registry         300         0         0         0         0
  profile_lines  import:profiles        1421         0         0         0         0
  old_hub        legacy:old_hub          475       449         3         0         0
[6/6] doctor   crhub doctor
  ok    python                 3.12.10, 64-bit, <repo>\.venv\Scripts\python.exe
  ...                                  (one row per check)
21 ok, 0 warning(s), 0 failure(s): the hub can run here
crhub setup: done. Start the hub with crhub (or crhub serve).
```

The counts are the ones CI's Windows runner printed for this branch; the `old_hub` row follows what your `hub\seed`
holds, so it can differ a little. If the repo is inside OneDrive, doctor counts one warning (`repo`): that is not a
failure. The first setup applies the imports. A later `.\crhub setup` applies nothing: it makes a dry run of each
import and prints `(dry run)` beside its counts, and, when something would change, the command that applies it
(`crhub imports apply <run>`). Read the counts, then run that command.

**5. Serve.**

```powershell
.\crhub
```

It prints, then opens http://127.0.0.1:8766 in your browser:

```text
lock      C:\Users\<you>\AppData\Local\CincinnatiRail\hub\hub.lock (pid 1234)
database  C:\Users\<you>\AppData\Local\CincinnatiRail\hub\region.db (quick_check ok)
migrate   up to date
backups   region-20261122T080000Z-daily.db, region-20261122T080000Z-weekly.db in C:\Users\<you>\...\hub\backups
seeds     none in <repo>\region\seed
imports   every importer's sources are as last applied
tiers     5 present, 1 partial, 0 missing (ground_1912_real partial: stage contours)
engine    starting 2 sidecar(s) in the background
jobs      scheduler on C:\Users\<you>\AppData\Local\CincinnatiRail\hub\cache\cache.db
app       app/dist is current
serving   http://127.0.0.1:8766  (Ctrl+C stops)
```

The page shows the map with the 16 Metro sections. The status bar at the bottom says `events: live`, `jobs: idle` and,
within a few seconds, `engine: ready`. Leave this window open: the hub runs as long as it does.

**6. Open Line 6.** Press Ctrl+K, type `Line 6` (or the old key `Line_6`) and press Enter. The line sheet opens, titled
`Line 6`, with the ground (brown) and the rail (blue), the PVI and station tables under it, and the inspector beside it.

**7. Try an edit in a scenario.** The old hub owns the profiles on `main` for now, so edits go into a scenario. In
`Layer` at the top, choose `New scenario...`, type `try` and press Enter (do this once: a second `try` is refused
with `layer try exists`). With `try` chosen in `Layer`, change a PVI level in the sheet's table and press Enter. The
rail redraws at once (the sheet shows `local solve` in milliseconds); a moment later the header shows
`server <key>, max diff 0 m`: the hub's own solve, sent back over the event stream, agrees. For that moment it may
still show the previous key with a diff such as `max diff 0.363 m`: that is the hub's solve from before the edit,
compared with the new rail, and it changes to the new key and `0 m` within a second. The edit is saved on `try`
as version 2 of the Line 6 profile: a scenario's first edit of a record continues its numbering from the version
below (here the old hub's version 1), and the app says `Saved PVI 1 level on Line 6 profile: version 2 on try.`
(for the first PVI). `main` is unchanged. Enter also left the cell, so press Ctrl+Z now: the edit is undone as
version 3, equal to version 1 (`Undone: ..., now version 3 on try.`). While a cell still holds text you typed and have
not saved, Ctrl+Z undoes your typing in that cell instead.

**8. Check the machine with the hub running.** In a second PowerShell window, in the repo folder:

```powershell
.\crhub doctor
```

The `port 8766` row now says `the hub is serving at http://127.0.0.1:8766: crhub serve (pid 1234, port 8766, ...)`
and the last line is `21 ok, 0 warning(s), 0 failure(s): the hub can run here`.

**9. Stop.** Ctrl+C in the hub's window. It prints `stopped   scheduler stopped, engine closed, WAL truncated, lock
released`. Because `.\crhub` is a `.cmd` file, Windows then asks `Terminate batch job (Y/N)?`: answer `Y`. The hub has
already stopped by then; the question is only about the launcher.

### Without uv, with uv

Everything above works through `.venv` and pip. Once you choose to install uv (`winget install --id astral-sh.uv -e`),
`.\crhub` runs through `uv run --locked` instead and `.\crhub setup` installs with `uv sync --locked --inexact` into
`.venv`. Nothing else changes.

### Linux

```sh
git pull
./crhub setup
./crhub serve --no-browser
```

### What setup does

`crhub setup` runs these steps and stops at the first that fails:

1. **Python packages.** With uv: `uv sync --locked --inexact` (the `--inexact` keeps any package you installed by
   hand). Without uv: `.venv\Scripts\python -m pip install -r requirements.lock -e .`.
2. **`npm ci`**: the engine's and the app's packages, from `package-lock.json`.
3. **`npm run build -w app`**: builds the web app into `app\dist`.
4. **The database.** Creates `var\region.db`, or migrates it after a checked backup into `var\backups`.
5. **The first imports**: the registry (sections, stations, params), the Metro line files (profiles, and each
   section's streets and roads from `data\profile\context\lines.json`) and the old hub's seed (`legacy:old_hub`:
   the alignments with Ben's access choices, each platform's side or island, the station complexes and the
   Chronology).
6. **`crhub doctor`**, whose table ends the run. Setup's exit code is the doctor's.

Setup refuses to start while the new hub is serving, or while `crhub jobs run` holds the hub's lock: stop it first
(Ctrl+C in its window). It says which process holds the lock (`var\hub.lock`). The old hub can keep running.
`crhub setup --dry-run` prints the steps without running anything. `--skip-npm`, `--skip-build`, `--skip-python`,
`--skip-migrate`, `--skip-imports` and `--no-doctor` leave one step out.

Run `crhub setup` again after any `git pull` that changes `uv.lock`, `requirements.lock`, `package-lock.json`, the
app or the engine. It is always safe to run: the Python and database steps do nothing when nothing changed, the
imports are dry runs (see step 4), and `npm ci` reinstalls `node_modules` and the app is built again every time.
Stop the old hub first when the pull changed `requirements.lock` (setup says so when it is running from `.venv`).

## Every day

```powershell
git pull
.\crhub                 # serve; opens http://127.0.0.1:8766
```

`crhub serve` (which is what `crhub` with no command runs) never runs npm and never touches the network. In order, it:

1. takes the single-instance lock (a second `crhub` says which one is already running);
2. checks the database (`quick_check`);
3. backs up, then migrates, when a migration is pending;
4. takes the daily and weekly backups that are due (and again once a day while it serves);
5. takes in the seeds you pulled (`region/seed`) and prints what changed (a pre-import backup first when that
   changes records). A seed file it cannot read (merge-conflict markers, a file saved in another encoding) is named
   with its path, and serving goes on without that layer;
6. scans the data tiers;
7. starts the live hub (next section), which brings every import up to its files in the background;
8. serves at http://127.0.0.1:8766.

It refuses to create an empty database: before `crhub setup` it says `no database at ...: run crhub setup to create
it` and leaves no `var` folder behind. It shows a banner when `app\dist` is older than the app's source;
`npm run build -w app` (or `crhub setup`) clears it. Stop it with Ctrl+C.

`crhub serve --no-browser` serves without opening a browser; `--port` serves on another port.

### Always live: no commands for daily updates

While the hub serves it watches everything it reads from outside its database, and takes a change in as soon as it is
saved. You do not run anything, in PowerShell or anywhere else:

- **the Metro line files** (`data\profile\lines`, what a Deck tie writes), read as they are on disk;
- **the old hub**: its live database `hub\hub.db` while you work in it (read through a copy, never the file itself),
  and its `hub\seed` export;
- **the rule registry** (`rules\registry.yaml`);
- **every data tier**: the 1912 ground's `STATUS.json`, the Sanborn tiles' index, the Deck's files, and the others in
  `configs\hub_paths.json`.

What happens when you save:

1. The hub waits until the files have been quiet for 1.5 s (a Deck tie writing all sixteen line files, or a file
   still being written, is one change), then reads them.
2. If they hold the same as last time (a file saved again unchanged), nothing runs.
3. Otherwise the import is checked first (a dry run). One that cannot be read (a half-written file, a deleted file,
   a folder that is not there) is reported and nothing changes; it is tried again when the file changes, and a toast
   says when it can be read again. A file another program holds open (Excel, OneDrive, a virus scanner) is looked
   at again a few times over the next minute, quietly, and taken in once it is free. Each file is read once into a
   copy that is both hashed and imported, so what the import records is exactly what it read.
4. It is then taken in as one import, which Undo this import reverts. **It never overrides your edits:** they sit in
   your layers above the import, a change that touches nothing you changed comes through, and a change that touches
   your edit (a station moved under a profile you edited, a field you changed) waits in the **Review** pane while
   your version stays what you see.
5. Only what the change touched is solved again: a change to Line 3's file re-solves Line 3 and nothing else, a note
   re-solves nothing, and the line in the pane you are looking at is solved first.

What you see: a toast in plain words (`Line 3 updated from the old hub: 2 stations moved, re-solving`, `1912 ground:
stage contours to surface, ready to use`), the open panes updating in place (your selection, zoom and unsaved edits
stay), a `re-solving…` mark on the line sheet while its line is being solved, and the **Sources chip** in the status
bar: `live`, `live: 2 pending` while changes are being taken in, `live: paused`, and when the last change came in.

**The Sources pane** (click the chip, or Ctrl+K and `Show the sources`) lists each source, its state, when it last
changed and what that change did, and the last ten changes. Its buttons:

- **Pause live** stops taking changes in (the hub keeps watching, and the chip counts what waits); **Resume live**
  takes in everything that changed meanwhile. The pause is kept across a restart of the hub, and serve says so.
  While paused the hub holds no handle on `hub\hub.db`, so the old hub can replace or delete it.
- **Undo this import** (also on the toast) reverts that source's last import as one change, and closes the Review
  items that import raised (they were about changes that are gone now). It stays offered until a newer import from
  the same source replaces it, even after a re-save or a file that could not be read. The same files are then
  held: they are not taken in again until they change, and **Apply** takes them in anyway.
- **Check now** looks at a source at once.

A big import (a Deck tie) is written in parts so your edits never wait long. If the hub is stopped between two
parts (the window closed, the machine shut down), the next import closes what was written as one change you can
undo, puts the changes that touch your edits in Review, and writes the rest. The old hub's own bookkeeping (its
pipeline log) changes `hub.db` without changing any document: the hub sees that and reads nothing. A file saved in a
folder the hub only keeps an eye on (the project folder above the repo, which holds `3D_Artifacts`, or `data\profile`
beside the line files) is not a change: the chip, the pane and its history stay as they were, unless the save moves
that tier's status or something a result reads.

`crhub serve --no-live` (or `"live": {"enabled": false}` in `configs\local.json`) serves without watching: serve then
reports changed sources at start as dry runs, to apply with `crhub imports apply <run>`. Other settings under `"live"`
in `configs\local.json`: `settle_s` (1.5, counted from the file's own write time), `poll_s` (0.25), `yield_s` (0.4:
after an import that changed something, the next one waits this long so the open sheets read the change first) and
`old_hub_db` (`hub/hub.db`; null to stop watching the old hub's database). `crhub rebuild` and CI still read the line
files and the old hub's seed from git.

Lines 10, 11 and 13 have no saved design: the hub solves their default design (the old page's levels and river bend
points), draws their rail with it, marked "default design (not saved)", and gives it to every line that crosses them.
It is never written to the profile; it becomes the design only when the line is edited. A profile saved against
older stop points (Line 2b) is solved, and read by the lines crossing it, mapped onto the current stops, as the old
page read it; its rail result is still the profile as saved.

### Run times on the line sheet

Under the structure strip the sheet draws the **run times** of the line's route (railsim, run by the hub): the speed
each way against the posted limit, the run time of each leg, and in the header the trip time each way, the era and
the train. The **Run times** card under the line panel has the station table both ways (run, dwell, arrive, depart,
scheduled, top speed), the totals, the round trip, "Where the time goes" (folded; it asks the hub for the cost of
each restriction only while it is open), the sources in plain words, and Export CSV.

- While you edit, the sheet runs your **unsaved** edit (a draft run) once your drag is over and the solve has
  landed: the new times show within a second or two, marked "draft", with the change against the saved run. Nothing
  is run while you drag. Undo back to the saved profile shows the saved run again.
- When you save, the hub runs the saved records (2 to 3 s on Line 6) and the band takes that run. A change that
  leaves the rail, the tunnels and the stations as they were (a paint, a note) runs nothing.
- The run comes after what you look at. The sheet asks for it once its first solves have landed (at the latest 10 s
  after it opens the line; until then the band says "updating" and keeps its place, so nothing moves under your
  mouse), and while a saved line file is imported, and the section in front of you is solved again, the hub holds
  the run's work back (for 10 s at most). So a line file you save reaches the open sheet in about 2 s, even on a
  fresh hub still working out its first run. It holds it back too while a save from a sheet, or a sheet's read of a
  line, is served, so a level you save shows in another tab on the same line within a second; when two tabs on one
  line ask for its run, the hub works it out once.
- The run reads only the hub's records and the files in the repo: the line config (`configs\metro`), the eras
  (`data\operations`) and the trains (`data\rollingstock`). No KMZ, no network, nothing is written.
- The curves are fitted to the line's drawn path for now (no horizontal alignment of its own yet), so run times
  differ from railsim's own KMZ runs by the curves: on Line 6 under 1 % on the trip, up to about 40 s at a station.
- `ground.source` (not registered yet: `line_file`) picks the ground the profiles read: the line file's, or the
  ground model's (`region`) for the view's year. The station panel's ground row and the run's sources say which.

## Commands

| Command | What it does |
|---|---|
| `crhub setup` | installs the packages, builds the app, creates or migrates the database, runs doctor |
| `crhub` or `crhub serve` | serves the hub at http://127.0.0.1:8766 |
| `crhub doctor` | checks this machine, `var`, the ports, the data tiers, the app build and the database |
| `crhub doctor --data` | the same, and validates every record again (slower; reads the database read-only, never changes it) |
| `crhub export` | before you commit: takes in pulled seeds first, then writes `main` and your proposals to `region/seed` (through the hub while it serves) |
| `crhub backup` | a checked backup of the database into `var\backups` (through the hub while it serves) |
| `crhub restore <file>` | puts a backup back (the current database is backed up first); refuses while the hub serves |
| `crhub conflicts list` | the open conflicts (the review queue); `(seed)` marks the ones that block export |
| `crhub conflicts resolve <id> --take ours` | keeps your revision (`--take theirs` takes the other side; `--all` resolves every open one, `--seed` only the seed ones) |
| `crhub imports status` | which importers' sources changed since their last applied import |
| `crhub imports run [name] --dry-run` | a dry run of the imports (through the hub while it serves); without `--dry-run` it applies them |
| `crhub imports apply <run>` | applies a dry run, refused when its sources changed since (through the hub while it serves) |
| `crhub rebuild --compare` | rebuilds a database from git into `var\rebuild` and compares it with yours; never touches yours |
| `crhub model migrate` | applies pending migrations, backing up first (serve and setup do this for you); refuses while the hub serves |
| `crhub model import` | takes in pulled seeds without exporting; refuses while the hub serves (serve did it at start, and export does it first) |
| `crhub model check` | `quick_check`, then every record validated again (read-only: safe while the hub runs) |
| `crhub model info` | the schema version, the layers and how many records each holds (read-only) |
| `crhub jobs list` | the queued and running jobs; `crhub jobs show <job>` prints one job and its log |
| `crhub info` | where this hub finds its repo, `var`, configs, tiers and features |
| `python -m region.tiers` | the data tier scan on its own (`--json` for the same as `GET /api/v1/tiers`) |

`crhub --help` lists every command, and `crhub <command> --help` its options. `crhub export`, `crhub backup` and
`crhub restore` are short names for `crhub model export`, `crhub model backup` and `crhub model restore`: either
spelling does the same.

**Beside a running hub.** While `crhub serve` runs, only it writes the database. `crhub export`, `crhub backup`,
`crhub conflicts` and `crhub imports run` and `apply` then ask it over HTTP (they print `through the hub serving at
http://127.0.0.1:8766`), so you can run them in a second window without stopping it. They never use a proxy for the
hub's address. `crhub export` refuses a hub that serves from another checkout of the repo, since that hub would write
the other checkout's `region/seed`. `crhub model import` and `crhub model migrate` refuse and say what to do instead. The
commands that write the database themselves (`crhub restore`, `crhub model migrate`, `export` and `import` with no hub
running, `crhub jobs run`, `crhub jobs wipe`) hold the hub's lock while they work, so each refuses while the hub serves
and names the process that holds the lock.

### Export, then commit

Your design reaches git only through `region/seed` (`main` and your proposals; scenarios stay on this machine).
Before you commit (the hub can keep running):

```powershell
.\crhub export
git add region/seed
git commit -m "Hub export"
```

Export prints the folder it wrote (`into ...`). It first takes in any seed changes you pulled. A layer where one of them
conflicts with a change of yours is not written, so export never overwrites something it has not merged; the other
layers are written, and export ends with `export refused for main: ... resolve them first`. Then:

```powershell
.\crhub conflicts list
.\crhub conflicts resolve <id> --take ours     # keep yours (or --take theirs for the pulled one)
.\crhub export
```

Scenarios are not exported: they stay in this machine's database only (and its backups). Work you want in git goes
in `main` or a proposal. Two exports in a row give the same bytes (the second prints `0 written`), with the hub
running or not. A promoted proposal takes no more seed changes, so export leaves its folder as it is when the folder
holds changes the database never took in (a cloud session's work after the promote). A proposal is named `proposal:<name>` (its folder is
`region/seed/proposals/<name>`); the hub refuses to make a proposal with any other name. A proposal whose parent
layer is not in your database (a scenario that lives only on the machine that made it) is not taken in: export lists
it as not imported and leaves its folder in `region/seed/proposals` as it is.

### Backups and restore

- Serve and setup back up before every migration. Those backups are kept forever, as are the ones you make with
  `crhub backup`.
- Serve takes a daily and a weekly backup, and every import or seed import that changes records takes a pre-import
  one first. Pre-import backups keep the newest 10, daily ones 14 and weekly ones 8.
- Every backup is checked with `quick_check` before it gets its name, so a file in `var\backups` is always whole.
- To restore, stop the hub, then give the full path of the backup (on Windows `var` is not in the repo):

  ```powershell
  .\crhub restore "$env:LOCALAPPDATA\CincinnatiRail\hub\backups\region-<time>-<reason>.db"
  ```

  It refuses while the hub serves, refuses a file that is not a hub database (the old hub's `hub\hub.db`, say), and
  refuses a backup of another database unless you add `--force`. It prints how many records the database you replace
  holds and how many the backup holds. The database you replace is backed up first, so a restore can be undone the
  same way.
- **A restore and `region/seed`.** `region/seed` usually holds exports newer than the backup. The next start (or
  export) takes nothing from it silently: every record where `region/seed` and the restored database differ is listed
  as a seed conflict, and a banner says how many. To keep the restored state, run
  `.\crhub conflicts resolve --all --seed --take ours`, then `.\crhub export` writes it into `region/seed`. To take
  `region/seed`'s instead (after restoring a damaged database, say), use `--take theirs`.

### Rebuild

`crhub rebuild --compare` builds a fresh database from what is in git (imports and seeds) into `var\rebuild` and lists
every difference from your database. It never touches your database. Use it to check that git holds everything
before you move to another machine, or after a large pull.

## Where things live

- **`var`**, the hub's own folder: `region.db` (the design), `cache.db` (results that can always be rebuilt),
  `cache\blobs`, `logs` (one file per day, kept 30 days), `backups`, and `live\state.json` (whether live is paused,
  and the imports you undid).
  - On Windows it is `%LOCALAPPDATA%\CincinnatiRail\hub`, not the repo under Documents, because OneDrive often syncs
    Documents and sync clients corrupt SQLite databases. On Linux it is the repo's `var` folder.
  - To move it, set `"var"` in `configs/local.json`, or the `CRHUB_VAR` environment variable for one session.
  - `crhub info` shows which folder is in use and why.
- **`configs/local.json`** holds this machine's settings only (it is not in git). Copy `configs/local.example.json` to
  start one. It can move `var`, change the port, point `engine.node` at a `node.exe`, and move a data tier's root:
  `{"tiers": {"ground_1912_real": {"root": "D:/cr/ground/1912"}}}`.
- **Data tiers** are the lane-B folders the hub reads but never writes, listed in `configs/hub_paths.json`: the 1912
  ground, the 2026 ground, the Sanborn tiles, the Deck's files, the old hub's seed and the Metro line files. Each is
  present, partial or missing. A missing or partial tier shows as a status chip and as the reason a map layer is
  unavailable; only a missing required tier (the old hub's seed, the line files) makes doctor fail. The 1912 surface
  stays partial until `ground/1912/STATUS.json` says `"done": true`; the moment it does, the live hub turns the
  `real_1912` ground layer record available and tells you.

## The old hub and the new hub side by side

| | Old hub | New hub |
|---|---|---|
| Start | `python hub\hub.py` | `.\crhub` |
| Address | http://127.0.0.1:8765 | http://127.0.0.1:8766 |
| Database | `hub\hub.db` | `var\region.db` |
| Into git | its Export button or `python hub\hub.py export` writes `hub/seed` | `crhub export` writes `region/seed` |
| Pages | Deck, Profiles, Station 3D, Chronology | the map, the line sheet, the inspector, jobs, the review queue |

- **Nothing in the old hub changes.** It keeps its database, its pages, its tests and its port.
- **The new hub follows the old one live.** While both run, a save in the old hub reaches the new hub within a few
  seconds: the new hub reads `hub\hub.db` through a copy made with SQLite's backup API (never the live file, and it
  never writes it), and shows a toast such as `Line 3 updated from the old hub: 2 stations moved, re-solving`. Without
  `hub\hub.db` (a fresh clone) it reads `hub/seed`. Export in the old hub as before, so git has your changes too.
- **Who owns what.** Each kind of record has an `authority` record saying which hub owns it (plan geometry stays
  with the old hub until the Deck adapter lands). While the old hub owns a kind, the new hub refuses edits to it on
  `main`, and says so. Scenarios stay editable, so you can try designs in the new hub
  without forking the truth. A kind moves to the new hub by one ruling, later.
- **The new hub's Old hub pane** links to the old hub's pages on 8765.
- **Running both.** Start each in its own PowerShell window, from the repo folder:

  ```powershell
  python hub\hub.py        # window 1: the old hub, http://127.0.0.1:8765
  .\crhub                  # window 2: the new hub, http://127.0.0.1:8766
  ```

  The two never share a file or a port. Stop each with Ctrl+C in its own window. Doctor shows port 8765 as
  information only (`the old hub is running at http://127.0.0.1:8765`, or that it is free). If the old hub was started
  on 8766 by mistake, doctor fails the `port 8766` row and says so.
- **Before you pull:** Export in the old hub and run `.\crhub export`, so your own changes are in git too.

## When doctor fails

Doctor prints one row per check: `ok`, `info`, `skip`, `warn` or `FAIL`, and under each warning or failure a line
starting `->` that says what to do. It exits 1 only when a row says `FAIL`: something that stops the hub from running
or puts the design at risk. Warnings and missing optional tiers never fail it. `crhub doctor --json` gives the same as
JSON.

| Row | When it fails | What to do |
|---|---|---|
| `python` | Python older than 3.12, or 32-bit | install the 64-bit Python 3.12 from python.org, then `.\crhub setup` |
| `packages` | a package the hub runs on is missing (a version mismatch only warns) | `.\crhub setup` |
| `sqlite` | SQLite older than 3.38, or without JSON or window functions | use the python.org build of Python 3.12 |
| `rtree` | SQLite has no R-tree module (the store's spatial index needs it) | use the python.org build of Python 3.12; others can lack it |
| `node` | no Node, a Node older than 22.18, or one that does not strip TypeScript types | install Node 24 LTS, or set `engine.node` in `configs/local.json` |
| `npm` | `node_modules` missing, or a workspace linked to another checkout (stale packages only warn) | `npm ci`, or `.\crhub setup` |
| `var` | `var` is inside OneDrive, Dropbox, Google Drive or iCloud Drive, or on a network share | set `"var"` in `configs/local.json` to a local folder that is not synced (the default `%LOCALAPPDATA%\CincinnatiRail\hub` is right) |
| `var write` | the folder cannot be written | check its permissions, or move `var` as above |
| `port 8766` | another program, or the old hub, holds the new hub's port | stop it, or set `"port"` in `configs/local.json`; if Windows reserves the port, `netsh interface ipv4 show excludedportrange protocol=tcp` lists the reserved ranges |
| `tier <name>` | a required tier is missing | restore it with git (`git checkout -- hub/seed data/profile`), or set its root in `configs/local.json` |
| `app` | `app\dist` has not been built (older than its source only warns) | `npm run build -w app`, or `.\crhub setup` |
| `database` | `var\region.db` fails `quick_check`, or the store cannot be loaded | for `quick_check`: stop the hub, then restore the newest backup from `var\backups`; for the store: `.\crhub setup` |
| `records` (with `--data`) | a record fails its kind's validation | `.\crhub model check` lists them all |

A row that says "the check itself failed" is a bug in doctor: the other rows still ran. Copy the row into a session.

How doctor tells a synced folder: by the folder names the sync clients use (`OneDrive...`, `Dropbox`, `My Drive`,
`iCloudDrive`, `Mobile Documents`), by the `OneDrive` environment variables, by the folders Dropbox lists in its own
`info.json`, by the marker files the clients leave in the root they sync, and on Windows by the attributes the cloud
files system sets on synced folders.

### What to send back

If doctor fails, or any step of the first run prints something other than what it shows, paste these into a session,
as text (copy from the PowerShell window; no screenshots needed):

1. the whole doctor table: `.\crhub doctor`, from the first row to the `ok, ... warning(s), ... failure(s)` line;
2. the JSON form: `.\crhub doctor --json`;
3. `.\crhub info` (where the hub finds its repo, `var`, configs and tiers);
4. the output of the step that went wrong, from its `[n/6]` line (setup) or its first line (serve) to the end;
5. if `.\crhub` started and then failed: the last 50 lines of the newest log in `var\logs` (this is the default
   `var`; if you moved it, use the folder `.\crhub info` names),
   `Get-ChildItem "$env:LOCALAPPDATA\CincinnatiRail\hub\logs" | Sort-Object LastWriteTime | Select-Object -Last 1 | Get-Content -Tail 50`.

None of these hold a password or a key; they hold folder paths and version numbers.

## Trouble

- **`npm ci` fails with EPERM or EBUSY on Windows.** Something has a file in `node_modules` open: a running `crhub`,
  the old hub's browser test, an editor's TypeScript server. Close it and run `.\crhub setup` again.
- **The repo itself is in OneDrive.** Doctor warns (it does not fail): the hub's databases are in `var`, not in the
  repo, but sync clients can damage `.git` and `node_modules`. A clone outside the synced folder is safer.
- **uv says the lock is out of date.** `uv.lock` changes only through the lead's sessions; `git pull` again. Without uv
  the same holds for `requirements.lock`.
- **`.\crhub` says it found neither uv nor `.venv`.** Make the venv as in step 3 of "First run on Windows, step by
  step".
- **Setup says another program runs from `.venv`, or pip fails with `[WinError 5] Access is denied`.** The old hub (or
  another Python started from `.venv`) has a package file loaded. Stop it (Ctrl+C in its window) and run
  `.\crhub setup` again.
- **Two checkouts of the repo.** On Windows every checkout uses the same `var` (`%LOCALAPPDATA%\CincinnatiRail\hub`),
  so a worktree (`git worktree add ..\cr_hub hub_region`) and the main checkout share one database. That is safe: the
  hub remembers which checkout's `region/seed` each layer was last exported to or imported from, and when you run it
  from the other checkout it takes nothing from that one's `region/seed` silently (a banner names the other folder and
  the differences are listed as seed conflicts). `crhub export` refuses a hub serving from another checkout. Simplest
  is one checkout per `var`: in the second checkout, set `"var"` in its `configs/local.json` to a folder of its own
  (for example `%LOCALAPPDATA%\CincinnatiRail\hub-worktree`) and run `.\crhub setup` there.
- **Logs** are in `var\logs\hub-YYYY-MM-DD.jsonl`, one JSON object per line, with the `request_id` an error toast shows.
