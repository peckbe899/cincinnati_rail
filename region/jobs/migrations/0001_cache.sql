-- cache.db, schema 1 (decision 9.18; section 4, "cache.db"). region/jobs/cache.py applies it in one transaction
-- together with its schema_version row. Everything here can be rebuilt: delete the cache folder and the hub recomputes.
-- Table names are unqualified, so the file applies to cache.db opened on its own; attach it afterwards as "cache".

CREATE TABLE schema_version (version INTEGER PRIMARY KEY, applied TEXT NOT NULL);

-- One row per piece of work. state: queued | running | done | failed | cancelled. A queued job whose plan still
-- needs an upstream result has key NULL and lists the upstream refs in waiting (JSON). lease_owner is the scheduler
-- instance running it; lease_until is extended by its heartbeat; an expired lease is re-queued at most max_requeue times.
CREATE TABLE job (
  id TEXT PRIMARY KEY,
  type TEXT NOT NULL,
  scope TEXT NOT NULL,
  view TEXT NOT NULL,
  key TEXT,
  state TEXT NOT NULL,
  priority INTEGER NOT NULL,
  host TEXT NOT NULL,
  reason TEXT,
  waiting TEXT,
  progress REAL NOT NULL DEFAULT 0,
  msg TEXT NOT NULL DEFAULT '',
  error TEXT,
  requeues INTEGER NOT NULL DEFAULT 0,
  lease_owner TEXT,
  lease_until REAL,
  heartbeat REAL,
  pid INTEGER,
  created TEXT NOT NULL,
  started TEXT,
  finished TEXT
);
-- one active job per (type, key): two views with the same content share the work
CREATE UNIQUE INDEX job_active_key ON job(type, key) WHERE state IN ('queued', 'running') AND key IS NOT NULL;
CREATE INDEX job_state ON job(state, priority, id);
CREATE INDEX job_goal ON job(type, scope, view, state);

CREATE TABLE job_log (
  seq INTEGER PRIMARY KEY AUTOINCREMENT,
  job TEXT NOT NULL,
  at TEXT NOT NULL,
  level TEXT NOT NULL,
  msg TEXT NOT NULL
);
CREATE INDEX job_log_job ON job_log(job, seq);

-- One row per key. status: ok | error | stale. arrays: {name: {sha256, dtype, shape, size}}; blobs: {name: {sha256, size}}.
-- Only ok rows are cache hits. last_used is Unix seconds, for LRU eviction.
CREATE TABLE result (
  key TEXT PRIMARY KEY,
  type TEXT NOT NULL,
  scope TEXT NOT NULL,
  view TEXT NOT NULL,
  status TEXT NOT NULL,
  output_hash TEXT,
  meta TEXT NOT NULL DEFAULT '{}',
  arrays TEXT NOT NULL DEFAULT '{}',
  blobs TEXT NOT NULL DEFAULT '{}',
  error TEXT,
  engine_build TEXT,
  job TEXT,
  ms REAL,
  created TEXT NOT NULL,
  last_used REAL NOT NULL,
  pinned INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX result_goal ON result(type, scope, view);
CREATE INDEX result_lru ON result(last_used);

-- Exactly the plan's reads (9.19). kind is the record kind of a rec: ref, so a bulk changeset (one summary event
-- that names kinds, not ids) still finds its dependants.
CREATE TABLE result_dep (
  key TEXT NOT NULL,
  ref TEXT NOT NULL,
  ref_hash TEXT,
  kind TEXT,
  PRIMARY KEY (key, ref)
);
CREATE INDEX result_dep_ref ON result_dep(ref);
CREATE INDEX result_dep_kind ON result_dep(kind);

-- Which blobs a result holds, so eviction can delete a blob no result still needs.
CREATE TABLE result_blob (
  key TEXT NOT NULL,
  sha256 TEXT NOT NULL,
  PRIMARY KEY (key, sha256)
);
CREATE INDEX result_blob_sha ON result_blob(sha256);

-- What to keep fresh. watch 1: re-planned whenever a dependency changes (until expires, Unix seconds). A submit
-- makes a row with watch 0, so result(type, scope, view) can answer. want_key is the key last planned, latest_key
-- the key of the newest committed ok result. pinned goals are spared by eviction. auto marks an upstream goal
-- registered by a downstream goal's need().
CREATE TABLE goal (
  type TEXT NOT NULL,
  scope TEXT NOT NULL,
  view TEXT NOT NULL,
  priority INTEGER NOT NULL,
  watch INTEGER NOT NULL DEFAULT 0,
  expires REAL,
  pinned INTEGER NOT NULL DEFAULT 0,
  auto INTEGER NOT NULL DEFAULT 0,
  want_key TEXT,
  latest_key TEXT,
  state TEXT,
  error TEXT,
  created TEXT NOT NULL,
  updated TEXT NOT NULL,
  PRIMARY KEY (type, scope, view)
);
CREATE INDEX goal_want ON goal(want_key);
CREATE INDEX goal_latest ON goal(latest_key);

-- Check findings of a result, one row per distinct finding.
CREATE TABLE issue (
  key TEXT NOT NULL,
  rule TEXT,
  sev TEXT,
  c0 REAL,
  c1 REAL,
  msg TEXT,
  data TEXT,
  dedupe TEXT NOT NULL,
  UNIQUE (key, dedupe)
);

-- Content-addressed files under the blobs folder (<sha256[:2]>/<sha256>). A row is written only after its file.
CREATE TABLE blob (
  sha256 TEXT PRIMARY KEY,
  size INTEGER NOT NULL,
  created TEXT NOT NULL,
  last_used REAL NOT NULL
);

-- sha256 of input files, reused while size and mtime_ns are unchanged.
CREATE TABLE file_hash (
  path TEXT PRIMARY KEY,
  size INTEGER NOT NULL,
  mtime_ns INTEGER NOT NULL,
  sha256 TEXT NOT NULL,
  checked TEXT NOT NULL
);

-- How far a reader has followed the truth DB's outbox ("invalidator").
CREATE TABLE cursor (
  name TEXT PRIMARY KEY,
  seq INTEGER NOT NULL,
  updated TEXT NOT NULL
);
