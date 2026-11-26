#!/usr/bin/env python3
"""Harvest Library of Congress Prints & Photographs records for Cincinnati
(everything except HABS/HAER) into the photo catalogue JSONL shape.

Usage:
    python3 harvest_loc_other.py OUTPUT.jsonl [--raw-dir DIR] [--max-items N]

Route: the public loc.gov JSON API (https://www.loc.gov/apis/) on /photos/ and
/collections/<slug>/ with q=cincinnati&fo=json. /pictures/search is NOT used
because www.loc.gov/robots.txt disallows it. Metadata and links only; no image
is downloaded. Access rules live in loc_fetch.py (robots, 6 s delay, stop on
401/403/429, request cap, disk cache).
"""
import argparse
import json
import os
import re
import sys
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from loc_fetch import LocClient, Refused  # noqa: E402

SOURCE = "loc_other"
PAGE = "&fo=json&c=100&at=results,pagination"
QUERIES = [
    ("photos", "https://www.loc.gov/photos/?q=cincinnati"),
    ("fsa", "https://www.loc.gov/collections/fsa-owi-black-and-white-negatives/?q=cincinnati"),
    ("fsac", "https://www.loc.gov/collections/fsa-owi-color-photographs/?q=cincinnati"),
    ("det", "https://www.loc.gov/collections/detroit-publishing-company/?q=cincinnati"),
    ("pan", "https://www.loc.gov/collections/panoramic-photographs/?q=cincinnati"),
    ("stereo", "https://www.loc.gov/collections/stereograph-cards/?q=cincinnati"),
]

STREET_TYPES = r"(?:Streets?|St\.|Sts\.|Avenue|Ave\.|Road|Alley|Place|Court|Parkway|Pike|Boulevard|Blvd\.|Drive|Square|Way|Viaduct)"
ORD = r"(?:\d{1,2}(?:st|nd|rd|th)|First|Second|Third|Fourth|Fifth|Sixth|Seventh|Eighth|Ninth|Twelfth|Thirteenth|Fourteenth|Fifteenth)"
STREET_RE = re.compile(
    r"\b((?:(?:West|East|North|South|W\.|E\.|N\.|S\.)\s+)?(?:" + ORD + r"|[A-Z][a-zA-Z']+(?:\s+[A-Z][a-z]+)?)\s+" + STREET_TYPES + r")(?![a-z])")
HOUSE_RE = re.compile(
    r"\b(\d{2,4}(?:\s*-\s*\d{1,4})?)\s+((?:(?:West|East|North|South|W\.|E\.|N\.|S\.)\s+)?(?:" + ORD + r"|[A-Z][a-z]+)\s+" + STREET_TYPES + r")")
PAIR_RE = re.compile(
    r"\b(" + ORD + r"|[A-Z][a-z]+)\s+(?:and|&)\s+(" + ORD + r"|[A-Z][a-z]+)\s+(?:Streets|Sts\.|Avenues)")
NOT_STREET_FIRST = {"The", "A", "An", "On", "In", "At", "Of", "From", "Near", "Public", "Fountain", "Government",
                    "Main Public", "District", "Old", "Wabash", "City", "Queen City", "Supreme", "Juvenile", "Lytle", "Market", "This", "Looking", "Ohio.", "Ohio", "Cincinnati", "County", "O.", "Along", "Across", "Down", "Up"}

LANDMARKS = [
    "Union Terminal", "Crosley Field", "Redland Field", "Palace of the Fans", "League Park", "Laurel Homes",
    "Lincoln Court", "Music Hall", "Fountain Square", "Tyler Davidson Fountain", "Suspension Bridge",
    "Roebling", "Carew Tower", "City Hall", "Plum Street Temple", "St. Peter in Chains", "Court House",
    "Courthouse", "Central Union Depot", "Central Union Station", "Grand Central", "Public Landing", "Eden Park",
    "Findlay Market", "Post Office", "Chamber of Commerce", "Rookwood", "Zoological", "University of Cincinnati",
    "Longworth Hall", "Cincinnati Southern", "Union Central", "Gibson House", "Sinton", "Burnet House",
    "Grand Hotel", "Art Museum", "Government Square", "Washington Park", "Lincoln Park", "Garfield Place",
    "Mount Adams", "Mt. Adams", "Incline", "Public Library", "Ingalls Building", "Taft Museum", "Lytle Park",
    "Central Bridge", "Chesapeake and Ohio", "C. & O.", "Mill Creek", "Ohio River", "levee", "Levee",
    "Procter", "Ivorydale", "Greenhills", "Spring Grove", "Federal Building", "Emery", "Netherland",
    "Pennsylvania Station", "Little Miami", "Hughes High School", "General Hospital", "Workhouse",
    "St. Xavier", "Odd Fellows", "Masonic", "Y.M.C.A.", "Arcade", "Shillito", "Alms & Doepke", "Pogue",
    "Marine Hospital", "Coney Island", "Chester Park", "Lagoon", "Cincinnatus", "Riverfront Stadium",
]

WE_STREETS = ["Freeman", "Baymiller", "Linn", "Cutter", "Mound", "John", "Smith", "Carr", "Harriet", "Hopkins",
              "Clark", "Richmond", "Kenyon", "Barr", "Betts", "Clinton", "Everett", "Armory", "Wade", "Gest",
              "Dalton", "McLean", "George", "Longworth", "Carlisle", "Dayton", "Central", "Findlay", "Bank",
              "Poplar", "York", "Charlotte", "Flint", "David", "Hathaway", "Kossuth", "Oliver", "Western"]
WE_RE = re.compile(
    r"\b(?:" + "|".join(WE_STREETS) + r")\s+(?:Street|St\.|Avenue|Ave\.)|\bWest End\b|\bLaurel Homes\b|\bLincoln Court\b"
    r"|\bUnion Terminal\b|\bCrosley Field\b|\bRedland Field\b|\bPalace of the Fans\b|\bLincoln Park\b|\bKenyon-Barr\b"
    r"|\bQueensgate\b|\bMill ?[Cc]reek\b"
    r"|\bLongworth Hall\b|\bCentral Union (?:Depot|Station)\b|\bGrand Central (?:Depot|Station)\b|\bCincinnati Southern\b")
OTR_RE = re.compile(r"\bOver-the-Rhine\b|\bOver the Rhine\b|\bMusic Hall\b|\bFindlay Market\b|\bWashington Park\b"
                    r"|\b(?:Elm|Race|Pleasant|Republic|Green|Elder|McMicken|Mohawk)\s+(?:Street|St\.|Avenue)|\bcanal\b|\bCanal\b")
DT_RE = re.compile(r"\bFountain Square\b|\bTyler Davidson\b|\bCarew Tower\b|\bCity Hall\b|\bPlum Street\b|\bSt\. Peter in Chains\b"
                   r"|\b(?:Race|Elm|Plum|Vine)\s+(?:Street|St\.)|\b(?:Fourth|Fifth|Sixth|Seventh|Third|4th|5th|6th|7th|3rd)\s+(?:Street|St\.)"
                   r"|\bGarfield Place\b|\bShillito|\bArcade\b|\bNetherland\b|\bSinton\b|\bGibson House\b|\bBurnet House\b|\bGrand Hotel\b"
                   r"|\bCourt\s+(?:Street|St\.)|\b(?:West|W\.)\s+" + ORD + r"\s+(?:Street|St\.)|\bSuspension Bridge\b|\bPublic Landing\b|\b[Ll]evee\b|\bChamber of Commerce\b|\bUnion Central\b")

DROP_PARTOF = ("historic american buildings survey", "historic american engineering record", "habs", "haer")
DROP_GROUP = ("baseball cards", "performing arts posters", "vaudeville", "cartoon", "veterans history",
              "american folklife center", "posters:", "yanker", "caricature")
PORTRAIT_RE = re.compile(r"portrait|cartoon|caricature|baseball cards|baseball players|political posters|sheet music|theatrical posters", re.I)


def as_list(v):
    if v is None:
        return []
    if isinstance(v, list):
        return v
    return [v]


def texts(v):
    out = []
    for x in as_list(v):
        if isinstance(x, dict):
            x = x.get("title") or ""
        if isinstance(x, str) and x.strip():
            out.append(x.strip())
    return out


def years(date_text, dates):
    ys = [int(y) for y in re.findall(r"(?<!\d)(1[5-9]\d\d|20[0-2]\d)(?!\d)", date_text or "")]
    if not ys:
        for d in as_list(dates):
            ys += [int(y) for y in re.findall(r"(?<!\d)(1[5-9]\d\d|20[0-2]\d)(?!\d)", str(d))]
    if not ys:
        m = re.search(r"(?<!\d)(1[5-9]\d)-(?!\d)", date_text or "")
        if m:
            return int(m.group(1)) * 10, int(m.group(1)) * 10 + 9
        return None, None
    return min(ys), max(ys)


def largest_image(urls):
    best, bw = "", -1
    for u in as_list(urls):
        if not isinstance(u, str):
            continue
        m = re.search(r"[#&]w=(\d+)", u)
        w = int(m.group(1)) if m else 0
        if w > bw:
            best, bw = u.split("#")[0], w
    return best, bw


def one(v):
    """Flatten a str-or-list field to one string."""
    return "; ".join(texts(v))


def select(r):
    """Return (keep, reason)."""
    it = r.get("item") or {}
    partof = " | ".join(as_list(r.get("partof"))).lower()
    if any(k in partof for k in DROP_PARTOF) or one(it.get("call_number")).startswith(("HABS", "HAER", "HALS")):
        return False, "habs_haer (other harvest)"
    states = [s.lower() for s in as_list(r.get("location_state"))]
    blob_place = " | ".join(texts(it.get("place")) + texts(it.get("subject_headings")) + as_list(r.get("location")))
    title = one(r.get("title")) or one(it.get("title"))
    if "iowa" in states and "ohio" not in states or re.search(r"Cincinnati,? Iowa|Iowa--Cincinnati", title + blob_place):
        return False, "cincinnati_iowa"
    place_signal = ("cincinnati" in [c.lower() for c in as_list(r.get("location_city"))]
                    or re.search(r"Ohio--(?:Hamilton County--)?Cincinnati|Cincinnati \(Ohio\)|Cincinnati--Ohio", blob_place)
                    or re.search(r"Cincinnati(?: \(vicinity\))?,? (?:Ohio|O\.|Oh\.)", title)
                    or re.search(r"\bCincinnati\b", title) and re.search(
                        r"street|bridge|river|levee|building|church|hotel|station|depot|park|view|skyline|panorama|"
                        r"square|fountain|hall|incline|market|wharf|landing|flood|housing|slum|house|school|factory|plant|"
                        r"bird's|hospital|cemetery|canal|terminal|field|club|zoo|garden|university|college|library", title, re.I))
    if not place_signal:
        return False, "no_cincinnati_place_signal"
    kinds = " | ".join(as_list(r.get("partof")) + texts(it.get("genre")) + texts(it.get("subject_headings"))
                       + texts(it.get("formats")))
    if any(k in partof for k in DROP_GROUP):
        return False, "portraits_posters_cartoons"
    if PORTRAIT_RE.search(kinds) and not re.search(r"street|building|cityscape|bridge|river|dwelling|housing|slum", kinds + title, re.I):
        return False, "portraits_posters_cartoons"
    return True, ""


def coll_hint(it):
    return one(it.get("part_of")) + one(it.get("source_collection"))


def view_type(kinds, title, has_house):
    k = (kinds + " | " + title)
    if re.search(r"\bmaps?\b|Sanborn", kinds, re.I):
        return "map"
    if re.search(r"aerial (?:photograph|view)", k, re.I):
        return "oblique_aerial"
    if re.search(r"panoram", k, re.I):
        return "panorama"
    if re.search(r"lithograph|engraving|drawing|woodcut|etching|chromolith|watercolor|bird's-eye|aquatint|architectural drawings|"
                 r"prints?--|\b1 print\b(?! *: *(?:gelatin|photographic|albumen))|posters?", k, re.I) and not re.search(
                 r"photographic print|photomechanical|negative|stereograph|gelatin|albumen|transparency", k, re.I):
        return "drawing"
    if re.search(r"\binteriors?\b|\bkitchen\b|\bbathroom\b|\bbedroom\b|\bceiling\b|\bmurals?\b", k, re.I):
        return "interior"
    if has_house:
        return "street_front"
    if re.search(r"\bstreets?\b|business district|cityscape|skyline|waterfront|levee|storefront|slum|housing|tenement|"
                 r"dwellings|row houses|alley|bridge|buildings|facade|plaza|square|city & town life", k, re.I):
        return "street_scene"
    if re.search(r"children|boys|girls|men\b|women|newsboy|workers|spectators|crowd|people|family|famil|employees|portrait", k, re.I):
        return "people"
    return "unknown"


def build(r, tag):
    it = r.get("item") or {}
    title = one(it.get("title")) or one(r.get("title"))
    notes_l = texts(it.get("notes"))
    summary = texts(it.get("summary"))
    subj = texts(it.get("subject_headings")) or texts(r.get("subject"))
    places = texts(it.get("place"))
    cap_parts = summary + [n for n in notes_l if not re.search(
        r"^Transfer;|More information about|^Temp\. note|^Film copy|digitiz|^Title (?:and other information )?from|"
        r"^Forms part of|^Gift;|^Purchase;|^Credit line|^This record contains unverified", n)]
    caption = " | ".join(cap_parts)[:600]
    blob = " . ".join([title] + summary + notes_l + subj)
    streets = []
    for m in STREET_RE.finditer(blob):
        s = m.group(1)
        first = s.split()[0]
        if "District Court" in s or first in NOT_STREET_FIRST or " ".join(s.split()[:2]) in NOT_STREET_FIRST:
            continue
        if s not in streets:
            streets.append(s)
    pair = PAIR_RE.search(blob)
    if pair:
        # "Fifth and Vine Sts." -> street "Fifth Street", cross street "Vine Street"
        streets = [x for x in streets if not x.startswith(pair.group(2) + " ")]
        for i, nm in enumerate((pair.group(1), pair.group(2))):
            streets = [x for x in streets if not x.startswith(nm + " ")]
            streets.insert(i, nm + " Street")
    hm = HOUSE_RE.search(blob)
    if hm and hm.group(2).split()[0] in NOT_STREET_FIRST:
        hm = None
    house = hm.group(1) if hm else ""
    if hm and hm.group(2) in streets:
        streets.remove(hm.group(2))
        streets.insert(0, hm.group(2))
    landmarks = []
    for lm in LANDMARKS:
        if re.search(r"(?<![A-Za-z])" + re.escape(lm), blob) and lm not in landmarks:
            landmarks.append(lm)
    loc_bits = []
    for x in places + as_list(r.get("location_str")) + [s for s in subj if re.search(r"Cincinnati|Ohio|Street|Avenue", s)] \
            + texts(it.get("location")):
        if x not in loc_bits:
            loc_bits.append(x)
    if re.search(r"Cincinnati|Ohio", title):
        loc_bits.append("title: " + title)
    date_text = one(it.get("date")) or one(it.get("created_published_date")) or one(r.get("date"))
    y0, y1 = years(date_text, r.get("dates") or it.get("sort_date"))
    img, w = largest_image(r.get("image_url"))
    if not img:
        img = one(it.get("service_medium"))
    thumb = one(it.get("service_low")) or one(it.get("thumb_gallery"))
    if not thumb and as_list(r.get("image_url")):
        thumb = as_list(r.get("image_url"))[0].split("#")[0]
    kinds = " | ".join(texts(it.get("genre")) + texts(it.get("formats")) + subj + texts(it.get("medium"))
                       + as_list(r.get("partof")))
    if WE_RE.search(blob):
        rel = "west_end"
    elif OTR_RE.search(blob):
        rel = "otr"
    elif DT_RE.search(blob):
        rel = "downtown_west"
    else:
        rel = "other"
    notes = []
    if w > 0:
        notes.append("largest listed derivative %d px wide" % w)
    if not r.get("digitized", True) or not img:
        notes.append("not digitized or no image served")
    if r.get("access_restricted"):
        notes.append("LoC flags access_restricted (larger images may display only on site)")
    if y0 and y0 >= 1965:
        notes.append("modern photograph (after 1965)")
    if rel != "west_end" and "farm security" in (kinds + coll_hint(it)).lower() and re.search(r"Mydans", blob + one(it.get("contributors"))) \
            and not re.search(r"Greenhills|Mariemont|suburb|outside|Subdivision|Laconia|Eastern Ave", blob):
        notes.append("candidate West End or basin housing (Mydans 1935 slum survey): caption does not place it in the "
                     "West End, needs visual or map placement")
    if hm and re.match(r"(?:West|W\.)\s", hm.group(2)) and int(re.match(r"\d+", house).group(0)) >= 400 and rel != "west_end":
        rel = "west_end"
        notes.append("west_end guessed from house number 400 or higher on a West numbered street (west of Central Avenue); check")
    elif rel == "west_end":
        m = WE_RE.search(blob)
        notes.append("west_end matched on: " + m.group(0))
    rn = one(it.get("reproduction_number"))
    if rn:
        notes.append("repro no: " + rn.replace("\n", "; ")[:160])
    lots = [p for p in as_list(r.get("partof")) if p.lower().startswith("lot ")]
    coll = one(it.get("part_of")) or one(it.get("source_collection"))
    if lots:
        coll = (coll + " [" + ", ".join(lots).upper() + "]").strip()
    cid = one(it.get("control_number")) or one(it.get("id")) or r.get("id", "").rstrip("/").split("/")[-1]
    return {
        "source": SOURCE,
        "holder": "Library of Congress, Prints and Photographs Division",
        "collection": coll,
        "item_id": str(cid),
        "call_number": one(it.get("call_number")),
        "title": title,
        "caption": caption,
        "creator": "; ".join(texts(it.get("creators")) or texts(it.get("contributors")) or texts(r.get("contributor"))),
        "date_text": date_text,
        "year_min": y0,
        "year_max": y1,
        "location_text": " | ".join(loc_bits),
        "street": streets[0] if streets else "",
        "house_number": house,
        "cross_street": "; ".join(streets[1:3]) if len(streets) > 1 else "",
        "landmark": "; ".join(landmarks[:4]),
        "plot_or_project_number": "",
        "page_url": (r.get("id") or r.get("url") or "").replace("http://", "https://"),
        "image_url": img,
        "thumb_url": thumb,
        "rights_text": (one(it.get("rights_advisory")) or one(it.get("rights_information")))[:240],
        "view_type": view_type(kinds, title, bool(house)),
        "relevance": rel,
        "notes": "; ".join(notes),
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("output")
    ap.add_argument("--raw-dir", default=None, help="cache folder for API responses (default: <output folder>/raw_loc_other)")
    ap.add_argument("--max-items", type=int, default=100, help="max item JSON reads for records lacking a date")
    ap.add_argument("--offline", action="store_true", help="build from cached responses only, make no request")
    a = ap.parse_args()
    raw = a.raw_dir or os.path.join(os.path.dirname(os.path.abspath(a.output)), "raw_loc_other")
    client = LocClient(raw, offline=a.offline)
    seen, recs, stats, claimed, problems = {}, [], Counter(), {}, []
    try:
        for tag, base in QUERIES:
            sp = 1
            while True:
                d = client.get_json(base + PAGE + "&sp=%d" % sp)
                if not d or "results" not in d:
                    problems.append("%s page %d: no results" % (tag, sp))
                    break
                claimed[tag] = d["pagination"].get("of")
                for r in d["results"]:
                    rid = r.get("id")
                    stats["seen_" + tag] += 1
                    if not rid or rid in seen:
                        continue
                    seen[rid] = tag
                    keep, why = select(r)
                    if not keep:
                        stats["dropped: " + why] += 1
                        continue
                    recs.append((r, tag))
                if not d["pagination"].get("next"):
                    break
                sp += 1
    except Refused as e:
        problems.append("STOPPED in query '%s' page %d: %s" % (tag, sp, e))
        client.stopped = client.stopped or str(e)
    out = []
    n_item = 0
    for r, tag in recs:
        rec = build(r, tag)
        if not rec["date_text"] and rec["year_min"] is None and n_item < a.max_items and not client.stopped:
            try:
                d = client.get_json(rec["page_url"] + "?fo=json&at=item")
                n_item += 1
                it = (d or {}).get("item") or {}
                if it:
                    r2 = dict(r)
                    merged = dict(r.get("item") or {})
                    for k, v in it.items():
                        if k not in merged or not merged[k]:
                            merged[k] = v
                    r2["item"] = merged
                    if it.get("date") and not r2.get("dates"):
                        r2["dates"] = [it["date"]]
                    rec = build(r2, tag)
                    rec["notes"] = (rec["notes"] + "; item JSON read").strip("; ")
            except Refused as e:
                problems.append("STOPPED on item read: %s" % e)
        out.append(rec)
    os.makedirs(os.path.dirname(os.path.abspath(a.output)), exist_ok=True)
    with open(a.output, "w") as f:
        for rec in out:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    rep = {"written": len(out), "unique_seen": len(seen), "claimed": claimed, "stats": dict(stats),
           "relevance": dict(Counter(x["relevance"] for x in out)), "view_type": dict(Counter(x["view_type"] for x in out)),
           "item_json_reads": n_item, "network_requests_this_run": client.n_requests, "problems": problems}
    print(json.dumps(rep, indent=1))


if __name__ == "__main__":
    main()
