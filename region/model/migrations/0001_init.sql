-- region.db, migration 0001: the model's tables (roadmap section 2.3; checklist 2.0.7, 2.0.8).
--
-- Conventions, every table:
--   id        TEXT PRIMARY KEY, a ULID, never reused or renamed (a replaced record is superseded, not re-keyed)
--   version   INTEGER, +1 on every write; writes carry the version they built on (If-Match) and a stale one is refused
--   created, updated   ISO-8601 UTC
--   source    TEXT, where the record came from (file, chat, ruling id, import run)
--   phase, year_open, year_close   when it is something built (NULL where it is not)
--   geom      BLOB, WKB in EPSG:26916 metres, where the record has a geometry
--   data      TEXT, JSON with the record's other fields (the schema is thin on purpose: columns are what we query by,
--             data holds the rest, validated by the importers and the contract schemas)
-- Geometry tables have an R-tree (SQLite rtree module) kept in step by triggers.

CREATE TABLE schema_version (version INTEGER NOT NULL, applied TEXT NOT NULL);

-- the network graph ------------------------------------------------------------------------------------------
CREATE TABLE node (
  id TEXT PRIMARY KEY, version INTEGER NOT NULL DEFAULT 1, created TEXT NOT NULL, updated TEXT NOT NULL, source TEXT,
  kind TEXT NOT NULL,                -- junction | line_end | stop | seam
  name TEXT, system TEXT,            -- metro | tri | apex | orr | tv | other
  level_m REAL,                      -- one rail level shared by every section through the node (NULL = free)
  phase TEXT, year_open INTEGER, year_close INTEGER,
  geom BLOB NOT NULL, data TEXT NOT NULL DEFAULT '{}');

CREATE TABLE section (
  id TEXT PRIMARY KEY, version INTEGER NOT NULL DEFAULT 1, created TEXT NOT NULL, updated TEXT NOT NULL, source TEXT,
  name TEXT, system TEXT NOT NULL,
  node_a TEXT NOT NULL REFERENCES node(id), node_b TEXT NOT NULL REFERENCES node(id),
  length_m REAL NOT NULL,            -- ground distance along the plan geometry, chainage runs node_a -> node_b
  tracks INTEGER NOT NULL DEFAULT 2, spacing_m REAL,
  phase TEXT, year_open INTEGER, year_close INTEGER,
  geom BLOB NOT NULL,                -- plan polyline; fitted elements (tangent, curve, spiral) live in data.plan
  data TEXT NOT NULL DEFAULT '{}');  -- vertical controls by offset (st, pvi, sg, so, locks, gnd), paints (ovr, tf, shafts), mode, ready

CREATE TABLE track (                 -- a track within a section, for shared trunks and throats
  id TEXT PRIMARY KEY, version INTEGER NOT NULL DEFAULT 1, created TEXT NOT NULL, updated TEXT NOT NULL, source TEXT,
  section_id TEXT NOT NULL REFERENCES section(id), position INTEGER NOT NULL, name TEXT, offset_m REAL NOT NULL DEFAULT 0,
  phase TEXT, year_open INTEGER, year_close INTEGER, data TEXT NOT NULL DEFAULT '{}');

CREATE TABLE route (                 -- an ordered list of sections with directions: a Metro line, a TRI trunk or branch
  id TEXT PRIMARY KEY, version INTEGER NOT NULL DEFAULT 1, created TEXT NOT NULL, updated TEXT NOT NULL, source TEXT,
  name TEXT NOT NULL, system TEXT NOT NULL, short TEXT, colour TEXT,
  phase TEXT, year_open INTEGER, year_close INTEGER, data TEXT NOT NULL DEFAULT '{}');

CREATE TABLE route_section (
  route_id TEXT NOT NULL REFERENCES route(id), position INTEGER NOT NULL,
  section_id TEXT NOT NULL REFERENCES section(id), direction INTEGER NOT NULL DEFAULT 1,   -- +1 a->b, -1 b->a
  PRIMARY KEY (route_id, position));

CREATE TABLE service (               -- a route pair through the trunk, pattern, mission, headways, era, fleet
  id TEXT PRIMARY KEY, version INTEGER NOT NULL DEFAULT 1, created TEXT NOT NULL, updated TEXT NOT NULL, source TEXT,
  name TEXT NOT NULL, system TEXT NOT NULL, mission TEXT, era_id TEXT,
  phase TEXT, year_open INTEGER, year_close INTEGER, data TEXT NOT NULL DEFAULT '{}');

-- stations ----------------------------------------------------------------------------------------------------
CREATE TABLE station (               -- the complex
  id TEXT PRIMARY KEY, version INTEGER NOT NULL DEFAULT 1, created TEXT NOT NULL, updated TEXT NOT NULL, source TEXT,
  name TEXT NOT NULL, system TEXT,
  phase TEXT, year_open INTEGER, year_close INTEGER,
  geom BLOB NOT NULL, data TEXT NOT NULL DEFAULT '{}');

CREATE TABLE stop (                  -- a station's stop on one route, at an offset on a section
  id TEXT PRIMARY KEY, version INTEGER NOT NULL DEFAULT 1, created TEXT NOT NULL, updated TEXT NOT NULL, source TEXT,
  station_id TEXT NOT NULL REFERENCES station(id), route_id TEXT NOT NULL REFERENCES route(id),
  section_id TEXT NOT NULL REFERENCES section(id), offset_m REAL NOT NULL,
  name TEXT, phase TEXT, year_open INTEGER, year_close INTEGER, data TEXT NOT NULL DEFAULT '{}');

CREATE TABLE platform (
  id TEXT PRIMARY KEY, version INTEGER NOT NULL DEFAULT 1, created TEXT NOT NULL, updated TEXT NOT NULL, source TEXT,
  stop_id TEXT NOT NULL REFERENCES stop(id),
  kind TEXT NOT NULL,                -- island | side
  length_m REAL NOT NULL, width_m REAL, slide_m REAL NOT NULL DEFAULT 0, grade_permille REAL NOT NULL DEFAULT 0,
  level_m REAL, selection TEXT,      -- Ben's structure selection (stt), NULL = by the rules
  gapfill INTEGER NOT NULL DEFAULT 0, deleted INTEGER NOT NULL DEFAULT 0,
  phase TEXT, year_open INTEGER, year_close INTEGER, geom BLOB, data TEXT NOT NULL DEFAULT '{}');

CREATE TABLE station_element (       -- hall, passage, flight, lift, gate, entrance
  id TEXT PRIMARY KEY, version INTEGER NOT NULL DEFAULT 1, created TEXT NOT NULL, updated TEXT NOT NULL, source TEXT,
  station_id TEXT NOT NULL REFERENCES station(id), kind TEXT NOT NULL, name TEXT,
  level_m REAL, level_to_m REAL, width_m REAL,
  phase TEXT, year_open INTEGER, year_close INTEGER, geom BLOB, data TEXT NOT NULL DEFAULT '{}');

-- structures, bridges, earthworks, ground, context ------------------------------------------------------------
CREATE TABLE structure (             -- a range on a section with method and form; origin says whether solved or set
  id TEXT PRIMARY KEY, version INTEGER NOT NULL DEFAULT 1, created TEXT NOT NULL, updated TEXT NOT NULL, source TEXT,
  section_id TEXT NOT NULL REFERENCES section(id), c0_m REAL NOT NULL, c1_m REAL NOT NULL,
  method TEXT NOT NULL,              -- box | twin | bore | trough | atgrade | embankment | viaduct | bridge | ramp | mined_station
  form TEXT, origin TEXT NOT NULL,   -- origin: solved | paint | selection | canon | ruling
  rule_ids TEXT,                     -- JSON list of registry ids the solver applied
  phase TEXT, year_open INTEGER, year_close INTEGER, data TEXT NOT NULL DEFAULT '{}');

CREATE TABLE bridge (                -- a river or valley crossing as a parametric object
  id TEXT PRIMARY KEY, version INTEGER NOT NULL DEFAULT 1, created TEXT NOT NULL, updated TEXT NOT NULL, source TEXT,
  name TEXT NOT NULL, kind TEXT, rail_m REAL, span_m REAL,
  phase TEXT, year_open INTEGER, year_close INTEGER, geom BLOB NOT NULL, data TEXT NOT NULL DEFAULT '{}');

CREATE TABLE earthwork (             -- a pad, corridor or freeform work, or a raster layer from ground/
  id TEXT PRIMARY KEY, version INTEGER NOT NULL DEFAULT 1, created TEXT NOT NULL, updated TEXT NOT NULL, source TEXT,
  name TEXT NOT NULL, kind TEXT NOT NULL,          -- pad | corridor | freeform | raster
  timeline TEXT NOT NULL DEFAULT 'canon',          -- canon | real | both
  mode TEXT NOT NULL DEFAULT 'replace',            -- replace | fill | cut
  phase TEXT, year_open INTEGER, year_close INTEGER, geom BLOB, data TEXT NOT NULL DEFAULT '{}');

CREATE TABLE ground_layer (          -- base surfaces by era and tier
  id TEXT PRIMARY KEY, version INTEGER NOT NULL DEFAULT 1, created TEXT NOT NULL, updated TEXT NOT NULL, source TEXT,
  name TEXT NOT NULL, tier TEXT NOT NULL,          -- core | corridor | region | survey
  year INTEGER, path TEXT NOT NULL, sha256 TEXT, geom BLOB, data TEXT NOT NULL DEFAULT '{}');

CREATE TABLE context_feature (       -- other systems' tracks and structures, roads, rivers, Deck streets/blocks/plots by reference
  id TEXT PRIMARY KEY, version INTEGER NOT NULL DEFAULT 1, created TEXT NOT NULL, updated TEXT NOT NULL, source TEXT,
  kind TEXT NOT NULL, system TEXT, name TEXT, class TEXT, level_m REAL,
  phase TEXT, year_open INTEGER, year_close INTEGER, geom BLOB NOT NULL, data TEXT NOT NULL DEFAULT '{}');

CREATE TABLE yard (
  id TEXT PRIMARY KEY, version INTEGER NOT NULL DEFAULT 1, created TEXT NOT NULL, updated TEXT NOT NULL, source TEXT,
  name TEXT NOT NULL, system TEXT, role TEXT,
  phase TEXT, year_open INTEGER, year_close INTEGER, geom BLOB NOT NULL, data TEXT NOT NULL DEFAULT '{}');

-- eras, rules, rulings, versions, results, issues --------------------------------------------------------------
CREATE TABLE era (
  id TEXT PRIMARY KEY, version INTEGER NOT NULL DEFAULT 1, created TEXT NOT NULL, updated TEXT NOT NULL, source TEXT,
  name TEXT NOT NULL, system TEXT, year_from INTEGER NOT NULL, year_to INTEGER, data TEXT NOT NULL DEFAULT '{}');

CREATE TABLE rule (                  -- mirrors rules/registry.yaml (the YAML is the seed and the editable form)
  id TEXT PRIMARY KEY, domain TEXT NOT NULL, status TEXT NOT NULL, decision TEXT, rank INTEGER, text TEXT NOT NULL,
  data TEXT NOT NULL DEFAULT '{}');

CREATE TABLE ruling (                -- a dated decision by Ben and what it governs
  id TEXT PRIMARY KEY, version INTEGER NOT NULL DEFAULT 1, created TEXT NOT NULL, updated TEXT NOT NULL, source TEXT,
  date TEXT NOT NULL, by_whom TEXT NOT NULL DEFAULT 'Ben', words TEXT, governs TEXT NOT NULL DEFAULT '[]', data TEXT NOT NULL DEFAULT '{}');

CREATE TABLE snapshot (              -- a named version: the input records of a route, station or service plan
  id TEXT PRIMARY KEY, version INTEGER NOT NULL DEFAULT 1, created TEXT NOT NULL, updated TEXT NOT NULL, source TEXT,
  name TEXT NOT NULL, scope_kind TEXT NOT NULL, scope_id TEXT NOT NULL, note TEXT, records TEXT NOT NULL);   -- records: JSON {table: {id: record}}

CREATE TABLE result (                -- derived, cached by input hash and engine version; never truth
  key TEXT PRIMARY KEY,              -- sha256 of (engine, engine_version, inputs)
  engine TEXT NOT NULL, engine_version TEXT NOT NULL, scope_kind TEXT, scope_id TEXT,
  created TEXT NOT NULL, ms INTEGER, output TEXT NOT NULL);

CREATE TABLE issue (                 -- a check failure with its rule and place
  id TEXT PRIMARY KEY, created TEXT NOT NULL, result_key TEXT REFERENCES result(key),
  rule_id TEXT NOT NULL, severity TEXT NOT NULL,   -- error | warning | info
  scope_kind TEXT, scope_id TEXT, c0_m REAL, c1_m REAL, message TEXT NOT NULL, data TEXT NOT NULL DEFAULT '{}');

-- keys, history ----------------------------------------------------------------------------------------------
CREATE TABLE legacy_key (            -- every old key (Deck station keys, profile station keys, chronology keys, street ids) -> id
  legacy TEXT NOT NULL, kind TEXT NOT NULL, tbl TEXT NOT NULL, id TEXT NOT NULL, note TEXT,
  PRIMARY KEY (kind, legacy));
CREATE INDEX legacy_key_id ON legacy_key(id);

CREATE TABLE history (               -- every previous version of every record, compacted later, never silently dropped
  tbl TEXT NOT NULL, id TEXT NOT NULL, version INTEGER NOT NULL, updated TEXT NOT NULL, record TEXT NOT NULL,
  PRIMARY KEY (tbl, id, version));

-- spatial indexes ---------------------------------------------------------------------------------------------
CREATE VIRTUAL TABLE node_rtree USING rtree(rowid, x0, x1, y0, y1);
CREATE VIRTUAL TABLE section_rtree USING rtree(rowid, x0, x1, y0, y1);
CREATE VIRTUAL TABLE station_rtree USING rtree(rowid, x0, x1, y0, y1);
CREATE VIRTUAL TABLE context_rtree USING rtree(rowid, x0, x1, y0, y1);
CREATE VIRTUAL TABLE earthwork_rtree USING rtree(rowid, x0, x1, y0, y1);
CREATE TABLE rtree_map (tbl TEXT NOT NULL, id TEXT NOT NULL, rowid_ INTEGER NOT NULL, PRIMARY KEY (tbl, id));

CREATE INDEX section_nodes ON section(node_a, node_b);
CREATE INDEX stop_station ON stop(station_id);
CREATE INDEX stop_section ON stop(section_id);
CREATE INDEX platform_stop ON platform(stop_id);
CREATE INDEX structure_section ON structure(section_id, c0_m);
CREATE INDEX element_station ON station_element(station_id);
CREATE INDEX issue_scope ON issue(scope_kind, scope_id);
CREATE INDEX result_scope ON result(scope_kind, scope_id);
