-- region.db, migration 0002: one record store (decisions 9.9 to 9.13, 9.17, 9.18, 9.28, 9.29; section 4).
--
-- 0002_store.py runs first in the same transaction and refuses to go on unless every 0001 table is empty; this
-- script then drops them. Enums (tiers, origins, reasons, states) are checked in Python against
-- region/kinds/_vocab.yaml, not by SQL CHECKs, so adding a value needs no table rebuild.
--
-- Changes from the layout in section 4 of the architecture:
--   rec.geom is TEXT: the canonical WKT of the get() shape (snapped to 1 mm), so reads convert nothing.
--   changeset.seq is the seq of the changeset's own event, which dates its revisions for tags (as-of reads).
--   event.data is the event's payload as sent (region.core.events), so replay never rebuilds it.

DROP TABLE IF EXISTS node;
DROP TABLE IF EXISTS section;
DROP TABLE IF EXISTS track;
DROP TABLE IF EXISTS route;
DROP TABLE IF EXISTS route_section;
DROP TABLE IF EXISTS service;
DROP TABLE IF EXISTS station;
DROP TABLE IF EXISTS stop;
DROP TABLE IF EXISTS platform;
DROP TABLE IF EXISTS station_element;
DROP TABLE IF EXISTS structure;
DROP TABLE IF EXISTS bridge;
DROP TABLE IF EXISTS earthwork;
DROP TABLE IF EXISTS ground_layer;
DROP TABLE IF EXISTS context_feature;
DROP TABLE IF EXISTS yard;
DROP TABLE IF EXISTS era;
DROP TABLE IF EXISTS rule;
DROP TABLE IF EXISTS ruling;
DROP TABLE IF EXISTS snapshot;
DROP TABLE IF EXISTS issue;
DROP TABLE IF EXISTS result;
DROP TABLE IF EXISTS legacy_key;
DROP TABLE IF EXISTS history;
DROP TABLE IF EXISTS node_rtree;
DROP TABLE IF EXISTS section_rtree;
DROP TABLE IF EXISTS station_rtree;
DROP TABLE IF EXISTS context_rtree;
DROP TABLE IF EXISTS earthwork_rtree;
DROP TABLE IF EXISTS rtree_map;

-- db_id, epoch (new on every restore), created, last_export, kinds_sha256
CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);

-- the kinds the store was last opened with (name, kind version, feature folder, geometry, file sha256, parsed file)
CREATE TABLE kind (name TEXT PRIMARY KEY, version INT NOT NULL, feature TEXT, geometry TEXT, sha256 TEXT, spec TEXT);

-- tier: import | legacy | main | scenario | proposal; state: open | promoted | archived
CREATE TABLE layer (id INTEGER PRIMARY KEY, slug TEXT UNIQUE NOT NULL, tier TEXT NOT NULL,
  parent INT REFERENCES layer(id), namespace TEXT, state TEXT DEFAULT 'open', title TEXT, note TEXT, created TEXT,
  by TEXT);

-- one row per (layer, id): the current revision on that layer. Promoted columns are derived from data by the kind's
-- column map; open_lo .. close_hi are month intervals (months since year 0, NULL = undated); x0 .. y1 the bbox.
CREATE TABLE rec (rid INTEGER PRIMARY KEY, layer INT NOT NULL REFERENCES layer(id), id TEXT NOT NULL,
  kind TEXT NOT NULL, kv INT NOT NULL, version INT NOT NULL, hash TEXT NOT NULL, base_hash TEXT,
  deleted INT NOT NULL DEFAULT 0, origin TEXT NOT NULL, source TEXT, by TEXT NOT NULL, changeset TEXT NOT NULL,
  import_run INT, created TEXT, updated TEXT,
  name TEXT, system TEXT, parent TEXT, c0 REAL, c1 REAL, ord TEXT, phase TEXT,
  open_lo INT, open_hi INT, close_lo INT, close_hi INT,
  x0 REAL, y0 REAL, x1 REAL, y1 REAL, geom TEXT, data TEXT NOT NULL, UNIQUE (layer, id));
CREATE INDEX rec_id ON rec(id);
CREATE INDEX rec_kind ON rec(kind, layer);
CREATE INDEX rec_kind_id ON rec(kind, id, layer);
CREATE INDEX rec_parent ON rec(parent, c0);
CREATE INDEX rec_name ON rec(kind, name);

CREATE VIRTUAL TABLE rec_rtree USING rtree(rid, x0, x1, y0, y1, +layer, +kind);

-- The R-tree follows every change to rec, raw SQL included (defect 8 of the old store).
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
CREATE TRIGGER rec_rtree_delete AFTER DELETE ON rec
BEGIN
  DELETE FROM rec_rtree WHERE rid = old.rid;
END;

-- Versions step by exactly one, and content never changes without a new version, whoever writes.
CREATE TRIGGER rec_version_steps BEFORE UPDATE OF version ON rec WHEN new.version IS NOT old.version + 1
BEGIN
  SELECT RAISE(ABORT, 'rec.version must step by one');
END;
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

-- every version of every revision, the current one included; row is the record in get() shape (defect 7)
CREATE TABLE rec_hist (layer INT, id TEXT, version INT, hash TEXT, changeset TEXT, at TEXT, by TEXT,
  row TEXT NOT NULL, PRIMARY KEY (layer, id, version));
CREATE INDEX rec_hist_changeset ON rec_hist(changeset);

-- the refs of each current revision (src is the referring record, dst the record referred to)
CREATE TABLE ref (layer INT, src TEXT, role TEXT, dst TEXT, PRIMARY KEY (layer, src, role, dst));
CREATE INDEX ref_dst ON ref(dst);

-- old keys to ids (status: current | alias)
CREATE TABLE legacy (lkind TEXT, key TEXT, id TEXT NOT NULL, status TEXT DEFAULT 'current',
  PRIMARY KEY (lkind, key));
CREATE INDEX legacy_id ON legacy(id);

-- kind: edit | import | seed | revert | rebase | promote | migration | legacy
CREATE TABLE changeset (id TEXT PRIMARY KEY, layer INT, by TEXT, client TEXT, message TEXT, kind TEXT,
  reverts TEXT, created TEXT, count INT, seq INT);
CREATE INDEX changeset_layer ON changeset(layer, seq);

-- the outbox: durable record and changeset events, written in the same transaction as the change
CREATE TABLE event (seq INTEGER PRIMARY KEY AUTOINCREMENT, at TEXT, type TEXT, layer INT, kind TEXT, id TEXT,
  version INT, hash TEXT, op TEXT, changeset TEXT, by TEXT, client TEXT, fields TEXT, bbox TEXT, data TEXT);

-- reason: both_changed | geometry_under_edit | orphan | dangling_ref | invalid | namespace | authority_divergence
-- state: open | resolved | dismissed
CREATE TABLE conflict (id TEXT PRIMARY KEY, layer INT, rec_id TEXT, kind TEXT, reason TEXT,
  ours_hash TEXT, theirs_hash TEXT, base_hash TEXT, proposed TEXT, fields TEXT, state TEXT DEFAULT 'open',
  import_run INT, created TEXT, resolved_by TEXT, resolution TEXT);
CREATE INDEX conflict_open ON conflict(state, layer, rec_id);

CREATE TABLE import_run (id INTEGER PRIMARY KEY, importer TEXT, version TEXT, layer INT, sources TEXT,
  dry_run INT, state TEXT, counts TEXT, report TEXT, changeset TEXT, started TEXT, finished TEXT);

-- a named version of a layer: the layer as of event seq
CREATE TABLE tag (layer INT, name TEXT, seq INT NOT NULL, note TEXT, created TEXT, by TEXT,
  PRIMARY KEY (layer, name));

-- the hash of each seeded record as last exported or imported, the base of the seed's three-way merge
CREATE TABLE seed_base (layer INT, id TEXT, hash TEXT NOT NULL, PRIMARY KEY (layer, id));
