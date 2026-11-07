"""Seeds: the model in git, one JSON file per record, sorted keys, geometry as WKT; derived tables never exported.

    python -m region.model export  [--db region.db] [--out region/seed]
    python -m region.model import  [--db region.db] [--seed region/seed]     # three-way merge against seed_base

Merge rule on import, per record: unchanged here and changed in the seed -> take the seed; changed here and unchanged
in the seed -> keep ours; changed on both -> keep ours and list it in the conflicts file (region/seed_conflicts/);
new in the seed -> add; gone from the seed -> keep ours and list it. The base for "changed" is the seed as last
exported or imported here (table seed_base). Ben's database is never overwritten.
"""
from __future__ import annotations

import json
from pathlib import Path

from shapely import wkt

from . import db as D

ROOT = Path(__file__).resolve().parents[2]
SEED = ROOT / "region" / "seed"
DERIVED = {"result", "issue", "history", "rtree_map", "schema_version"}


def _to_json(rec: dict) -> str:
    r = dict(rec)
    if r.get("geom") is not None:
        r["geom"] = wkt.dumps(r["geom"], rounding_precision=3)
    return json.dumps(r, sort_keys=True, indent=1, ensure_ascii=False) + "\n"


def _from_json(text: str) -> dict:
    r = json.loads(text)
    if r.get("geom"):
        r["geom"] = wkt.loads(r["geom"])
    return r


def _ensure_base(con):
    con.execute("CREATE TABLE IF NOT EXISTS seed_base (tbl TEXT NOT NULL, id TEXT NOT NULL, record TEXT NOT NULL, PRIMARY KEY (tbl, id))")


def export(con, out: Path = SEED) -> int:
    _ensure_base(con)
    n = 0
    for t in D.tables(con):
        if t in DERIVED or t == "seed_base":
            continue
        d = out / t; d.mkdir(parents=True, exist_ok=True)
        keep = set()
        for rec in D.rows(con, t):
            s = _to_json(rec)
            (d / f"{rec.get('id') or rec.get('legacy')}.json").write_text(s, encoding="utf-8")
            keep.add(rec.get("id") or rec.get("legacy"))
            con.execute("INSERT OR REPLACE INTO seed_base(tbl, id, record) VALUES (?, ?, ?)", (t, rec.get("id") or rec.get("legacy"), s))
            n += 1
        for f in d.glob("*.json"):
            if f.stem not in keep:
                f.unlink()
    return n


def import_seed(con, seed: Path = SEED, conflicts: Path | None = None) -> dict:
    _ensure_base(con)
    conflicts = conflicts or (ROOT / "region" / "seed_conflicts")
    report = {"taken": 0, "kept": 0, "added": 0, "conflicts": [], "removed_in_seed": []}
    for d in sorted(p for p in seed.iterdir() if p.is_dir()):
        t = d.name
        if t in DERIVED:
            continue
        cols = set(D.columns(con, t))
        seed_ids = set()
        for f in sorted(d.glob("*.json")):
            s = f.read_text(encoding="utf-8"); rec = _from_json(s)
            key = rec.get("id") or rec.get("legacy"); seed_ids.add(key)
            base = con.execute("SELECT record FROM seed_base WHERE tbl=? AND id=?", (t, key)).fetchone()
            cur = con.execute("SELECT * FROM %s WHERE %s=?" % (t, "id" if "id" in cols else "legacy"), (key,)).fetchone()
            cur_s = _to_json(D._join(con, t, cur)) if cur else None
            if cur is None:
                _write(con, t, rec); report["added"] += 1
            elif base and base[0] == s:
                report["kept"] += 1                               # the seed did not change; ours stands
            elif base and base[0] == cur_s:
                _write(con, t, rec, replace=True); report["taken"] += 1   # we did not change; take the seed
            elif cur_s == s:
                report["kept"] += 1
            else:
                report["conflicts"].append((t, key)); conflicts.mkdir(parents=True, exist_ok=True)
                (conflicts / f"{t}__{key}.json").write_text(s, encoding="utf-8")
            con.execute("INSERT OR REPLACE INTO seed_base(tbl, id, record) VALUES (?, ?, ?)", (t, key, s))
        for r in con.execute("SELECT id FROM seed_base WHERE tbl=?", (t,)):
            if r[0] not in seed_ids:
                report["removed_in_seed"].append((t, r[0]))
    return report


def _write(con, t, rec, replace=False):
    cols = set(D.columns(con, t))
    if "version" in cols:
        cur = con.execute("SELECT version FROM %s WHERE id=?" % t, (rec["id"],)).fetchone()
        D.put(con, t, rec, if_version=cur[0] if (cur and replace) else None)
    else:
        row = D._split(con, t, rec)
        con.execute("INSERT OR REPLACE INTO %s(%s) VALUES (%s)" % (t, ",".join(row), ",".join("?" * len(row))), list(row.values()))
