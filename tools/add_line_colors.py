"""Write each Rail Profiles line's map colour (KML aabbggrr, the most common LineStyle colour of
its drawn track in the source KMZ) into its line file as `color`, for the page's 3D KMZ export.

    python tools/add_line_colors.py        (after rebuilding line files)
"""

from __future__ import annotations

import collections
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from railsim.kml import line_styles, read_kmz, select  # noqa: E402

PROFILE = ROOT / "data" / "profile"
KMZ = ROOT / "data" / "kmz" / "Cincinnati_Rail.kmz"


def colour(kmz, folder, exclude=()):
    styles = line_styles(kmz)
    pms = [p for p in select(read_kmz(kmz), folder) if p.lines and p.name not in exclude]
    cols = collections.Counter(styles.get(p.style.lstrip("#"), ("", 0))[0] for p in pms)
    cols.pop("", None)
    return cols.most_common(1)[0][0] if cols else None


def main():
    jobs = []
    for e in json.loads((PROFILE / "lines" / "index.json").read_text()):
        if e["id"] == "CVG_Express":
            jobs.append((PROFILE / "lines" / "CVG_Express.json", ROOT / "data" / "kmz" / "CVG_Express.kmz",
                         "CVG Express New", ("CVG Express 5 - Original", "CVG Express Yard", "Maintenance Building")))
        else:
            jobs.append((PROFILE / "lines" / f"{e['id']}.json", KMZ, f"Cincinnati Metro/{e['line']}", ()))
    for e in json.loads((PROFILE / "rer" / "lines" / "index.json").read_text()):
        jobs.append((PROFILE / "rer" / "lines" / f"{e['id']}.json", KMZ, f"Cincinnati RER/{e['line']}", ()))
    for path, kmz, folder, excl in jobs:
        d = json.loads(path.read_text())
        c = colour(kmz, folder, excl)
        d["color"] = c
        path.write_text(json.dumps(d, separators=(",", ":")))
        print(f"{d['id']:12s} {folder:28s} {c}")


if __name__ == "__main__":
    main()
