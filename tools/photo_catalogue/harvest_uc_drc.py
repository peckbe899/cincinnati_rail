#!/usr/bin/env python3
"""Catalogue harvester: UC Libraries Digital Resource Commons (DSpace),
"Cincinnati Subway and Street Improvements" (City Engineer photographs).

Usage:
  python3 harvest_uc_drc.py OUT.jsonl --raw RAW_DIR [--probe-step 400]
        [--ranges 716300-716420,...] [--cap 1200] [--offline]

Access route. The site's robots.txt disallows the REST API (except bitstream
content), the OAI-PMH endpoint, /search and /browse, so none of those are used.
Community and collection pages are not server rendered (their data would come
from the disallowed API), so a collection cannot be listed. What robots.txt
does allow, and what this script uses, is:
  /handle/2374.UC/<n>   answers 301 to /items/<uuid> (one request)
  /items/<uuid>         server rendered page with the full record embedded
Item handles of this collection are consecutive-ish numbers assigned in
box/folder order, and folders are alphabetical by street, so the script
(1) probes every --probe-step'th handle to map which box/folder sits where and
(2) walks the handle ranges given by --ranges. Each record costs two requests
at the 10 second crawl delay robots.txt asks for, so one run inside the
1200-request cap can only hold a few hundred of the 8,000+ records. Rerun with
other --ranges (the cache keeps what was fetched) to extend coverage.

Metadata and links only: no image is downloaded.
"""
import argparse
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import drc_fetch as D  # noqa: E402

SOURCE = "uc_drc"
HANDLE_PREFIX = "2374.UC/"
COMMUNITY = "Cincinnati Subway and Street Improvements"
# handle span of the community's items, learned from probing
DEFAULT_SPAN = (702781, 733200)

# Street names (as they appear in folder names and dc.subject, without the
# "(Cincinnati, Ohio)" tail) that lie wholly or mainly in the West End.
WEST_END = [
    "Freeman Avenue", "Baymiller Street", "Linn Street", "Cutter Street", "Mound Street",
    "John Street", "Smith Street", "Central Avenue", "Carr Street", "Harriet Street",
    "Hopkins Street", "Clark Street", "Richmond Street", "Kenyon Avenue", "Barr Street",
    "Betts Street", "Clinton Street", "Everett Street", "Armory Avenue", "Wade Street",
    "Lincoln Park Drive", "Laurel Parkway", "Terminal Parkway", "Laurel Street", "Gest Street",
    "Dalton Avenue", "Dalton Street", "McLean Avenue", "George Street", "Longworth Street",
    "Carlisle Avenue", "Dayton Street", "Bank Street", "Western Avenue", "Hoefer Street",
    "Poplar Street", "York Street", "Chestnut Street", "Kenner Street", "Hulbert Street",
    "Cincinnati Union Terminal", "Union Terminal", "Crosley Field", "Laurel Homes",
    "Lincoln Court", "Lincoln Park", "Eighth Street Viaduct", "Western Hills Viaduct",
    "Sixth Street Viaduct", "Waldvogel Viaduct", "Plum Street Depot", "Colerain Avenue Viaduct",
    "Kenyon-Barr", "Queensgate", "West End", "Mill Creek Expressway", "Millcreek Expressway",
    "Stone Street", "Budd Street", "Gilmore Avenue", "Flint Street", "Oliver Street",
    "Elizabeth Street", "Barnard Street", "Livingston Street", "Cook Street", "Whiteman Street",
    "Sherman Avenue", "David Street", "Charlotte Street", "Hathaway Street", "Jones Street",
]
# Streets that cross the West End but also run through downtown or Over-the-Rhine:
# decided by the holder's estimated coordinates when present.
AMBIGUOUS = [
    "Central Parkway", "Liberty Street", "Court Street", "Findlay Street", "Third Street",
    "Fourth Street", "Fifth Street", "Sixth Street", "Seventh Street", "Eighth Street",
    "Ninth Street", "Second Street", "Pearl Street", "Front Street", "Water Street",
    "Plum Street", "Elm Street", "Race Street", "Twelfth Street", "Thirteenth Street",
    "Fourteenth Street", "Fifteenth Street", "Canal", "Vine Street", "Walnut Street",
    "Main Street", "Sycamore Street", "Broadway", "McMicken Avenue", "Elder Street",
    "Green Street", "Pleasant Street", "Mohawk",
]
COORD_RE = re.compile(r"(3[89]\.\d{3,})\s*,\s*(-8[45]\.\d{3,})")


def name_hit(names, text):
    low = text.lower()
    return [n for n in names if re.search(r"(?<![a-z])" + re.escape(n.lower()) + r"(?![a-z])", low)]


def relevance(text, lat, lon):
    """Return (relevance, reason). Coordinates are the holder's estimates."""
    we = name_hit(WEST_END, text)
    if lat is not None:
        if 39.093 <= lat <= 39.126 and -84.548 <= lon <= -84.5195:
            return "west_end", "holder coordinates fall in West End box" + ("; names " + ", ".join(we) if we else "")
        if we:
            return "west_end", "names " + ", ".join(we) + " (coordinates outside West End box, check)"
        if 39.095 <= lat < 39.1075 and -84.5195 < lon <= -84.5125:
            return "downtown_west", "holder coordinates downtown west of Vine"
        if 39.1075 <= lat <= 39.120 and -84.5215 < lon <= -84.5125:
            return "otr", "holder coordinates in Over-the-Rhine west of Vine"
        return "other", ""
    if we:
        return "west_end", "names " + ", ".join(we)
    amb = name_hit(AMBIGUOUS, text)
    if amb:
        return "downtown_west", "no coordinates; basin street named (" + ", ".join(amb) + "), could be downtown, Over-the-Rhine or West End"
    return "other", ""


def years(date_text):
    ys = [int(y) for y in re.findall(r"(?<!\d)(1[89]\d\d|20[0-2]\d)(?!\d)", date_text or "")]
    return (min(ys), max(ys)) if ys else (None, None)


def view_type(desc, dctype):
    low = desc.lower()
    if "interior" in low or "basement" in low or "inside" in low:
        return "interior"
    if "aerial" in low:
        return "oblique_aerial"
    if "drawing" in low or "blueprint" in low or "plan of" in low:
        return "drawing"
    if "map" in low.split():
        return "map"
    if "photograph" in " ".join(dctype).lower():
        return "street_scene"
    return "unknown"


def record_from_page(text, page_url):
    st = D.state(text)
    if st is None:
        return None
    objs = D.objects(st)
    items = [o for o in objs if o.get("type") == "item"]
    if not items:
        return None
    it = items[0]
    g = lambda k: D.md(it, k)  # noqa: E731
    title = "; ".join(g("dc.title"))
    colls = [("; ".join(D.md(o, "dc.title"))) for o in objs if o.get("type") == "collection"]
    comms = [("; ".join(D.md(o, "dc.title"))) for o in objs if o.get("type") == "community"]
    desc = g("dc.description")
    notes_md = g("dc.description.notes")
    series = g("dc.relation.ispartofseries")
    subjects = g("dc.subject")
    date_text = "; ".join(g("dc.date.created"))
    y0, y1 = years(date_text)
    if y0 is None:
        y0, y1 = years(title.rsplit("--", 1)[-1])
    # folder name in the title: "... Box 25, Folder 47 (Laurel Parkway) -- print, 1934-04-16"
    m = re.search(r"Folder\s+\S+\s+\((.*?)\)\s+--", title)
    folder_name = m.group(1).strip() if m else ""
    m = re.search(r"(Box\s+\S+?,\s+Folder\s+\S+)", title)
    box_folder = m.group(1) if m else ""
    streets = [re.sub(r"\s*\(Cincinnati, Ohio\)\s*$", "", s) for s in subjects if "(Cincinnati" in s]
    street = folder_name if re.search(r"(Street|Avenue|Road|Parkway|Drive|Pike|Place|Alley|Boulevard|Way|Lane|Terrace|Court|Viaduct|Bridge)", folder_name) else (streets[0] if streets else "")
    cross = [s for s in streets if s.lower() != street.lower()]
    coords = "; ".join(g("dc.coverage.spatial"))
    cm = COORD_RE.search(coords) or COORD_RE.search(" ".join(notes_md))
    lat, lon = (float(cm.group(1)), float(cm.group(2))) if cm else (None, None)
    hn = re.search(r"(?:No\.|#)\s*(\d{2,4})\b|\b(\d{3,4})\s+(?:[NSEW]\.\s+)?[A-Z][a-z]+\s+(?:St|Ave|Street|Avenue)\b", " ".join(desc))
    house = (hn.group(1) or hn.group(2)) if hn else ""
    # public files are the ones the page links for download
    public = set(re.findall(r'/bitstreams/([0-9a-f-]{36})/download', text))
    bits = [o for o in objs if o.get("type") == "bitstream" and o["uuid"] in public]
    bits.sort(key=lambda o: -(o.get("sizeBytes") or 0))
    def content(o):
        return o.get("_links", {}).get("content", {}).get("href", "")
    image_url = content(bits[0]) if bits else ""
    files = ["%s (%s bytes) %s" % (o.get("name") or "; ".join(D.md(o, "dc.title")), o.get("sizeBytes"), content(o)) for o in bits]
    thumbs = [o for o in objs if o.get("type") == "bitstream" and o["uuid"] not in public
              and re.search(r"\.jpe?g\.jpg$", (o.get("name") or "; ".join(D.md(o, "dc.title"))), re.I)]
    thumb_url = content(thumbs[-1]) if thumbs else ""
    stem = ""
    if bits:
        stem = re.sub(r"\.[A-Za-z0-9]+$", "", bits[0].get("name") or "; ".join(D.md(bits[0], "dc.title")))
    loc_parts = [p for p in [folder_name] + subjects + ([coords] if coords else []) if p]
    alltext = " | ".join([title] + desc + notes_md + subjects)
    rel, why = relevance(alltext, lat, lon)
    caption = " | ".join(desc + [n for n in notes_md if not n.startswith("GeoCoordinates")])[:600]
    notes = []
    if why:
        notes.append("relevance: " + why)
    if lat is not None:
        notes.append("holder coordinates %s,%s (holder marks many as estimated)" % (lat, lon))
    if series:
        notes.append("series: " + "; ".join(series))
    fmt = "; ".join(g("dc.format.medium") + g("dc.format.extent"))
    if fmt:
        notes.append("format: " + fmt)
    if len(files) > 1:
        notes.append("other public files: " + " ; ".join(files[1:]))
    handle = it.get("handle") or ""
    return {
        "source": SOURCE,
        "holder": "; ".join(g("dc.publisher.OLrepository")) or "University of Cincinnati. Archives and Rare Books Library",
        "collection": " / ".join([c for c in ([COMMUNITY] if COMMUNITY in comms else comms[-1:]) + colls[:1] if c]),
        "item_id": handle,
        "call_number": ", ".join([p for p in [box_folder, stem] if p]),
        "title": title,
        "caption": caption,
        "creator": "; ".join(g("dc.contributor.author")),
        "date_text": date_text,
        "year_min": y0,
        "year_max": y1,
        "location_text": " | ".join(loc_parts),
        "street": street,
        "house_number": house,
        "cross_street": "; ".join(cross),
        "landmark": folder_name if folder_name and folder_name != street else "",
        "plot_or_project_number": "",
        "page_url": page_url,
        "image_url": image_url,
        "thumb_url": thumb_url,
        "rights_text": "; ".join(g("dc.rights") + g("dc.rights.uri"))[:300],
        "view_type": view_type(" ".join(desc), g("dc.type")),
        "relevance": rel,
        "notes": " || ".join(notes),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("out")
    ap.add_argument("--raw", required=True, help="cache folder for fetched pages")
    ap.add_argument("--probe-step", type=int, default=400, help="probe every Nth handle across the span (0 = no probing)")
    ap.add_argument("--span", default="%d-%d" % DEFAULT_SPAN)
    ap.add_argument("--ranges", default="", help="comma list of handle ranges a-b to walk in full")
    ap.add_argument("--cap", type=int, default=1200)
    ap.add_argument("--offline", action="store_true", help="build the output from the cache only")
    a = ap.parse_args()

    c = D.DrcClient(a.raw, cap=a.cap, offline=a.offline)
    plan = []
    lo, hi = [int(x) for x in a.span.split("-")]
    if a.probe_step:
        plan += list(range(lo, hi + 1, a.probe_step))
    for r in [r for r in a.ranges.split(",") if r.strip()]:
        x, y = [int(v) for v in r.split("-")]
        plan += list(range(x, y + 1))
    stop = ""
    try:
        for n in plan:
            loc = c.resolve_handle(HANDLE_PREFIX + str(n))
            if loc.startswith("/items/"):
                c.get(D.HOST + loc)
    except D.Refused as e:
        stop = str(e)

    # the output is rebuilt from everything in the cache, so reruns accumulate
    recs, bad, missing = {}, 0, 0
    for fn in sorted(os.listdir(a.raw)):
        if not (fn.startswith("handle_") and fn.endswith(".txt")):
            continue
        loc = open(os.path.join(a.raw, fn)).read().strip()
        if not loc.startswith("/items/"):
            continue
        url = D.HOST + loc
        p = c.cache_path(url)
        if not os.path.exists(p):
            missing += 1
            continue
        rec = record_from_page(open(p, encoding="utf-8", errors="replace").read(), url)
        if rec is None:
            bad += 1
            continue
        recs[rec["item_id"] or url] = rec
    for fn in sorted(os.listdir(a.raw)):  # item pages fetched directly, not via a handle
        if fn.startswith("drc_libraries_uc_edu_items_") and fn.endswith(".html"):
            text = open(os.path.join(a.raw, fn), encoding="utf-8", errors="replace").read()
            m = re.search(r'/server/api/core/items/([0-9a-f-]{36})/owningCollection', text)
            rec = record_from_page(text, D.HOST + "/items/" + m.group(1)) if m else None
            if rec and (rec["item_id"] or rec["page_url"]) not in recs:
                recs[rec["item_id"] or rec["page_url"]] = rec
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)

    def hkey(k):
        m = re.search(r"/(\d+)$", k)
        return int(m.group(1)) if m else 0

    with open(a.out, "w", encoding="utf-8") as f:
        for k in sorted(recs, key=hkey):
            f.write(json.dumps(recs[k], ensure_ascii=False) + "\n")
    rel = {}
    for r in recs.values():
        rel[r["relevance"]] = rel.get(r["relevance"], 0) + 1
    print("records: %d  by relevance: %s  unparsed pages: %d  handles without page: %d  requests so far: %d%s"
          % (len(recs), rel, bad, missing, c.n_requests, ("  STOPPED: " + stop) if stop else ""))


if __name__ == "__main__":
    main()
