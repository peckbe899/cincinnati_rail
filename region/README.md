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

## First setup

PowerShell, from the repo folder:

```powershell
git pull
.\crhub setup
```

If `.\crhub setup` says it found neither uv nor `.venv`, make the venv first, then run setup:

```powershell
py -3.12 -m venv .venv
.venv\Scripts\pip install -r requirements.lock -e .
.\crhub setup
```

(`py -3.12 -m region setup`, run from the repo folder, does the same in one go: it creates `.venv` itself.)

Linux:

```sh
git pull
./crhub setup
```

`crhub setup` runs these steps and stops at the first that fails:

1. **Python packages.** With uv: `uv sync --locked --inexact` (the `--inexact` keeps any package you installed by
   hand). Without uv: `.venv\Scripts\python -m pip install -r requirements.lock -e .`.
2. **`npm ci`**: the engine's and the app's packages, from `package-lock.json`.
3. **`npm run build -w app`**: builds the web app into `app\dist`.
4. **The database.** Creates `var\region.db`, or migrates it after a checked backup into `var\backups`.
5. **The first imports** (the Metro sections, stations and profiles), once the imports command provides them.
6. **`crhub doctor`**, whose table ends the run. Setup's exit code is the doctor's.

Setup refuses to start while the new hub is serving: stop it first (Ctrl+C in its window). The old hub can keep
running. `crhub setup --dry-run` prints the steps without running anything. `--skip-npm`, `--skip-build`, `--skip-python`,
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

It refuses to create an empty database: run `crhub setup` first. It shows a banner when `app\dist` is older than the
app's source; `npm run build -w app` (or `crhub setup`) clears it. Stop it with Ctrl+C.

`crhub serve --no-browser` serves without opening a browser; `--port` serves on another port.

## Commands

| Command | What it does |
|---|---|
| `crhub setup` | installs the packages, builds the app, creates or migrates the database, runs doctor |
| `crhub` or `crhub serve` | serves the hub at http://127.0.0.1:8766 |
| `crhub doctor` | checks this machine, `var`, the ports, the data tiers, the app build and the database |
| `crhub doctor --data` | the same, and validates every record again, on a copy (slower; never changes the database) |
| `crhub model export` | before you commit: takes in pulled seeds first, then writes your design to `region/seed/main` |
| `crhub model backup` | a checked backup of the database into `var\backups` |
| `crhub model restore <file>` | puts a backup back (the current database is backed up first) |
| `crhub rebuild --compare` | rebuilds a database from git into `var\rebuild` and compares it with yours; never touches yours |
| `crhub model migrate` | applies pending migrations, backing up first (serve and setup do this for you) |
| `crhub model check` | `quick_check`, then every record validated again |
| `crhub model info` | the schema version, the layers and how many records each holds |
| `crhub info` | where this hub finds its repo, `var`, configs, tiers and features |
| `python -m region.tiers` | the data tier scan on its own (`--json` for the same as `GET /api/v1/tiers`) |

`crhub --help` lists every command, and `crhub <command> --help` its options.

### Export, then commit

Your design reaches git only through `region/seed/main`. Before you commit:

```powershell
.\crhub model export
git add region/seed
git commit -m "Hub export"
```

Export first takes in any seed changes you pulled, and refuses while one of them conflicts with a change of yours, so
it never overwrites something it has not merged. Two exports in a row give the same bytes.

### Backups and restore

- Serve and setup back up before every migration. Those backups are kept forever, as are the ones you make with
  `crhub model backup`.
- Pre-import backups keep the newest 10, daily ones 14 and weekly ones 8.
- Every backup is checked with `quick_check` before it gets its name, so a file in `var\backups` is always whole.
- To restore, stop the hub, then `.\crhub model restore var\backups\region-<time>-<reason>.db` (use the full path
  `crhub info` shows for `var`). The database you replace is backed up first, so a restore can be undone the same way.

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
| Into git | its Export button or `python hub\hub.py export` writes `hub/seed` | `crhub model export` writes `region/seed/main` |
| Pages | Deck, Profiles, Station 3D, Chronology | the map, the line sheet, the inspector, jobs, the review queue |

- **Nothing in the old hub changes.** It keeps its database, its pages, its tests and its port.
- **The new hub reads the old one's design from git, never from its live database.** The `legacy:old_hub` layer is
  built from `hub/seed`. So: Export in the old hub, commit, and the new hub sees it after its next start.
- **Who owns what.** Each kind of record has an `authority` record saying which hub owns it (plan geometry stays
  with the old hub until the Deck adapter lands). While the old hub owns a kind, the new hub refuses edits to it on
  `main`, and says so. Scenarios stay editable, so you can try designs in the new hub
  without forking the truth. A kind moves to the new hub by one ruling, later.
- **The new hub's Legacy pane** links to the old hub's pages on 8765.
- **Running both.** Start each in its own PowerShell window. Doctor shows port 8765 as information only: whether the
  old hub is running there.
- **Before you pull:** Export in the old hub and run `.\crhub model export`, so your own changes are in git too.

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
