#!/usr/bin/env python3
"""Cincinnati Museum Center, Kenyon-Barr collection (SC#115): catalogue harvest.

Usage: harvest_cmc_kenyon_barr.py OUTPUT.jsonl [--raw RAW_DIR]

Access rules built in: robots.txt is read first for each host and obeyed
(including Crawl-delay), GET only, honest User-Agent, at least 3 s between
requests per host, stop using a host on 401/403/429 or a robots disallow.

State when written (2026-11-26): searchcollections.cincymuseum.org/robots.txt
is "User-agent: * / Disallow: /", so the online catalogue is NOT harvested.
The script re-checks this on every run. If the museum ever opens the
catalogue to robots the script says so and stops, because the item-page
parser would then have to be written against pages nobody has yet been
allowed to read by machine.

What is written instead: the few Kenyon-Barr photographs whose address or
number is cited on public third-party pages (found by web search, listed in
SEED below, each with the citing page). These are pointers for a person to
look up in the catalogue, not catalogue records.
"""
import argparse, json, os, sys, time, urllib.request, urllib.error, urllib.robotparser
from urllib.parse import urlparse

UA = "research-catalogue-script/0.1"
CATALOGUE = "https://searchcollections.cincymuseum.org/public/museum/Portal/Combined.aspx"
INFO_PAGES = ["https://www.cincymuseum.org/photograph-film/"]
MIN_DELAY = 3.0
_last, _robots, _stopped = {}, {}, set()

def get(url, raw_dir, name):
    host = urlparse(url).netloc
    if host in _stopped:
        return None
    path = os.path.join(raw_dir, name) if raw_dir else None
    if path and os.path.exists(path):
        return open(path, encoding="utf-8", errors="replace").read()
    delay = MIN_DELAY
    rp = _robots.get(host)
    if rp and rp.crawl_delay(UA):
        delay = max(delay, float(rp.crawl_delay(UA)))
    wait = _last.get(host, 0) + delay - time.time()
    if wait > 0:
        time.sleep(wait)
    try:
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=60) as r:
            text = r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        _last[host] = time.time()
        if e.code in (401, 403, 429):
            _stopped.add(host)
            print("REFUSED %s by %s: host dropped" % (e.code, host), file=sys.stderr)
        return None
    _last[host] = time.time()
    if path:
        with open(path, "w", encoding="utf-8") as f:
            f.write(text)
    return text

def robots(host, raw_dir):
    text = get("https://%s/robots.txt" % host, raw_dir, "robots_%s.txt" % host)
    rp = urllib.robotparser.RobotFileParser()
    if text is None:            # unreadable robots: treat as closed
        rp.parse(["User-agent: *", "Disallow: /"])
    else:
        # the www host puts Crawl-delay before any User-agent line; honour it
        lines = text.splitlines()
        if any(l.lower().startswith("crawl-delay") for l in lines):
            d = [l for l in lines if l.lower().startswith("crawl-delay")][0]
            lines = ["User-agent: *", d] + lines
        rp.parse(lines)
    _robots[host] = rp
    return rp

RIGHTS = ("Credit line as printed by news users: 'Image from SC# 115 The Kenyon-Barr "
          "Collection; Provided Courtesy of the Cincinnati History Library and Archive, "
          "The Cincinnati Museum Center'. No rights statement read from the catalogue. "
          "Reproductions: reproductions@cincymuseum.org")
BASE = {"source": "cmc_kenyon_barr", "holder": "Cincinnati Museum Center, Cincinnati History Library and Archives",
        "collection": "Kenyon-Barr Collection", "item_id": "", "call_number": "SC#115", "title": "",
        "caption": "", "creator": "City of Cincinnati", "date_text": "1959", "year_min": 1959,
        "year_max": 1959, "location_text": "", "street": "", "house_number": "", "cross_street": "",
        "landmark": "", "plot_or_project_number": "", "page_url": "", "image_url": "", "thumb_url": "",
        "rights_text": RIGHTS, "view_type": "street_front", "relevance": "west_end", "notes": ""}
NOTE = ("SECONDARY CITATION, not a catalogue record: address and date taken from a caption on the "
        "citing page (page_url), found by web search. Item number, signboard number and catalogue "
        "URL not known. Look up in the museum catalogue by address.")
SEED = [
    {"title": "1067 Clark Street", "caption": "1067 Clark Street in 1959.", "location_text": "1067 Clark Street",
     "street": "Clark Street", "house_number": "1067",
     "page_url": "https://www.citybeat.com/news/echoes-of-a-lost-west-end-12219411", "notes": NOTE},
    {"title": "763 Barr Street", "caption": "763 Barr Street in 1959.", "location_text": "763 Barr Street",
     "street": "Barr Street", "house_number": "763",
     "page_url": "https://www.citybeat.com/news/echoes-of-a-lost-west-end-12219411", "notes": NOTE},
    {"title": "743-745 West Court Street",
     "caption": "743-745 West Court Street in Cincinnati's lower West End in 1959.",
     "location_text": "743-745 West Court Street; lower West End", "street": "West Court Street",
     "house_number": "743-745",
     "page_url": "https://www.wvxu.org/arts/2018-09-24/finding-kenyon-barr-and-cincinnatis-lost-lower-west-end",
     "notes": NOTE},
    {"item_id": "SC#115-1414", "call_number": "SC#115-1414", "date_text": "", "year_min": None, "year_max": None,
     "view_type": "unknown",
     "page_url": "https://cintimha.com/wp-content/uploads/2021/03/SOL-2021-4003-Reference-File-2-Historical-Neighborhood-Overview.pdf",
     "notes": "SECONDARY CITATION: a housing authority reference file cites a photograph as SC#115-1414. "
              "Subject and address not known from the search result. Shows the item number form "
              "SC#115-<number>. Date not confirmed."},
]

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("output")
    ap.add_argument("--raw", default="", help="folder for saved responses (optional cache)")
    a = ap.parse_args()
    if a.raw:
        os.makedirs(a.raw, exist_ok=True)
    chost = urlparse(CATALOGUE).netloc
    if robots(chost, a.raw).can_fetch(UA, CATALOGUE):
        print("NOTE: catalogue robots.txt now ALLOWS the portal. No parser exists yet; "
              "nothing fetched from it. Extend this script.", file=sys.stderr)
    else:
        print("catalogue host %s: robots.txt disallows the portal; not harvested." % chost, file=sys.stderr)
    for u in INFO_PAGES:
        h = urlparse(u).netloc
        if robots(h, a.raw).can_fetch(UA, u):
            t = get(u, a.raw, u.rstrip("/").rsplit("/", 1)[-1] + ".html")
            if t and "Kenyon-Barr" in t:
                print("info page read: %s (mentions Kenyon-Barr)" % u, file=sys.stderr)
    os.makedirs(os.path.dirname(os.path.abspath(a.output)), exist_ok=True)
    with open(a.output, "w", encoding="utf-8") as f:
        for s in SEED:
            f.write(json.dumps(dict(BASE, **s), ensure_ascii=False) + "\n")
    print("wrote %d secondary-citation records to %s" % (len(SEED), a.output), file=sys.stderr)

if __name__ == "__main__":
    main()
