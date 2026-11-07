import argparse
from pathlib import Path

from . import db, seed


def main():
    p = argparse.ArgumentParser(prog="python -m region.model")
    sub = p.add_subparsers(dest="cmd", required=True)
    e = sub.add_parser("export"); e.add_argument("--db", default="region.db"); e.add_argument("--out", default=str(seed.SEED))
    i = sub.add_parser("import"); i.add_argument("--db", default="region.db"); i.add_argument("--seed", default=str(seed.SEED))
    m = sub.add_parser("migrate"); m.add_argument("--db", default="region.db")
    a = p.parse_args()
    con = db.open_db(a.db)
    if a.cmd == "export":
        print("exported", seed.export(con, Path(a.out)), "records to", a.out)
    elif a.cmd == "import":
        print(seed.import_seed(con, Path(a.seed)))
    else:
        print("schema at", con.execute("SELECT max(version) FROM schema_version").fetchone()[0])


main()
