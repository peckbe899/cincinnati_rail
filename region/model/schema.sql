-- region.db schema after every migration (generated: python -m region.model schema --write)

CREATE TABLE changeset (id TEXT PRIMARY KEY, layer INT, by TEXT, client TEXT, message TEXT, kind TEXT,
  reverts TEXT, created TEXT, count INT, seq INT);

CREATE TABLE conflict (id TEXT PRIMARY KEY, layer INT, rec_id TEXT, kind TEXT, reason TEXT,
  ours_hash TEXT, theirs_hash TEXT, base_hash TEXT, proposed TEXT, fields TEXT, state TEXT DEFAULT 'open',
  import_run INT, created TEXT, resolved_by TEXT, resolution TEXT);

CREATE TABLE event (seq INTEGER PRIMARY KEY AUTOINCREMENT, at TEXT, type TEXT, layer INT, kind TEXT, id TEXT,
  version INT, hash TEXT, op TEXT, changeset TEXT, by TEXT, client TEXT, fields TEXT, bbox TEXT, data TEXT);

CREATE TABLE import_run (id INTEGER PRIMARY KEY, importer TEXT, version TEXT, layer INT, sources TEXT,
  dry_run INT, state TEXT, counts TEXT, report TEXT, changeset TEXT, started TEXT, finished TEXT);

CREATE TABLE kind (name TEXT PRIMARY KEY, version INT NOT NULL, feature TEXT, geometry TEXT, sha256 TEXT, spec TEXT);

CREATE TABLE layer (id INTEGER PRIMARY KEY, slug TEXT UNIQUE NOT NULL, tier TEXT NOT NULL,
  parent INT REFERENCES layer(id), namespace TEXT, state TEXT DEFAULT 'open', title TEXT, note TEXT, created TEXT,
  by TEXT);

CREATE TABLE legacy (lkind TEXT, key TEXT, id TEXT NOT NULL, status TEXT DEFAULT 'current',
  PRIMARY KEY (lkind, key));

CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);

CREATE TABLE rec (rid INTEGER PRIMARY KEY, layer INT NOT NULL REFERENCES layer(id), id TEXT NOT NULL,
  kind TEXT NOT NULL, kv INT NOT NULL, version INT NOT NULL, hash TEXT NOT NULL, base_hash TEXT,
  deleted INT NOT NULL DEFAULT 0, origin TEXT NOT NULL, source TEXT, by TEXT NOT NULL, changeset TEXT NOT NULL,
  import_run INT, created TEXT, updated TEXT,
  name TEXT, system TEXT, parent TEXT, c0 REAL, c1 REAL, ord TEXT, phase TEXT,
  open_lo INT, open_hi INT, close_lo INT, close_hi INT,
  x0 REAL, y0 REAL, x1 REAL, y1 REAL, geom TEXT, data TEXT NOT NULL, UNIQUE (layer, id));

CREATE TABLE rec_hist (layer INT, id TEXT, version INT, hash TEXT, changeset TEXT, at TEXT, by TEXT,
  row TEXT NOT NULL, PRIMARY KEY (layer, id, version));

CREATE VIRTUAL TABLE rec_rtree USING rtree(rid, x0, x1, y0, y1, +layer, +kind);

CREATE TABLE ref (layer INT, src TEXT, role TEXT, dst TEXT, PRIMARY KEY (layer, src, role, dst));

CREATE TABLE schema_version (version INTEGER NOT NULL, applied TEXT NOT NULL);

CREATE TABLE seed_base (layer INT, id TEXT, hash TEXT NOT NULL, PRIMARY KEY (layer, id));

CREATE TABLE tag (layer INT, name TEXT, seq INT NOT NULL, note TEXT, created TEXT, by TEXT,
  PRIMARY KEY (layer, name));

CREATE INDEX changeset_layer ON changeset(layer, seq);

CREATE INDEX conflict_open ON conflict(state, layer, rec_id);

CREATE INDEX legacy_id ON legacy(id);

CREATE INDEX rec_hist_changeset ON rec_hist(changeset);

CREATE INDEX rec_id ON rec(id);

CREATE INDEX rec_kind ON rec(kind, layer);

CREATE INDEX rec_kind_id ON rec(kind, id, layer);

CREATE INDEX rec_name ON rec(kind, name);

CREATE INDEX rec_parent ON rec(parent, c0);

CREATE INDEX ref_dst ON ref(dst);

CREATE TRIGGER rec_content_needs_version BEFORE UPDATE OF kv, hash, deleted, geom, data ON rec
  WHEN new.version IS old.version
BEGIN
  SELECT RAISE(ABORT, 'a change to a record needs a new version');
END;

CREATE TRIGGER rec_identity_fixed BEFORE UPDATE OF id, kind, layer ON rec
  WHEN new.id IS NOT old.id OR new.kind IS NOT old.kind OR new.layer IS NOT old.layer
BEGIN
  SELECT RAISE(ABORT, 'a record keeps its id, kind and layer');
END;

CREATE TRIGGER rec_rtree_delete AFTER DELETE ON rec
BEGIN
  DELETE FROM rec_rtree WHERE rid = old.rid;
END;

CREATE TRIGGER rec_rtree_insert AFTER INSERT ON rec WHEN new.x0 IS NOT NULL
BEGIN
  INSERT INTO rec_rtree (rid, x0, x1, y0, y1, layer, kind) VALUES (new.rid, new.x0, new.x1, new.y0, new.y1,
    new.layer, new.kind);
END;

CREATE TRIGGER rec_rtree_update AFTER UPDATE OF x0, y0, x1, y1 ON rec
BEGIN
  DELETE FROM rec_rtree WHERE rid = old.rid;
  INSERT INTO rec_rtree (rid, x0, x1, y0, y1, layer, kind)
    SELECT new.rid, new.x0, new.x1, new.y0, new.y1, new.layer, new.kind WHERE new.x0 IS NOT NULL;
END;

CREATE TRIGGER rec_version_steps BEFORE UPDATE OF version ON rec WHEN new.version IS NOT old.version + 1
BEGIN
  SELECT RAISE(ABORT, 'rec.version must step by one');
END;
