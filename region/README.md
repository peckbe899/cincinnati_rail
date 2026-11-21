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

Do these in order, in a PowerShell window opened in the repo folder (steps 7 and 8 use a second one). The old hub
can keep running in its own window the whole time: nothing here touches `hub\`, `hub\hub.db` or port 8765. Each step shows what it prints when it
works; if a step prints something else, stop there and send it back (see "What to send back" under "When doctor
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
  profile_lines  import:profiles        1405         0         0         0         0
  old_hub        legacy:old_hub           36        13         3         0         0
[6/6] doctor   crhub doctor
  ok    python                 3.12.10, 64-bit, <repo>\.venv\Scripts\python.exe
  ...                                  (one row per check)
21 ok, 0 warning(s), 0 failure(s): the hub can run here
crhub setup: done. Start the hub with crhub (or crhub serve).
```

The counts are the ones CI's Windows runner printed for this branch; the `old_hub` row follows what your `hub\seed`
holds, so it can differ a little. If the repo is inside OneDrive, doctor counts one warning (`repo`): that is not a
failure. A second `.\crhub setup` prints `unchanged` counts and creates nothing.

**5. Serve.**

```powershell
.\crhub
```

It prints, then opens http://127.0.0.1:8766 in your browser:

```text
lock      C:\Users\<you>\AppData\Local\CincinnatiRail\hub\hub.lock (pid 1234)
database  C:\Users\<you>\AppData\Local\CincinnatiRail\hub\region.db (quick_check ok)
migrate   up to date
seeds     none in <repo>\region\seed
tiers     5 present, 1 partial, 0 missing (ground_1912_real partial: stage contours)
engine    starting 2 sidecar(s) in the background
jobs      scheduler on C:\Users\<you>\AppData\Local\CincinnatiRail\hub\cache\cache.db
app       app/dist is current
serving   http://127.0.0.1:8766  (Ctrl+C stops)
```

The page shows the map with the 16 Metro sections. The status bar at the bottom says `events: live`, `jobs: idle` and,
within a few seconds, `engine: ready`. Leave this window open: the hub runs as long as it does.

**6. Open Line 6.** Press Ctrl+K, type `Line_6` and press Enter. The line sheet opens with the ground (brown) and the
rail (blue), the PVI and station tables under it, and the inspector beside it.

**7. Try an edit in a scenario.** The old hub owns the profiles on `main` for now, so edits go into a scenario. The
app cannot make a scenario yet; make one called `try` from a second PowerShell window (it prints the new layer):

```powershell
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8766/api/v1/layers -Headers @{"X-CR-Client"="powershell"} `
  -ContentType "application/json" -Body '{"slug": "try", "tier": "scenario", "parent": "main", "title": "try"}'
```

Reload the page, choose `try` in `Layer` at the top, change a PVI level in the sheet's table and press Enter. The
rail redraws at once (the sheet shows `local solve` in milliseconds); a moment later the header shows
`server <key>, max diff 0 m`: the hub's own solve, sent back over the event stream, agrees. For that moment it may
still show the previous key with a diff such as `max diff 0.363 m`: that is the hub's solve from before the edit,
compared with the new rail, and it changes to the new key and `0 m` within a second. The edit is saved on `try`
as version 2 of the Line 6 profile: a scenario's first edit of a record continues its numbering from the version
below (here the old hub's version 1). `main` is unchanged. Click the sheet's title (so the focus is outside the
table) and press Ctrl+Z: the edit is undone as version 3, equal to version 1.

**8. Check the machine with the hub running.** In a second PowerShell window, in the repo folder:

```powershell
.\crhub doctor
```

The `port 8766` row now says `the hub is serving at http://127.0.0.1:8766: crhub serve (pid 1234, port 8766, ...)`
and the last line is `21 ok, 0 warning(s), 0 failure(s): the hub can run here`.

**9. Stop.** Ctrl+C in the hub's window. It prints `stopped   scheduler stopped, engine closed, WAL truncated, lock
released`.

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
5. **The first imports**: the registry (sections, stations, params), the Metro line files (profiles) and the old
   hub's seed (`legacy:old_hub`).
6. **`crhub doctor`**, whose table ends the run. Setup's exit code is the doctor's.

Setup refuses to start while the new hub is serving, or while `crhub jobs run` holds the hub's lock: stop it first
(Ctrl+C in its window). It says which process holds the lock (`var\hub.lock`). The old hub can keep running.
`crhub setup --dry-run` prints the steps without running anything. `--skip-npm`, `--skip-build`, `--skip-python`,
`--skip-migrate`, `--skip-imports` and `--no-doctor` leave one step out.

Run `crhub setup` again after any `git pull` that changes `uv.lock`, `requirements.lock`, `package-lock.json`, the
app or the engine. It is always safe to run: the Python and database steps do nothing when nothing changed; `npm ci`
reinstalls `node_modules` and the app is built again every time.

## Every day

```powershell
git pull
.\crhub                 # serve; opens http://127.0.0.1:8766
```

`crhub serve` (which is what `crhub` with no command runs) never runs npm and never touches the network. In order, it:

1. takes the single-instance lock (a second `crhub` says which one is already running);
2. checks the database (`quick_check`);
3. backs up, then migrates, when a migration is pending;
4. takes in the seeds you pulled (`region/seed`) and prints what changed;
5. scans the data tiers;
6. serves at http://127.0.0.1:8766.

It refuses to create an empty database: before `crhub setup` it says `no database at ...: run crhub setup to create
it` and leaves no `var` folder behind. It shows a banner when `app\dist` is older than the app's source;
`npm run build -w app` (or `crhub setup`) clears it. Stop it with Ctrl+C.

`crhub serve --no-browser` serves without opening a browser; `--port` serves on another port.

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

**Beside a running hub.** While `crhub serve` runs, only it writes the database. `crhub export` and `crhub backup` then
ask it over HTTP (they print `through the hub serving at http://127.0.0.1:8766`), so you can run them in a second
window without stopping it. `crhub model import` and `crhub model migrate` refuse and say what to do instead. The
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

Export first takes in any seed changes you pulled, and refuses while one of them conflicts with a change of yours, so
it never overwrites something it has not merged. Two exports in a row give the same bytes (the second prints
`0 written`), with the hub running or not. A proposal is named `proposal:<name>` (its folder is
`region/seed/proposals/<name>`); the hub refuses to make a proposal with any other name. A proposal whose parent
layer is not in your database (a scenario that lives only on the machine that made it) is not taken in: export lists
it as not imported and leaves its folder in `region/seed/proposals` as it is.

### Backups and restore

- Serve and setup back up before every migration. Those backups are kept forever, as are the ones you make with
  `crhub backup`.
- Pre-import backups keep the newest 10, daily ones 14 and weekly ones 8.
- Every backup is checked with `quick_check` before it gets its name, so a file in `var\backups` is always whole.
- To restore, stop the hub, then `.\crhub restore var\backups\region-<time>-<reason>.db` (use the full path
  `crhub info` shows for `var`). It refuses while the hub serves. The database you replace is backed up first, so a
  restore can be undone the same way.

### Rebuild

`crhub rebuild --compare` builds a fresh database from what is in git (imports and seeds) into `var\rebuild` and lists
every difference from your database. It never touches your database. Use it to check that git holds everything
before you move to another machine, or after a large pull.

## Where things live

- **`var`**, the hub's own folder: `region.db` (the design), `cache.db` (results that can always be rebuilt),
  `cache\blobs`, `logs` (one file per day, kept 30 days) and `backups`.
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
  stays partial until `ground/1912/STATUS.json` says `"done": true`.

## The old hub and the new hub side by side

| | Old hub | New hub |
|---|---|---|
| Start | `python hub\hub.py` | `.\crhub` |
| Address | http://127.0.0.1:8765 | http://127.0.0.1:8766 |
| Database | `hub\hub.db` | `var\region.db` |
| Into git | its Export button or `python hub\hub.py export` writes `hub/seed` | `crhub export` writes `region/seed` |
| Pages | Deck, Profiles, Station 3D, Chronology | the map, the line sheet, the inspector, jobs, the review queue |

- **Nothing in the old hub changes.** It keeps its database, its pages, its tests and its port.
- **The new hub reads the old one's design from git, never from its live database.** The `legacy:old_hub` layer is
  built from `hub/seed`. So: Export in the old hub, commit, and the new hub sees it after its next start.
- **Who owns what.** Each kind of record has an `authority` record saying which hub owns it (plan geometry stays
  with the old hub until the Deck adapter lands). While the old hub owns a kind, the new hub refuses edits to it on
  `main`, and says so. Scenarios stay editable, so you can try designs in the new hub
  without forking the truth. A kind moves to the new hub by one ruling, later.
- **The new hub's Legacy pane** links to the old hub's pages on 8765.
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
- **`.\crhub` says it found neither uv nor `.venv`.** Make the venv as in First setup.
- **Trying the new hub before `hub_region` is merged.** `git worktree add ..\cr_hub hub_region`, then run
  `.\crhub setup` inside `..\cr_hub`. Its `var` is still `%LOCALAPPDATA%\CincinnatiRail\hub` unless `configs/local.json`
  there says otherwise.
- **Logs** are in `var\logs\hub-YYYY-MM-DD.jsonl`, one JSON object per line, with the `request_id` an error toast shows.
