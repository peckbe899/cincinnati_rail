"""KMZ/KML reading and writing without third-party dependencies.

Reading keeps the folder hierarchy so that programs can select lines and station folders
by path (e.g. "Cincinnati Rail/Cincinnati RER/RER-1"). MultiGeometry placemarks are
expanded into their component LineStrings.
"""

from __future__ import annotations

import io
import re
import zipfile
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, List, Optional
from xml.sax.saxutils import escape


@dataclass
class Placemark:
    name: str
    folder_path: tuple  # names of enclosing folders, outermost first (Document excluded)
    description: str = ""
    style: str = ""
    points: List[tuple] = field(default_factory=list)  # [(lat, lon, z)]
    lines: List[List[tuple]] = field(default_factory=list)  # each [(lat, lon, z), ...]
    has_z: bool = False  # True if any coordinate carried a non-zero altitude

    @property
    def path_str(self) -> str:
        return "/".join(self.folder_path)


def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _child(e, name):
    for c in e:
        if _local(c.tag) == name:
            return c
    return None


def _parse_coords(text: str):
    out = []
    has_z = False
    for tok in (text or "").split():
        parts = tok.split(",")
        if len(parts) < 2:
            continue
        lon, lat = float(parts[0]), float(parts[1])
        z = float(parts[2]) if len(parts) > 2 and parts[2] != "" else 0.0
        if z != 0.0:
            has_z = True
        out.append((lat, lon, z))
    return out, has_z


def read_kml_bytes(data: bytes) -> List[Placemark]:
    root = ET.fromstring(data)
    out: List[Placemark] = []

    def walk(elem, path):
        for c in elem:
            t = _local(c.tag)
            if t == "Document":
                walk(c, path)
            elif t == "Folder":
                n = _child(c, "name")
                walk(c, path + ((n.text or "").strip() if n is not None else "",))
            elif t == "Placemark":
                out.append(_parse_placemark(c, path))

    walk(root, ())
    return out


def _parse_placemark(pm, path) -> Placemark:
    n = _child(pm, "name")
    d = _child(pm, "description")
    s = _child(pm, "styleUrl")
    p = Placemark(
        name=(n.text or "").strip() if n is not None else "",
        folder_path=path,
        description=(d.text or "").strip() if d is not None else "",
        style=(s.text or "").strip() if s is not None else "",
    )
    for g in pm.iter():
        t = _local(g.tag)
        if t not in ("Point", "LineString"):
            continue
        ce = _child(g, "coordinates")
        if ce is None:
            continue
        coords, hz = _parse_coords(ce.text)
        p.has_z = p.has_z or hz
        if t == "Point" and coords:
            p.points.append(coords[0])
        elif t == "LineString" and len(coords) >= 2:
            p.lines.append(coords)
    return p


def read_kmz(path: str | Path) -> List[Placemark]:
    path = Path(path)
    if path.suffix.lower() == ".kml":
        return read_kml_bytes(path.read_bytes())
    with zipfile.ZipFile(path) as z:
        names = [n for n in z.namelist() if n.lower().endswith(".kml")]
        if not names:
            raise ValueError(f"No .kml inside {path}")
        main = "doc.kml" if "doc.kml" in names else names[0]
        return read_kml_bytes(z.read(main))


def select(placemarks: Iterable[Placemark], folder: Optional[str] = None,
           name_regex: Optional[str] = None) -> List[Placemark]:
    """Filter placemarks whose folder path starts with `folder` (slash separated, case-insensitive,
    any leading folders may be omitted) and whose name matches `name_regex`."""
    want = [w.strip().lower() for w in folder.split("/")] if folder else None
    rx = re.compile(name_regex, re.I) if name_regex else None
    out = []
    for p in placemarks:
        if want is not None:
            fp = [f.lower() for f in p.folder_path]
            ok = any(fp[i:i + len(want)] == want for i in range(len(fp) - len(want) + 1))
            if not ok:
                continue
        if rx and not rx.search(p.name):
            continue
        out.append(p)
    return out


# ----------------------------------------------------------------------------- writing

class KmlWriter:
    """Tiny KML builder: folders, styled LineStrings and Points."""

    def __init__(self, name: str):
        self.name = name
        self._styles = {}
        self._body: List[str] = []
        self._depth = 0

    def _style_id(self, color_abgr: str, width: float) -> str:
        key = (color_abgr, round(width, 1))
        if key not in self._styles:
            self._styles[key] = f"s{len(self._styles)}"
        return self._styles[key]

    def open_folder(self, name: str):
        self._body.append(f"<Folder><name>{escape(name)}</name>")

    def close_folder(self):
        self._body.append("</Folder>")

    def line(self, name: str, latlonz, color_abgr="ff0000ff", width=4.0, description="",
             absolute_altitude=False):
        sid = self._style_id(color_abgr, width)
        coords = " ".join(f"{lon:.7f},{lat:.7f},{z:.2f}" for lat, lon, z in latlonz)
        alt = "<altitudeMode>absolute</altitudeMode>" if absolute_altitude else ""
        self._body.append(
            f"<Placemark><name>{escape(name)}</name>"
            f"<description>{escape(description)}</description><styleUrl>#{sid}</styleUrl>"
            f"<LineString><tessellate>1</tessellate>{alt}<coordinates>{coords}</coordinates>"
            f"</LineString></Placemark>")

    def point(self, name: str, lat: float, lon: float, description: str = ""):
        self._body.append(
            f"<Placemark><name>{escape(name)}</name><description>{escape(description)}</description>"
            f"<Point><coordinates>{lon:.7f},{lat:.7f},0</coordinates></Point></Placemark>")

    def to_string(self) -> str:
        styles = "".join(
            f'<Style id="{sid}"><LineStyle><color>{c}</color><width>{w}</width></LineStyle></Style>'
            for (c, w), sid in self._styles.items())
        return ('<?xml version="1.0" encoding="UTF-8"?>\n'
                '<kml xmlns="http://www.opengis.net/kml/2.2"><Document>'
                f"<name>{escape(self.name)}</name>{styles}{''.join(self._body)}</Document></kml>")

    def save(self, path: str | Path):
        path = Path(path)
        data = self.to_string().encode("utf-8")
        if path.suffix.lower() == ".kml":
            path.write_bytes(data)
            return
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
            z.writestr("doc.kml", data)
        path.write_bytes(buf.getvalue())


def rgb_to_kml(r: float, g: float, b: float, a: float = 1.0) -> str:
    """matplotlib-style floats (0..1) -> KML aabbggrr hex."""
    c = [int(round(max(0, min(1, v)) * 255)) for v in (a, b, g, r)]
    return "".join(f"{v:02x}" for v in c)
