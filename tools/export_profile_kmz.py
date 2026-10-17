"""Export designed Rail Profiles lines as 3D KMZ for Google Earth, the same file the page's
"Export KMZ" button makes (the published page can only save it as .kmz.zip): one uniform line in
the line's colour from its source KMZ (purple if none), width 4, at rail level (absolute altitude,
NAVD88 m), extruded to the ground, a vertex about every 10 m, normal/highlight styles, and the
stations at the platform centre with their rail level, depth and structure.

    python tools/export_profile_kmz.py CVG_Express Line_9 RER_2 --out out/kmz
    python tools/export_profile_kmz.py all --alignments <dir of saved page profiles>

Saved profiles come from --alignments (one <id>.json per line, e.g. the page database read with
ArtifactData), else data/profile/alignments; lines without one use the solver default.
"""

from __future__ import annotations

import argparse
import json
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from xml.sax.saxutils import escape

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from railsim.metro_profile import STRUCTURE, MetroProfile  # noqa: E402

PROFILE = ROOT / "data" / "profile"
STEP, WIDTH, DEFAULT_COLOR = 10.0, 4, "ff800080"
LABEL = {"elevated": "Elevated", "atgrade": "At grade", "trough": "Open trough", "cutcover": "Cut & cover",
         "shield": "Shallow shield", "deep": "Deep tube"}


def line_ids():
    ids = [e["id"] for e in json.loads((PROFILE / "lines" / "index.json").read_text())]
    return ids + [e["id"] for e in json.loads((PROFILE / "rer" / "lines" / "index.json").read_text())]


def load(lid: str, align_dir: Path | None) -> MetroProfile:
    rer = lid.startswith("RER_")
    line = PROFILE / ("rer/lines" if rer else "lines") / f"{lid}.json"
    al = None
    for d in ([align_dir] if align_dir else []) + [PROFILE / "alignments"]:
        if d and (Path(d) / f"{lid}.json").exists():
            doc = json.loads((Path(d) / f"{lid}.json").read_text())
            al = Path(d) / f"{lid}.json"
            if "data" in doc and "st" not in doc:  # an ArtifactData record: unwrap it
                tmp = ROOT / "out" / "tmp_align" / f"{lid}.json"
                tmp.parent.mkdir(parents=True, exist_ok=True)
                tmp.write_text(json.dumps(doc["data"]))
                al = tmp
            break
    settings = PROFILE / ("rer/settings.json" if rer else "settings.json")
    return MetroProfile.load(line, al, settings), al


def lonlat(mp: MetroProfile, c):
    p = np.array(mp.data["path"], float)
    return np.interp(c, p[:, 0], p[:, 1]), np.interp(c, p[:, 0], p[:, 2])


def build_kml(mp: MetroProfile) -> str:
    L = mp.length
    c = np.append(np.arange(0.0, L, STEP), L)
    z = mp.rail_at(c)
    lon, lat = lonlat(mp, c)
    colour = (mp.data.get("color") or DEFAULT_COLOR).lower()
    name = f"{mp.data['line']} 3D"
    coords = " ".join(f"{a:.7f},{b:.7f},{h:.2f}" for a, b, h in zip(lon, lat, z))
    half = mp.settings["platform"] / 2
    sts = []
    for i, s in enumerate(mp.stations):
        zr = float(mp.st[i])
        slon, slat = lonlat(mp, s["c"])
        t = mp.type_at(s["c"], zr)
        data = {"rail": round(zr, 2), "c": round(s["c"], 2), "point_c": round(s.get("c0", s["c"]), 2),
                "ground": round(float(mp.ground_at(s["c"])), 2), "depth": round(float(mp.surface_at(s["c"])) - zr, 2),
                "structure": LABEL.get(t, t), "platform_m": round(2 * half, 2),
                "platform_from": round(s["c"] - half, 2), "platform_to": round(s["c"] + half, 2),
                "platform_grade_permille": mp.sg[i] if i < len(mp.sg) else 0}
        ext = "".join(f'<Data name="{k}"><value>{escape(str(v))}</value></Data>' for k, v in data.items())
        sts.append(f"<Placemark><name>{escape(s['name'])}</name><styleUrl>#st</styleUrl><ExtendedData>{ext}</ExtendedData>"
                   f"<Point><extrude>1</extrude><altitudeMode>absolute</altitudeMode>"
                   f"<coordinates>{float(slon):.7f},{float(slat):.7f},{zr:.2f}</coordinates></Point></Placemark>")
    style = (f'<StyleMap id="rail"><Pair><key>normal</key><styleUrl>#rail_n</styleUrl></Pair>'
             f'<Pair><key>highlight</key><styleUrl>#rail_h</styleUrl></Pair></StyleMap>'
             f'<Style id="rail_n"><LineStyle><color>{colour}</color><width>{WIDTH}</width></LineStyle></Style>'
             f'<Style id="rail_h"><LineStyle><color>{colour}</color><width>{WIDTH}</width></LineStyle></Style>'
             f'<Style id="st"><IconStyle><scale>0.9</scale><Icon><href>http://maps.google.com/mapfiles/kml/shapes/rail.png</href>'
             f'</Icon></IconStyle><LineStyle><color>{colour}</color><width>1</width></LineStyle></Style>')
    stamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
    desc = (f"{mp.data.get('system', '')} {mp.data['line']}: designed rail at rail level (absolute altitude, NAVD88 m), "
            f"extruded to the ground; stations at the platform centre. Exported {stamp}.")
    return ('<?xml version="1.0" encoding="UTF-8"?><kml xmlns="http://www.opengis.net/kml/2.2" '
            'xmlns:gx="http://www.google.com/kml/ext/2.2"><Document>'
            f"<name>{escape(name)}</name><description>{escape(desc)}</description>{style}"
            f'<Placemark><name>{escape(name)}</name><styleUrl>#rail</styleUrl><LineString><extrude>1</extrude>'
            f"<altitudeMode>absolute</altitudeMode><coordinates>{coords}</coordinates></LineString></Placemark>"
            f"<Folder><name>Stations</name>{''.join(sts)}</Folder></Document></kml>")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("lines", nargs="+", help="line ids (e.g. CVG_Express Line_9 RER_2) or 'all'")
    ap.add_argument("--alignments", type=Path, help="directory of saved page profiles (<id>.json)")
    ap.add_argument("--out", type=Path, default=ROOT / "out" / "kmz")
    a = ap.parse_args(argv)
    ids = line_ids() if a.lines == ["all"] else a.lines
    a.out.mkdir(parents=True, exist_ok=True)
    for lid in ids:
        mp, al = load(lid, a.alignments)
        dest = a.out / f"{lid}_profile.kmz"
        with zipfile.ZipFile(dest, "w", zipfile.ZIP_DEFLATED) as z:
            z.writestr(f"{lid}_profile.kml", build_kml(mp))
        print(f"{dest.relative_to(ROOT) if dest.is_relative_to(ROOT) else dest}  "
              f"({mp.length / 1000:.2f} km, {len(mp.stations)} stations, {'saved profile' if al else 'solver default'}, "
              f"colour {mp.data.get('color') or DEFAULT_COLOR})")


if __name__ == "__main__":
    main()
