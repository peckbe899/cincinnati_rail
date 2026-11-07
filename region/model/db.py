"""region.db: open, migrate, read and write records with versions, history, legacy keys and spatial lookups.

    from region.model import db
    con = db.open_db(path)                       # applies migrations/*.sql in order
    sid = db.put(con, "section", {...})           # new record: a ULID id, version 1
    rec = db.get(con, "section", sid)
    db.put(con, "section", {**rec, "name": "x"}, if_version=rec["version"])   # a stale if_version raises Conflict
    db.legacy(con, "deck_station", "metro:Syacmore:715445:4331182")           # -> id
    db.within(con, "section", (x0, y0, x1, y1))                               # ids whose bbox overlaps

Records are dicts; the table's columns are taken from the dict and everything else goes into `data` (JSON), so a
record round-trips whole. Geometry is a Shapely geometry under the key "geom" (stored as WKB, EPSG:26916).
"""
from __future__ import annotations

import datetime as dt
import json
import sqlite3
from pathlib import Path

from shapely import wkb
from shapely.geometry.base import BaseGeometry
from ulid import ULID

HERE = Path(__file__).resolve().parent
MIGRATIONS = HERE / "migrations"
RTREE = {"node": "node_rtree", "section": "section_rtree", "station": "station_rtree", "context_feature": "context_rtree", "earthwork": "earthwork_rtree"}
VERSIONED = ("version", "created", "updated")


class Conflict(Exception):
    """The write carried a version that is no longer current."""


class NotFound(KeyError):
    pass


def now() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def new_id() -> str:
    return str(ULID())


def open_db(path: str | Path = ":memory:") -> sqlite3.Connection:
    con = sqlite3.connect(str(path), isolation_level=None)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA journal_mode=WAL") if path != ":memory:" else None
    con.execute("PRAGMA foreign_keys=ON")
    migrate(con)
    return con


def migrate(con: sqlite3.Connection) -> list[int]:
    """Apply every migrations/NNNN_*.sql not yet applied, in order; returns the versions applied now."""
    have = con.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='schema_version'").fetchone()
    done = {r[0] for r in con.execute("SELECT version FROM schema_version")} if have else set()
    applied = []
    for f in sorted(MIGRATIONS.glob("[0-9][0-9][0-9][0-9]_*.sql")):
        v = int(f.name[:4])
        if v in done:
            continue
        con.executescript("BEGIN;\n" + f.read_text(encoding="utf-8") + "\nCOMMIT;")   # executescript ends any open transaction first
        con.execute("INSERT INTO schema_version(version, applied) VALUES (?, ?)", (v, now()))
        applied.append(v)
    return applied


def columns(con, table) -> list[str]:
    return [r[1] for r in con.execute("PRAGMA table_info(%s)" % table)]


def _split(con, table, rec):
    cols = set(columns(con, table))
    row, extra = {}, {}
    for k, v in rec.items():
        if k == "geom":
            row["geom"] = wkb.dumps(v) if isinstance(v, BaseGeometry) else v
        elif k in cols and k != "data":
            row[k] = v
        elif k != "data":
            extra[k] = v
    if "data" in cols:
        base = rec.get("data") if isinstance(rec.get("data"), dict) else (json.loads(rec["data"]) if rec.get("data") else {})
        base.update(extra)
        row["data"] = json.dumps(base, sort_keys=True, separators=(",", ":"))
    return row


def _join(con, table, row) -> dict:
    rec = dict(row)
    if rec.get("geom") is not None:
        rec["geom"] = wkb.loads(rec["geom"])
    if "data" in rec:
        d = json.loads(rec.pop("data") or "{}")
        for k, v in d.items():
            rec.setdefault(k, v)
    return rec


def _index(con, table, id_, geom):
    rt = RTREE.get(table)
    if not rt or geom is None:
        return
    g = wkb.loads(geom) if isinstance(geom, (bytes, bytearray)) else geom
    x0, y0, x1, y1 = g.bounds
    m = con.execute("SELECT rowid_ FROM rtree_map WHERE tbl=? AND id=?", (table, id_)).fetchone()
    if m:
        con.execute("UPDATE %s SET x0=?, x1=?, y0=?, y1=? WHERE rowid=?" % rt, (x0, x1, y0, y1, m[0]))
    else:
        cur = con.execute("INSERT INTO %s(x0, x1, y0, y1) VALUES (?, ?, ?, ?)" % rt, (x0, x1, y0, y1))
        con.execute("INSERT INTO rtree_map(tbl, id, rowid_) VALUES (?, ?, ?)", (table, id_, cur.lastrowid))


def get(con, table, id_) -> dict:
    r = con.execute("SELECT * FROM %s WHERE id=?" % table, (id_,)).fetchone()
    if not r:
        raise NotFound((table, id_))
    return _join(con, table, r)


def put(con, table, rec: dict, if_version: int | None = None, source: str | None = None) -> str:
    """Insert (no id, or an unknown id) or update (if_version must equal the current version). Returns the id."""
    rec = dict(rec)
    id_ = rec.get("id") or new_id()
    rec["id"] = id_
    if source is not None:
        rec["source"] = source
    cols = columns(con, table)
    con.execute("BEGIN IMMEDIATE")
    try:
        cur = con.execute("SELECT * FROM %s WHERE id=?" % table, (id_,)).fetchone()
        t = now()
        if cur is None:
            if "version" in cols:
                rec["version"], rec["created"], rec["updated"] = 1, t, t
            row = _split(con, table, rec)
            con.execute("INSERT INTO %s(%s) VALUES (%s)" % (table, ",".join(row), ",".join("?" * len(row))), list(row.values()))
        else:
            if "version" in cols:
                if if_version is None or if_version != cur["version"]:
                    raise Conflict((table, id_, cur["version"], if_version))
                old = dict(cur)
                con.execute("INSERT INTO history(tbl, id, version, updated, record) VALUES (?, ?, ?, ?, ?)",
                            (table, id_, old["version"], old["updated"], json.dumps({k: (v.hex() if isinstance(v, bytes) else v) for k, v in old.items()}, sort_keys=True)))
                rec["version"], rec["updated"], rec["created"] = cur["version"] + 1, t, cur["created"]
            row = _split(con, table, rec)
            sets = ",".join("%s=?" % k for k in row if k != "id")
            con.execute("UPDATE %s SET %s WHERE id=?" % (table, sets), [v for k, v in row.items() if k != "id"] + [id_])
        if "geom" in cols and rec.get("geom") is not None:
            _index(con, table, id_, rec["geom"] if isinstance(rec["geom"], (bytes, bytearray)) else wkb.dumps(rec["geom"]))
        con.execute("COMMIT")
    except Exception:
        con.execute("ROLLBACK")
        raise
    return id_


def history(con, table, id_) -> list[dict]:
    return [dict(version=r["version"], updated=r["updated"], record=json.loads(r["record"])) for r in
            con.execute("SELECT version, updated, record FROM history WHERE tbl=? AND id=? ORDER BY version", (table, id_))]


def add_legacy(con, kind: str, legacy: str, table: str, id_: str, note: str | None = None):
    con.execute("INSERT OR REPLACE INTO legacy_key(legacy, kind, tbl, id, note) VALUES (?, ?, ?, ?, ?)", (legacy, kind, table, id_, note))


def legacy(con, kind: str, key: str) -> str | None:
    r = con.execute("SELECT id FROM legacy_key WHERE kind=? AND legacy=?", (kind, key)).fetchone()
    return r[0] if r else None


def within(con, table, bbox) -> list[str]:
    """Ids of records whose bounding box overlaps bbox (x0, y0, x1, y1)."""
    rt = RTREE[table]
    x0, y0, x1, y1 = bbox
    rows = con.execute("SELECT m.id FROM %s r JOIN rtree_map m ON m.rowid_ = r.rowid AND m.tbl = ? WHERE r.x1 >= ? AND r.x0 <= ? AND r.y1 >= ? AND r.y0 <= ?" % rt,
                       (table, x0, x1, y0, y1))
    return [r[0] for r in rows]


def rows(con, table, where: str = "", params=()) -> list[dict]:
    return [_join(con, table, r) for r in con.execute("SELECT * FROM %s %s" % (table, ("WHERE " + where) if where else ""), params)]


def tables(con) -> list[str]:
    return [r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE '%rtree%' AND name NOT IN ('schema_version','history','rtree_map','result','issue') ORDER BY name")]
