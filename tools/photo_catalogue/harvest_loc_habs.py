#!/usr/bin/env python3
"""Harvest Library of Congress HABS/HAER/HALS survey records for Cincinnati and
Hamilton County, Ohio, into the photo catalogue JSONL shape. Metadata and links
only: no image files are downloaded.

Usage:
    python3 harvest_loc_habs.py OUT.jsonl [--raw RAW_DIR] [--skip-host HOST ...]

Sources (all public, GET only):
  * https://www.loc.gov/collections/historic-american-buildings-landscapes-and-engineering-records/
    ?q=cincinnati&fo=json  (the loc.gov JSON API; /pictures/search is disallowed
    by robots.txt and is NOT used)
  * the "Photo Caption Page(s)" PDF of each survey on tile.loc.gov (it has an OCR
    text layer holding one caption per photograph).

Access rules built in: robots.txt is fetched and obeyed per host, an honest
generic User-Agent is sent, one request every 6 s on www.loc.gov and every 3 s
elsewhere, at most 1200 requests per host, and a host is dropped for the rest of
the run on 401/403, on a bot challenge, or on a second 429 (after one 60 s wait).
Every parsed response is cached under RAW_DIR so nothing is fetched twice.
RAW_DIR defaults to ../raw/loc_habs relative to the output file.
"""
import argparse
import json
import os
import re
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import urllib.robotparser

UA = "research-catalogue-script/0.1"
SOURCE = "loc_habs"
HOLDER = "Library of Congress, Prints and Photographs Division"
SEARCH = ("https://www.loc.gov/collections/historic-american-buildings-landscapes-and-"
          "engineering-records/?q=cincinnati&fo=json&c=100&sp={page}&at=results,pagination")
DELAY = {"www.loc.gov": 6.0}
DEFAULT_DELAY = 3.0
CAP = 1200

KEYS = ["source", "holder", "collection", "item_id", "call_number", "title", "caption",
        "creator", "date_text", "year_min", "year_max", "location_text", "street",
        "house_number", "cross_street", "landmark", "plot_or_project_number", "page_url",
        "image_url", "thumb_url", "rights_text", "view_type", "relevance", "notes"]

# Relevance by survey id, set by hand from the address in the HABS title
# (west_end = west of Central Avenue incl. both sides of Central, Dayton Street
# district, Union Terminal; downtown_west = downtown between Central and Vine;
# otr = Over-the-Rhine west of Vine). Anything not listed falls to the street rules
# below, then to "other".
RELEVANCE_BY_ID = {
    "oh0406": "otr",            # 112 Findlay Street
    "oh0167": "west_end",       # Eighth Street District: W. Eighth, John, W. Seventh
    "oh0459": "downtown_west",  # 413 West Eighth Street
    "oh0460": "downtown_west",  # 412-416 West Seventh Street
    "oh0214": "other",          # East Third Street
    "oh0266": "other",          # Third & Kilgour (east end of downtown)
}
WEST_END_STREETS = [
    "dayton street", "bank street", "freeman", "baymiller", "linn street", "cutter",
    "mound street", "john street", "smith street", "central avenue", "carr street",
    "harriet", "hopkins", "clark street", "richmond street", "kenyon", "barr street",
    "betts", "clinton street", "everett", "armory avenue", "wade street",
    "west liberty street", "lincoln park", "gest street", "dalton", "mclean",
    "george street", "longworth", "carlisle", "laurel homes", "lincoln court",
    "union terminal", "crosley field", "western avenue", "kenner street",
    "flint street", "ezzard charles",
]
DOWNTOWN_WEST_STREETS = [
    "plum street", "elm street", "race street", "west fifth street", "west fourth street",
    "west sixth street", "west seventh street", "west eighth street", "west ninth street",
    "west third street", "garfield place", "vine street", "plum streets",
]


class HostRefused(Exception):
    pass


class Fetcher:
    def __init__(self, raw_dir, skip_hosts=()):
        self.raw = raw_dir
        self.last = {}
        self.count = {}
        self.refused = {h: "skipped by --skip-host" for h in skip_hosts}
        self.robots = {}
        self.had_429 = set()
        self.log = []

    def _path(self, host, name):
        d = self.raw if host == "www.loc.gov" else os.path.join(self.raw, host.split(".")[0])
        os.makedirs(d, exist_ok=True)
        return os.path.join(d, name)

    def _http(self, url):
        host = urllib.parse.urlsplit(url).netloc
        if host in self.refused:
            raise HostRefused(f"{host}: {self.refused[host]}")
        if self.count.get(host, 0) >= CAP:
            self.refused[host] = "request cap reached"
            raise HostRefused(f"{host}: request cap reached")
        wait = DELAY.get(host, DEFAULT_DELAY) - (time.time() - self.last.get(host, 0))
        if wait > 0:
            time.sleep(wait)
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        self.count[host] = self.count.get(host, 0) + 1
        try:
            with urllib.request.urlopen(req, timeout=120) as r:
                body, status = r.read(), r.status
        except urllib.error.HTTPError as e:
            body, status = e.read(), e.code
        finally:
            self.last[host] = time.time()
        challenge = b"Just a moment" in body[:4000] or b"cf_chl" in body[:20000]
        if status == 429 and not challenge and host not in self.had_429:
            self.had_429.add(host)
            time.sleep(60)
            return self._http(url)
        if status in (401, 403, 429) or challenge:
            why = f"HTTP {status}" + (" with bot challenge" if challenge else "")
            self.refused[host] = why
            self.log.append(f"REFUSED {url} {why}")
            raise HostRefused(f"{host}: {why}")
        return status, body

    def allowed(self, url):
        host = urllib.parse.urlsplit(url).netloc
        if host not in self.robots:
            p = self._path(host, "robots.txt")
            if os.path.exists(p):
                text = open(p, "rb").read().decode("utf-8", "replace")
            else:
                status, body = self._http(f"https://{host}/robots.txt")
                text = body.decode("utf-8", "replace") if status == 200 else ""
                open(p, "wb").write(body if status == 200 else b"")
            if "<html" in text[:2000].lower():   # an HTML 404 page, i.e. no robots.txt
                text = ""
            rp = urllib.robotparser.RobotFileParser()
            rp.parse(text.splitlines())
            self.robots[host] = rp
        return self.robots[host].can_fetch(UA, url)

    def get(self, url, name):
        """Return cached bytes, or fetch politely. None if 404."""
        host = urllib.parse.urlsplit(url).netloc
        p = self._path(host, name)
        if os.path.exists(p) and os.path.getsize(p) > 0:
            return open(p, "rb").read()
        if host in self.refused:
            raise HostRefused(f"{host}: {self.refused[host]}")
        if not self.allowed(url):
            self.log.append(f"ROBOTS-DISALLOWED {url}")
            raise HostRefused(f"{host}: robots.txt disallows {url}")
        status, body = self._http(url)
        if status != 200:
            self.log.append(f"HTTP {status} {url}")
            return None
        open(p, "wb").write(body)
        return body


def clean(s):
    return re.sub(r"\s+", " ", s or "").strip()


def parse_title(title):
    """HABS titles read 'Name, address, [more], City, County, ST'."""
    parts = [p.strip() for p in title.split(", ")]
    core = parts[:-3] if len(parts) > 3 else parts[:1]
    landmark = street = house = cross = ""
    addr_re = re.compile(r"^(\d+[\d\-\s,&]*?)\s+((?:[NSEW]\.? |North |South |East |West )?[A-Z].*)$")

    def strip_paren(s):
        return clean(re.sub(r"\s*\([^)]*\)", "", s))
    addr = ""
    first = core[0] if core else ""
    if addr_re.match(strip_paren(first)) or re.search(r"\((House|Houses|Commercial Buildings?)\)$", first):
        addr = strip_paren(first)
        m = re.search(r"\(([^)]*)\)", first)
        landmark = ""
        extra = core[1:]
    else:
        rest = core[1:]
        pick = next((i for i, p in enumerate(rest) if addr_re.match(strip_paren(p))), None)
        if pick is None:
            pick = next((i for i, p in enumerate(rest)
                         if re.search(r"^(Bounded|Spanning)|Streets?\b|Avenues?\b|Road\b|Drive\b", p)), None)
        if pick is None:
            pick = 0 if rest else None
        addr = rest[pick] if pick is not None else ""
        while pick and re.search(r"& .*Streets$", addr) and len(rest[pick - 1].split()) <= 2:
            pick -= 1                      # 'West Eighth, John & West Seventh Streets'
            addr = ", ".join(rest[pick:pick + 2])
            rest = rest[:pick] + [addr] + rest[pick + 2:]
        landmark = ", ".join([first] + (rest[:pick] if pick else []))
        if addr.startswith(("Bounded", "Spanning")) or (pick is not None and not addr_re.match(strip_paren(addr))):
            addr = ", ".join(rest[pick:])
        extra = rest[pick + 1:] if pick is not None else []
    m = addr_re.match(addr)
    if m:
        house, street = clean(m.group(1)), clean(m.group(2))
    elif " & " in addr and "," not in addr and not addr.lower().startswith(("bounded", "spanning")):
        a, b = addr.split(" & ", 1)
        suffix = re.search(r"(Streets|Avenues)$", b)
        if suffix and not re.search(r"(Street|Avenue|Road|Alley|Place)$", a):
            a = a + " " + suffix.group(1)[:-1]
        street, cross = clean(a), clean(re.sub(r"(Street|Avenue)s$", r"\1", b))
    else:
        street = addr
    loc = ", ".join(core[1:] if landmark else core) or title
    return landmark, street, house, cross, loc, ", ".join(extra)


def relevance(sid, title):
    if sid in RELEVANCE_BY_ID:
        return RELEVANCE_BY_ID[sid]
    t = title.lower()
    if "hamilton county" not in t or ", cincinnati," not in t:
        return "other"
    if any(s in t for s in WEST_END_STREETS):
        return "west_end"
    if any(s in t for s in DOWNTOWN_WEST_STREETS):
        return "downtown_west"
    return "other"


def parse_captions(pdf_path, survey_no):
    """Read the OCR text of a HABS 'Index to Photographs' PDF.

    Returns ({photo_number: caption}, header text with photographer and date).
    A caption line starts with the survey number plus a running number, e.g.
    'OH-655-3   VIEW SOUTHEAST ...'. The OCR often garbles the prefix and the
    running number, so the line is recognised by the digits of the survey number
    near its start, and the running number falls back to the previous one plus 1.
    """
    try:
        text = subprocess.run(["pdftotext", "-layout", pdf_path, "-"], capture_output=True,
                              timeout=120).stdout.decode("utf-8", "replace")
    except (OSError, subprocess.SubprocessError):
        return {}, "", 0
    m = re.search(r"-(\d+)(?:-([A-Z]{1,2}))?\s*$", survey_no or "")
    if not m:
        return {}, "", 0
    num, letter = m.group(1), m.group(2)
    line_re = re.compile(r"^\s*\S{1,4}?%s\S?%s[-\s]?(.*)$" % (
        re.escape(num), (r"[-\s]?\S{1,3}?" if letter else "")))
    caps, cur, prev, heads, guessed = {}, None, 0, [], 0
    for line in text.splitlines():
        m = None if re.search(r"HA[BE][SR] No|HALS No", line) else line_re.match(line)
        if m:
            rest = m.group(1)
            sp = re.match(r"(\S*)\s{2,}(\S.*)$", rest) or re.match(r"(\d+)\s+(\S.*)$", rest)
            if sp:
                tok, body = sp.group(1), sp.group(2)
            else:
                w = re.search(r"[A-Za-z]{3,}", rest)
                tok, body = (rest[:w.start()], rest[w.start():]) if w else (rest, "")
            if re.fullmatch(r"\d{1,3}", tok.strip()):
                n = int(tok)
            else:
                n = prev + 1
                guessed += 1
            prev = n
            if n in caps or re.match(r"(through|thru|to)\b", body):
                cur = None
                continue
            cur = n
            caps[n] = clean(body)
        elif not line.strip():
            cur = None
        elif cur is not None and line.startswith("   ") and not re.search(r"HISTORIC AMERICAN|INDEX TO", line):
            caps[cur] = clean(caps[cur] + " " + line)
        else:
            cur = None
        if re.search(r"photograph(er|ed)\b", line, re.I) and not m and len(clean(line)) < 160:
            heads.append(clean(line))
    out = []
    for h in heads:
        if h not in out:
            out.append(h)
    return caps, " | ".join(out[:4]), guessed


def view_type(caption, kind):
    if kind == "sheet":
        return "drawing"
    c = caption.upper()
    if not c:
        return "unknown"
    if re.search(r"\bAERIAL\b", c):
        return "oblique_aerial"
    if re.search(r"PHOTOCOPY OF (A |AN )?(DRAWING|PLAN|MAP|ENGRAVING|LITHOGRAPH|BLUEPRINT)|\bPLAN OF\b", c):
        return "drawing"
    if re.search(r"\bEXTERIOR\b", c) and "INTERIOR" not in c:
        return "street_front"
    if re.search(r"\bINTERIOR\b|\bROOM\b|STAIR|\bHALL\b|ROTUNDA|CONCOURSE|\bLOBBY\b|FIREPLACE|MANTEL|CEILING|BASEMENT|\bFLOOR\b", c):
        return "interior"
    if re.search(r"\bDETAIL\b|CLOSE-?UP", c):
        return "detail"
    if re.search(r"STREETSCAPE|\bBLOCK OF\b|STREET SCENE|LOOKING (UP|DOWN|ALONG)|GENERAL VIEW|CONTEXT|ENVIRON", c):
        return "street_scene"
    if re.search(r"ELEVATION|FACADE|FRONT|EXTERIOR|\bSIDE\b|\bREAR\b|CORNER|\bVIEW\b|FROM (THE )?(NORTH|SOUTH|EAST|WEST)", c):
        return "street_front"
    return "unknown"


def years(text):
    ys = [int(y) for y in re.findall(r"\b(1[89]\d\d|20[0-2]\d)\b", text or "")]
    return (min(ys), max(ys)) if ys else (None, None)


def build_records(res, fetcher, stats):
    item = res.get("item", {})
    sid = item.get("control_number") or res["id"].rstrip("/").split("/")[-1]
    title = clean(res.get("title", ""))
    places = [p.get("title", "") for p in item.get("place", [])]
    in_area = any("Hamilton County" in p for p in places) or "Cincinnati, OH" in title
    if not in_area:
        stats["skipped_out_of_area"].append(f"{sid} {title}")
        return []
    aka = res.get("aka", [])
    ids = {"photos": [], "color": [], "sheet": []}
    for a in aka:
        m = re.search(r"/resource/hhh\.%s\.(photos|color|sheet)\.([0-9a-z]+)/?$" % re.escape(sid), a)
        if m and m.group(2) not in ids[m.group(1)]:
            ids[m.group(1)].append(m.group(2))
    for k in ids:
        ids[k].sort()
    notes_list = [clean(n) for n in item.get("notes", [])]
    survey_no = next((n.split(":", 1)[1].strip() for n in notes_list if n.startswith("Survey number")), "")
    bdates = next((n for n in notes_list if n.startswith("Building/structure dates")), "")
    signif = next((n for n in notes_list if n.startswith("Significance")), "")
    creators = "; ".join(clean(c.get("title", "") + (" (" + c["role"] + ")" if c.get("role") else ""))
                         for c in item.get("creators", []))
    photographers = "; ".join(clean(c.get("title", "")) for c in item.get("creators", [])
                              if "photographer" in (c.get("role") or ""))
    landmark, street, house, cross, loc, extra = parse_title(title)
    rel = relevance(sid, title)
    rights = clean(item.get("rights_information") or item.get("rights_advisory") or "")
    part_of = clean(item.get("part_of", "")) or "Historic American Buildings Survey/Historic American Engineering Record/Historic American Landscapes Survey"
    first_img = [u.split("#")[0] for u in res.get("image_url", [])]
    cap_url = next((u for u in item.get("resource_links", []) if u.endswith("cap.pdf")
                    and u.startswith("https://tile.loc.gov/")), "")
    data_url = next((u for u in item.get("resource_links", []) if u.endswith("data.pdf")), "")
    caps, head, cap_state, guessed = {}, "", "no caption PDF listed", 0
    if cap_url:
        try:
            body = fetcher.get(cap_url, f"{sid}cap.pdf")
            if body is None:
                cap_state = "caption PDF not found (HTTP error)"
            else:
                path = fetcher._path("tile.loc.gov", f"{sid}cap.pdf")
                caps, head, guessed = parse_captions(path, survey_no)
                cap_state = f"caption PDF parsed, {len(caps)} captions" if caps else "caption PDF has no parsable text"
        except HostRefused as e:
            cap_state = f"caption PDF not fetched ({e})"
    stats["cap_states"][cap_state.split(",")[0].split(" (")[0]] = stats["cap_states"].get(cap_state.split(",")[0].split(" (")[0], 0) + 1
    base = ""
    for u in first_img:
        m = re.match(r"(https://tile\.loc\.gov/storage-services/service/pnp/habshaer/.+/)(photos|color|sheet)/(\w+?)(_150px|r|v)\.jpg$", u)
        if m:
            base = m.group(1)
            if m.group(2) == "photos" and not ids["photos"]:
                ids["photos"].append(m.group(3))   # single-photo survey: id only in the image URL
    img_dir = base + "photos/" if base else ""
    photo_ids = ids["photos"]
    # Photo ids are consecutive scan numbers in index order. Caption number k is
    # given to the photo whose id is (first id + k - 1), but only when the id span
    # equals the highest caption number, so a gap or an addendum cannot shift it.
    idnum = {pid: int(re.match(r"\d+", pid).group(0)) for pid in photo_ids if re.match(r"\d+", pid)}
    span = (max(idnum.values()) - min(idnum.values()) + 1) if idnum else 0
    top = max(caps) if caps else 0
    matched = bool(caps) and len(idnum) == len(photo_ids) and (
        span == top or (top - span == len(ids["color"]) > 0 and all(k in caps for k in range(1, span + 1))))
    if caps and not matched:
        stats["caption_count_mismatch"].append(
            f"{sid}: captions numbered up to {max(caps)} ({len(caps)} read) vs {len(photo_ids)} photos, id span {span}")
    date_text = head
    y0, y1 = years(re.sub(r"HABS|HAER|No\.\s*\S+", "", head))
    base_notes = [f"Survey {survey_no}" if survey_no else "", bdates,
                  f"Medium: {clean(item.get('medium_brief', ''))}",
                  f"Caption index PDF: {cap_url}" if cap_url else "",
                  f"Data pages PDF: {data_url}" if data_url else ""]

    def rec(**kw):
        r = {k: "" for k in KEYS}
        r.update(year_min=None, year_max=None, source=SOURCE, holder=HOLDER, collection=part_of,
                 call_number=clean(item.get("call_number", "")), title=title, creator=creators,
                 location_text=title, street=street, house_number=house, cross_street=cross,
                 landmark=landmark, rights_text=rights[:300], relevance=rel)
        r.update(kw)
        return r

    out = []
    if not any(ids.values()):
        out.append(rec(item_id=sid, page_url=f"https://www.loc.gov/pictures/item/{sid}/",
                       image_url=first_img[-1] if first_img else "", thumb_url=first_img[0] if first_img else "",
                       caption=signif[:600], view_type="unknown", date_text=date_text, year_min=y0, year_max=y1,
                       notes="; ".join([n for n in base_notes if n] + ["One record for the whole survey: the search result lists no individual photo ids"])))
        return out
    for kind in ("photos", "color", "sheet"):
        for i, pid in enumerate(ids[kind]):
            cap, capno = "", ""
            notes = [n for n in base_notes if n]
            if kind == "photos":
                notes.append(f"Photo {i + 1} of {len(photo_ids)} in id order")
                k = idnum[pid] - min(idnum.values()) + 1 if matched else None
                if matched and k in caps:
                    cap = caps[k]
                    notes.append(f"Caption {survey_no.replace('HABS ', '').replace('HAER ', '')}-{k} from the OCR text of the index PDF, matched by scan-number order; check against the image"
                                 + (" (OCR of caption numbers was poor in this index)" if guessed else ""))
                    mdir = re.search(r"(?:VIEW|LOOKING|FACING|CAMERA FACING)\s+(?:TO(?:WARDS?)?\s+(?:THE\s+)?)?((?:NORTH|SOUTH|EAST|WEST)[- ]?(?:NORTH|SOUTH|EAST|WEST)?(?:EAST|WEST)?)|FROM (?:THE )?((?:NORTH|SOUTH|EAST|WEST)(?:EAST|WEST)?)", cap.upper())
                    if mdir:
                        notes.append("Direction phrase in caption: " + clean(mdir.group(0)))
                elif matched:
                    notes.append("Caption not assigned: this photo's caption line was not read from the index PDF")
                elif caps:
                    notes.append(f"Caption not assigned: index numbering (up to {max(caps)}) does not line up with the {len(photo_ids)} photo ids; read the caption PDF")
                else:
                    notes.append("Caption not assigned: " + cap_state)
            elif kind == "sheet":
                notes.append(f"Measured drawing sheet {i + 1} of {len(ids['sheet'])}")
            else:
                notes.append(f"Colour transparency {i + 1} of {len(ids['color'])}")
            image = thumb = ""
            if kind == "photos" and img_dir:
                image, thumb = f"{img_dir}{pid}v.jpg", f"{img_dir}{pid}_150px.jpg"
                if not any(u.endswith(f"/photos/{pid}v.jpg") for u in first_img):
                    notes.append("image_url and thumb_url built from the survey's first photo URL pattern, not individually checked")
            loc_text = title + (" | " + cap if cap else "")
            out.append(rec(item_id=f"hhh.{sid}.{kind}.{pid}",
                           page_url=f"https://www.loc.gov/resource/hhh.{sid}.{kind}.{pid}/",
                           image_url=image, thumb_url=thumb, caption=cap[:600],
                           creator=creators, date_text=date_text, year_min=y0, year_max=y1,
                           location_text=loc_text, view_type=view_type(cap, kind),
                           notes="; ".join(notes)))
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("out")
    ap.add_argument("--raw", default=None, help="cache folder (default: ../raw/loc_habs beside OUT)")
    ap.add_argument("--skip-host", action="append", default=[],
                    help="do not contact this host (cached responses are still used)")
    a = ap.parse_args()
    out = os.path.abspath(a.out)
    raw = a.raw or os.path.join(os.path.dirname(os.path.dirname(out)), "raw", SOURCE)
    os.makedirs(raw, exist_ok=True)
    os.makedirs(os.path.dirname(out), exist_ok=True)
    f = Fetcher(raw, a.skip_host)
    stats = {"skipped_out_of_area": [], "cap_states": {}, "caption_count_mismatch": [],
             "search_total_claimed": None, "search_results_read": 0, "search_pages_missing": []}
    results, page, pages = [], 1, 1
    while page <= pages:
        try:
            body = f.get(SEARCH.format(page=page), f"coll_p{page}.json")
        except HostRefused as e:
            stats["search_pages_missing"].append(f"page {page}: {e}")
            page += 1
            continue
        if body is None:
            stats["search_pages_missing"].append(f"page {page}: HTTP error")
            page += 1
            continue
        d = json.loads(body)
        pages = d["pagination"]["total"]
        stats["search_total_claimed"] = d["pagination"]["of"]
        results += d["results"]
        page += 1
    stats["search_results_read"] = len(results)
    n = 0
    with open(out, "w", encoding="utf-8") as fh:
        for res in results:
            for r in build_records(res, f, stats):
                fh.write(json.dumps({k: r[k] for k in KEYS}, ensure_ascii=False) + "\n")
                n += 1
    stats.update(records_written=n, requests=f.count, refused_hosts=f.refused, log=f.log)
    json.dump(stats, open(os.path.join(raw, "run_stats.json"), "w"), indent=1)
    print(json.dumps(stats, indent=1), file=sys.stderr)


if __name__ == "__main__":
    main()
