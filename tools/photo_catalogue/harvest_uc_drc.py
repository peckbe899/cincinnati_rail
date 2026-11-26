#!/usr/bin/env python3
"""Catalogue harvester: UC Libraries Digital Resource Commons (DSpace),
"Cincinnati Subway and Street Improvements" (City Engineer photographs).

Usage:
  python3 harvest_uc_drc.py OUT.jsonl --raw RAW_DIR [--probe-step 400]
        [--ranges 716300-716420,...] [--seek "Central Avenue@718381-718781,..."]
        [--items UUID,UUID]
        [--cap 1200] [--offline]

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
(3) --seek NAME@LO-HI looks for one street's folders without walking a whole
box: inside a stretch of handles where folders run alphabetically it halves
the interval on the folder name until it lands in a folder whose name starts
with NAME, then walks both ways to the folder's ends. Add ":lo" when pages that
are not street folders (date folders, other collections, missing handles) lie
below the target in the interval; the default treats them as above it.

Where the boxes sit (learned by probing, November 2026; handles 2374.UC/<n>).
Boxes were loaded in part-box batches, mostly but not always in box order:
  703581-705581  Rapid Transit Photographs, Boxes 12 to 20 (folders named by date)
  717181-717292  Box 35 negatives, Fifth Street to Gate Street (Freeman at 717260)
  717293-717400  Box 39 negatives, Liberty Street to Lischer Avenue
  718381-718935  Boxes 32 to 34 negatives, Burnet to Erie (Central Avenue 718434,
                 Court 718544, Cutter 718618, Eighth Street 718803)
  718944-719181  Box 36 negatives from Geiger Street (Gest Street 718950)
  719308-719431  Box 37 negatives, Ida to Kemper (John Street near 719343)
  719435-719581  Box 40 negatives, Madison to McFadden
  719782-719887  Box 38 negatives, order jumbled (Laurel Street at 719887)
  719888-720046  Boxes 42 and 41 negatives in pieces
  720081-720181  Box 42 negatives, Myrtle to North Wendell (Ninth Street 720106)
  720381-720981  Boxes 43 to 45 negatives, Postal Alley to Taylor (Richmond 720556,
                 Sixth Street 720771 to 720830, Smith 720837)
  724781         Box 29 prints (Tyne Avenue)
  725981, 726185 Miscellaneous Photographs, Box 54
  728309-728431  Box 21 prints, Bassett to Clara
  728481-728781  Box 51 negatives (folders named by date)
  729243-729410  Box 48 prints (by date); 729581 Box 50; 729758 Box 46 (Torrence)
  729981-730090  Box 27 prints, Montgomery to Portman
  730312-730379  Box 25 prints, Kreis Lane to Liddell (Laurel Street 730335-730355)
  730380-        Box 24 prints from Harrison Avenue
Not yet located: Boxes 22, 23, 26, 28 (prints D to G, M, R to S), 30, 31, 47
(negatives A to B, W to Z) and most of 46, 48 to 53.

The request count is kept in RAW_DIR/requests_made.txt so the per-host cap holds
across runs in one sitting; remove that file to start a new budget another day.

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
    "Kenyon-Barr", "Queensgate", "Mill Creek Expressway", "Millcreek Expressway",
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
    "Fourteenth Street", "Fifteenth Street", "Canal", "Vine Street", "McMicken Avenue",
    "Elder Street", "Green Street", "Pleasant Street", "Mohawk",
]
# Names that put a basin photograph east of Vine Street (so not downtown_west).
EAST_SIDE = [
    "Walnut Street", "Main Street", "Sycamore Street", "Broadway", "Lock Street", "Ellen Street",
    "Eggleston Avenue", "Culvert Street", "Pike Street", "Butler Street", "Lawrence Street",
    "Ludlow Street", "Marine Hospital", "Fifth Street Viaduct", "Gilbert Avenue", "Reading Road",
    "Columbia Parkway", "Eastern Avenue", "Martin Street", "Kilgour Street", "Mount Adams",
]
# Basin streets that lie at Over-the-Rhine latitude (north of the old canal).
OTR_LATITUDE = [
    "Liberty Street", "Findlay Street", "Twelfth Street", "Thirteenth Street", "Fourteenth Street",
    "Fifteenth Street", "McMicken Avenue", "Elder Street", "Green Street", "Pleasant Street", "Mohawk",
]
WEST_OF_VINE = ["Race Street", "Elm Street", "Plum Street", "Central Parkway", "Canal"]
# series title prefix -> collection name inside the community
SERIES_COLLECTION = {
    "Street Improvement Photographs": "Street Construction and Improvements",
    "Rapid Transit Photographs": "Rapid Transit Construction",
    "Miscellaneous Photographs": "Miscellaneous Photographs and Negatives",
}
COORD_RE = re.compile(r"(3[89]\.\d{3,})\s*,\s*(-8[45]\.\d{3,})")


ABBREV = [(r"\bSts?\b\.?", "Street"), (r"\bAve?\b\.?", "Avenue"), (r"\bVia\b\.", "Viaduct"),
          (r"\bPkwy\b\.?", "Parkway"), (r"\b3rd\b", "Third"), (r"\b4th\b", "Fourth"), (r"\b5th\b", "Fifth"),
          (r"\b6th\b", "Sixth"), (r"\b7th\b", "Seventh"), (r"\b8th\b", "Eighth"), (r"\b9th\b", "Ninth")]


def expand(text):
    """Spell out the photographers' abbreviations so 'W. 8th St. Via.' matches 'Eighth Street Viaduct'."""
    for pat, rep in ABBREV:
        text = re.sub(pat, rep, text, flags=re.I)
    return text


def name_hit(names, text):
    low = text.lower()
    return [n for n in names if re.search(r"(?<![a-z-])" + re.escape(n.lower()) + r"(?![a-z])", low)]


def central_lon(lat):
    """Rough longitude of Central Avenue at a latitude (the basin grid leans west going north)."""
    return -84.5203 - (lat - 39.1003) * 0.30


def relevance(text, lat, lon):
    """Return (relevance, reason). Coordinates are the holder's estimates and can
    be a few blocks off, so a named West End street wins over them."""
    text = expand(text)
    we = name_hit(WEST_END, text)
    if lat is not None:
        edge = central_lon(lat) + 0.0008  # Central Avenue itself counts as West End
        mill = -84.546 + (lat - 39.095) * 0.23  # rough line of Mill Creek
        if 39.093 <= lat <= 39.126 and mill <= lon <= edge:
            return "west_end", "holder coordinates fall west of Central Avenue" + ("; names " + ", ".join(we) if we else "")
        if we:
            return "west_end", "names " + ", ".join(we) + " (holder coordinates fall outside the West End, check)"
        if edge < lon <= edge + 0.0086:  # about four blocks, Central Avenue to Vine Street
            if 39.095 <= lat < 39.1078:
                return "downtown_west", "holder coordinates downtown west of Vine"
            if 39.1078 <= lat <= 39.120:
                return "otr", "holder coordinates in Over-the-Rhine west of Vine"
        return "other", ""
    if we:
        return "west_end", "names " + ", ".join(we)
    amb = name_hit(AMBIGUOUS, text)
    east = name_hit(EAST_SIDE, text)
    em = EAST_PREFIX_RE.search(text)  # "E. Court St." is the part of the street east of Vine
    if em:
        east.append(em.group(0))
    if east and not name_hit(WEST_OF_VINE, text):
        return "other", "no coordinates; east of Vine by name (" + ", ".join(east) + ")"
    if amb:
        if name_hit(OTR_LATITUDE, text):
            return "otr", "no coordinates; named street (" + ", ".join(amb) + ") runs through Over-the-Rhine, but the view could be east of Vine or in the West End"
        return "downtown_west", "no coordinates; basin street named (" + ", ".join(amb) + "), could be downtown either side of Vine or the West End"
    return "other", ""


EAST_PREFIX_RE = re.compile(r"\bE(?:ast)?\.?\s+(?:Court|Second|Third|Fourth|Fifth|Sixth|Seventh|Eighth|Ninth|Twelfth|"
                            r"Thirteenth|Fourteenth|Fifteenth|Liberty|Front|Pearl|McMicken)\b")
DIR_RE = re.compile(r"\b(north|south|east|west|n|s|e|w|ne|nw|se|sw)(?:erly|wardly|ward)?\.?\s+(from|of|at|to|toward|towards)\s+([^/|]{2,60})", re.I)


def direction_hint(desc):
    """The photographer's own 'E. from Cutter' phrase, kept verbatim for later view cones."""
    m = DIR_RE.search(desc)
    return m.group(0).strip(" .") if m else ""


def years(date_text):
    ys = [int(y) for y in re.findall(r"(?<!\d)(1[89]\d\d|20[0-2]\d)(?!\d)", date_text or "")]
    return (min(ys), max(ys)) if ys else (None, None)


def view_type(desc, dctype, title=""):
    low = desc.lower()
    if not title.startswith(tuple(SERIES_COLLECTION)):  # other collections describe the view in the title
        tl = title.lower()
        if "aerial" in tl:
            return "oblique_aerial"
        if re.search(r"\b(panorama|skyline|view of (downtown )?cincinnati)\b", tl):
            return "panorama"
        return "unknown"
    if "interior" in low or "basement" in low or "inside" in low:
        return "interior"
    if "aerial" in low:
        return "oblique_aerial"
    if "drawing" in low or "blueprint" in low or "plan of" in low:
        return "drawing"
    if "map" in low.split():
        return "map"
    if re.search(r"\bNo\.?\s*\d{2,4}\b", desc) and not re.search(r"\b(from|looking|toward)\b", low):
        return "street_front"  # a view of one numbered building, as in the Law Dept. pictures
    if "photograph" in " ".join(dctype).lower():
        return "street_scene"
    return "unknown"


STREET_RE = re.compile(r"\b(Street|Avenue|Road|Parkway|Drive|Pike|Place|Alley|Boulevard|Way|Lane|Terrace|Court|Route|Highway)\b")
STRUCT_RE = re.compile(r"\b(Viaduct|Bridge|Overpass|Underpass|Subway|Steps|Market|Terminal|Station|Depot|Park|Hospital|"
                       r"School|Church|Building|Tunnel|Incline|Canal|Creek|Field|Homes|Hall|Square|Playground)\b")
HOUSE_RES = [
    re.compile(r"(?:\bNo\.?\s*|#\s*)(\d{2,4}(?:-\d{1,4})?)\b(?!\s*(?:'|ft|feet))"),
    re.compile(r"\b(?:from|at|of)\s+(\d{3,4})\b(?!\s*(?:'|ft|feet|block))", re.I),
    re.compile(r"\b(\d{3,4})\s+(?:[NSEW]\.\s+)?[A-Z][a-z]+\s+(?:St|Ave|Street|Avenue)\b"),
]


def house_number(desc, holder_notes):
    """House number as the photographer wrote it ('No. 1334 Cutter St.', 'W. from #511',
    'E. From 835'), else one the holder read off the picture ('The address "537" is seen')."""
    for rx in HOUSE_RES:
        m = rx.search(desc)
        if m:
            return m.group(1)
    m = re.search(r'address\s+"?(\d{2,4})"?', holder_notes)
    return m.group(1) if m else ""


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
    places = [re.sub(r"\s*\(Cincinnati, Ohio\)\s*$", "", s) for s in subjects if "(Cincinnati" in s]
    streets = [p for p in places if not STRUCT_RE.search(p)]
    landmarks = [p for p in places if STRUCT_RE.search(p)]
    street = ""
    if folder_name and not DATE_NAME_RE.search(folder_name):
        sm = STRUCT_RE.search(folder_name)
        if sm:  # "Sixth Street Viaduct Extension": the structure is the landmark, the street is what precedes it
            if folder_name.lower() not in [x.lower() for x in landmarks]:
                landmarks.insert(0, folder_name)
            head = folder_name[:sm.start()].strip()
            street = head if STREET_RE.search(head) else ""
        elif STREET_RE.search(expand(folder_name)) or folder_name.lower() in [x.lower() for x in streets]:
            street = folder_name
        else:
            landmarks.insert(0, folder_name)
    if not street and streets:
        street = streets[0]
    cross = [s for s in streets if s.lower() != street.lower()]
    coords = "; ".join(g("dc.coverage.spatial"))
    cm = COORD_RE.search(coords) or COORD_RE.search(" ".join(notes_md))
    lat, lon = (float(cm.group(1)), float(cm.group(2))) if cm else (None, None)
    # Rapid Transit captions end in the negative's serial number ("No 1889"), not an address
    house = "" if title.startswith("Rapid Transit") else house_number(" / ".join(desc), " ".join(notes_md))
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
    dh = direction_hint(" / ".join(desc))
    if dh:
        notes.append("direction as written: " + dh)
    if series:
        notes.append("series: " + "; ".join(series))
    fmt = "; ".join(g("dc.format.medium") + g("dc.format.extent"))
    if fmt:
        notes.append("format: " + fmt)
    if len(files) > 1:
        notes.append("other public files: " + " ; ".join(files[1:]))
    handle = it.get("handle") or ""
    part_of = [p for p in g("dc.relation.ispartof") if p != COMMUNITY]
    if colls or comms:
        collection = " / ".join([c for c in ([COMMUNITY] if COMMUNITY in comms else comms[-1:]) + colls[:1] + part_of if c])
    else:
        # a few pages arrive without their collection and file list; name the
        # collection from the series title, which is fixed for each of the three
        collection = " / ".join(g("dc.relation.ispartof")[:1] + [v for k, v in SERIES_COLLECTION.items() if title.startswith(k)])
        notes.append("page came without its file list, so no image link was recorded; open the page for the files")
    return {
        "source": SOURCE,
        "holder": "; ".join(g("dc.publisher.OLrepository")) or "University of Cincinnati. Archives and Rare Books Library",
        "collection": collection,
        "item_id": handle,
        "call_number": ", ".join([p for p in [box_folder, stem] if p]),
        "title": title,
        "caption": caption,
        "creator": "; ".join(g("dc.contributor.author") or g("dc.contributor")),
        "date_text": date_text,
        "year_min": y0,
        "year_max": y1,
        "location_text": " | ".join(loc_parts),
        "street": street,
        "house_number": house,
        "cross_street": "; ".join(cross),
        "landmark": "; ".join(landmarks),
        "plot_or_project_number": "",
        "page_url": page_url,
        "image_url": image_url,
        "thumb_url": thumb_url,
        "rights_text": "; ".join(g("dc.rights") + g("dc.rights.uri"))[:300],
        "view_type": view_type(" ".join(desc), g("dc.type"), title),
        "relevance": rel,
        "notes": " || ".join(notes),
        "_is_photo": bool(re.search(r"photo|image", " ".join(g("dc.type") + g("dc.format.medium")), re.I)),
    }


TITLE_RE = re.compile(r"Street Improvement Photographs -- Box\s+(\d+),\s+Folder\s+(\S+)\s+\((.*?)\)\s+--")
DATE_NAME_RE = re.compile(r"^(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d|^Unknown$|^\d{4}")


def folder_of(c, n):
    """(box, folder, name) of the Street Improvement item at handle n, or None
    when the handle is not an item of that series or its folder is named by
    date. Costs up to two requests; everything is cached."""
    loc = c.resolve_handle(HANDLE_PREFIX + str(n))
    if not loc.startswith("/items/"):
        return None
    st = D.state(c.get(D.HOST + loc))
    if st is None:
        return None
    for o in D.objects(st, "item"):
        m = TITLE_RE.search("; ".join(D.md(o, "dc.title")))
        if m and not DATE_NAME_RE.search(m.group(3).strip()):
            return int(m.group(1)), m.group(2), m.group(3).strip()
        break
    return None


def seek(c, name, lo, hi, unknown_is="hi", max_walk=40, log=print):
    """Find the folders whose name starts with `name` between handles lo and hi."""
    key = name.lower()
    hit = None
    # Batches of other boxes are interleaved in places. A probe that lands in a
    # lower-numbered box than the starting handle's is outside the alphabetical
    # run being searched, so it is treated like a page that is not a street folder.
    first = folder_of(c, lo)
    box_lo = first[0] if first else 0
    while hi - lo > 1:
        mid = (lo + hi) // 2
        f, n = None, mid
        for n in range(mid, min(mid + 3, hi)):  # step over a missing handle or two
            f = folder_of(c, n)
            if f and f[0] < box_lo:
                f = None
            if f:
                break
        if not f:
            log("  seek %s: %d not a street folder, taken as %s" % (name, mid, unknown_is))
            if unknown_is == "hi":
                hi = mid
            else:
                lo = min(mid + 2, hi)
            continue
        log("  seek %s: %d is Box %d, Folder %s (%s)" % (name, n, f[0], f[1], f[2]))
        fl = f[2].lower()
        if fl.startswith(key):
            hit = n
            break
        if fl < key:
            lo = n
        else:
            hi = mid
    if hit is None:
        log("  seek %s: no folder of that name found; search closed at handle %d" % (name, lo))
        return 0
    got = 1
    for step in (-1, 1):
        n, miss = hit + step, 0
        while got < max_walk and miss < 2:
            f = folder_of(c, n)
            if f is None:
                miss += 1
            elif f[2].lower().startswith(key):
                got, miss = got + 1, 0
            else:
                break
            n += step
    log("  seek %s: %d records around handle %d" % (name, got, hit))
    return got


def wanted(rec):
    """Probing lands on other collections of the repository (concert programs,
    registers, modern portraits). Keep the City Engineer photographs, and any
    other pre-1965 photograph fetched on purpose with --items."""
    if COMMUNITY in rec["collection"]:
        return True
    return rec.pop("_is_photo", False) and rec["year_min"] is not None and rec["year_min"] < 1965


def build_output(c, a, stop=""):
    """Rebuild the output from everything in the cache, so reruns accumulate."""
    recs, bad, missing, skipped = {}, 0, 0, 0
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
        if not wanted(rec):
            skipped += 1
            continue
        rec.pop("_is_photo", None)
        recs[rec["item_id"] or url] = rec
    for fn in sorted(os.listdir(a.raw)):  # item pages fetched directly, not via a handle
        if fn.startswith("drc_libraries_uc_edu_items_") and fn.endswith(".html"):
            text = open(os.path.join(a.raw, fn), encoding="utf-8", errors="replace").read()
            m = re.search(r'/server/api/core/items/([0-9a-f-]{36})/owningCollection', text)
            rec = record_from_page(text, D.HOST + "/items/" + m.group(1)) if m else None
            if rec and (rec["item_id"] or rec["page_url"]) not in recs and wanted(rec):
                rec.pop("_is_photo", None)
                recs[rec["item_id"] or rec["page_url"]] = rec
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)

    def hkey(k):
        m = re.search(r"/(\d+)$", k)
        return int(m.group(1)) if m else 0

    tmp = a.out + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        for k in sorted(recs, key=hkey):
            f.write(json.dumps(recs[k], ensure_ascii=False) + "\n")
    os.replace(tmp, a.out)
    rel = {}
    for r in recs.values():
        rel[r["relevance"]] = rel.get(r["relevance"], 0) + 1
    print("records: %d  by relevance: %s  pages without a public record: %d  handles whose page fetch failed: %d  "
          "items of other collections left out: %d  requests so far: %d%s"
          % (len(recs), rel, bad, missing, skipped, c.n_requests, ("  STOPPED: " + stop) if stop else ""), flush=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("out")
    ap.add_argument("--raw", required=True, help="cache folder for fetched pages")
    ap.add_argument("--probe-step", type=int, default=400, help="probe every Nth handle across the span (0 = no probing)")
    ap.add_argument("--span", default="%d-%d" % DEFAULT_SPAN)
    ap.add_argument("--ranges", default="", help="comma list of handle ranges a-b to walk in full")
    ap.add_argument("--seek", default="", help='comma list of NAME@LO-HI[:lo|:hi] folder searches, e.g. "Central Avenue@718381-718781"')
    ap.add_argument("--seek-max", type=int, default=40, help="most records to walk for one --seek name")
    ap.add_argument("--items", default="", help="comma list of item uuids to fetch directly (one request each)")
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
        for u in [x.strip() for x in a.items.split(",") if x.strip()]:
            if re.match(r"^[0-9a-f-]{36}$", u):
                c.get(D.HOST + "/items/" + u)
        if plan and a.seek:
            build_output(c, a)
        for spec in [x.strip() for x in a.seek.split(",") if x.strip()]:
            m = re.match(r"^(.*?)@(\d+)-(\d+)(?::(lo|hi))?$", spec)
            if not m:
                print("bad --seek entry: " + spec, flush=True)
                continue
            print("seek " + spec, flush=True)
            seek(c, m.group(1), int(m.group(2)), int(m.group(3)), m.group(4) or "hi", a.seek_max,
                 log=lambda t: print(t, flush=True))
            build_output(c, a)
    except D.Refused as e:
        stop = str(e)
    build_output(c, a, stop)


if __name__ == "__main__":
    main()
