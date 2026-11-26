#!/usr/bin/env python3
"""Cincinnati Museum Center, photograph collections other than Kenyon-Barr.

Usage: harvest_cmc_other.py OUTPUT.jsonl [--raw RAW_DIR]

Access rules built in: robots.txt is read first for each host and obeyed
(including Crawl-delay), GET only, plain honest User-Agent, at least 3 s
between requests per host, a host is dropped on 401/403/429.

State when written (2026-11-26): searchcollections.cincymuseum.org/robots.txt
is "User-agent: * / Disallow: /". The online catalogue is therefore NOT
harvested, and this script never requests anything from it except robots.txt.
It re-checks on every run and says so if that ever changes (no catalogue
parser exists, because no catalogue page has been read by machine).

What is written instead, from the museum's own public website
(www.cincymuseum.org, robots.txt allows it, Crawl-delay 10):
  1. ITEM rows: photographs the museum reproduced in its blog posts with a
     caption or credit. Each row is written only if the image file name and
     the caption text are both still found on the page.
  2. COLLECTION rows: one pointer per named photograph collection described
     on the museum's pages, with the museum's own wording. These are not
     items; item_id starts with "collection:".
Relevance and view type of ITEM rows were set by hand from the caption; where
the caption gives no place, the notes field says so.
"""
import argparse, html, json, os, re, sys, time, urllib.request, urllib.error, urllib.robotparser

UA = "research-catalogue-script/0.1"
WWW = "www.cincymuseum.org"
CAT = "searchcollections.cincymuseum.org"
CATALOGUE = "https://%s/public/museum/Portal/Combined.aspx" % CAT
MIN_DELAY = 3.0
HOLDER = "Cincinnati Museum Center, Cincinnati History Library and Archives"
_last, _stopped, _delay = {}, set(), {}

def get(host, path, raw_dir):
    if host in _stopped:
        return None
    name = (path.strip("/").replace("/", "_") or "index") + ("" if path.endswith(".txt") else ".html")
    if path == "/robots.txt":
        name = "robots_%s.txt" % host
    fn = os.path.join(raw_dir, name) if raw_dir else None
    if fn and os.path.exists(fn):
        return open(fn, encoding="utf-8", errors="replace").read()
    wait = _last.get(host, 0) + max(MIN_DELAY, _delay.get(host, 0)) - time.time()
    if wait > 0:
        time.sleep(wait)
    try:
        req = urllib.request.Request("https://%s%s" % (host, path), headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=60) as r:
            text = r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        _last[host] = time.time()
        print("HTTP %s %s%s" % (e.code, host, path), file=sys.stderr)
        if e.code in (401, 403, 429):
            _stopped.add(host)
            print("REFUSED by %s: host dropped" % host, file=sys.stderr)
        return None
    except Exception as e:
        _last[host] = time.time()
        print("FAILED %s%s: %s" % (host, path, e), file=sys.stderr)
        return None
    _last[host] = time.time()
    if fn:
        with open(fn, "w", encoding="utf-8") as f:
            f.write(text)
    return text

def robots(host, raw_dir):
    text = get(host, "/robots.txt", raw_dir)
    rp = urllib.robotparser.RobotFileParser()
    if text is None:                       # unreadable robots: treat as closed
        rp.parse(["User-agent: *", "Disallow: /"])
        return rp
    lines = text.splitlines()
    for l in lines:                        # Crawl-delay may sit outside any group
        m = re.match(r"(?i)crawl-delay:\s*([\d.]+)", l.strip())
        if m:
            _delay[host] = max(_delay.get(host, 0), float(m.group(1)))
    rp.parse(lines)
    return rp

def page_lines(t):
    """Visible text lines of a page, with each <img> turned into '[IMG src]'."""
    t = re.sub(r"(?s)<(script|style|noscript).*?</\1>", "", t)
    t = re.sub(r'<img[^>]*?src="([^"]+)"[^>]*>', lambda m: "\n[IMG %s]\n" % m.group(1), t)
    x = html.unescape(re.sub(r"<[^>]+>", "\n", t))
    return [re.sub(r"\s+", " ", l).strip() for l in x.split("\n") if l.strip()]

def rec(**kw):
    r = {"source": "cmc_other", "holder": HOLDER, "collection": "", "item_id": "", "call_number": "",
         "title": "", "caption": "", "creator": "", "date_text": "", "year_min": None, "year_max": None,
         "location_text": "", "street": "", "house_number": "", "cross_street": "", "landmark": "",
         "plot_or_project_number": "", "page_url": "", "image_url": "", "thumb_url": "",
         "rights_text": "", "view_type": "unknown", "relevance": "other", "notes": ""}
    r.update(kw)
    return r

NOLOC = "Caption gives no address. "
SEEN = "Image not viewed; view type set from the caption only. "
P_UT = "/2019/03/14/portal-to-the-world-cincinnati-celebrates-its-new-railroad-terminal/"
P_LI = "/2020/05/20/the-queen-city-welcomes-charles-lindbergh-and-his-spirit-of-st-louis-august-6-1927/"
P_FF = "/2023/02/27/fashion-frocks/"
P_KO = "/2019/12/27/the-poetry-of-felix-j-koch-exhibition/"
P_BR = "/2020/05/05/a-snapshot-of-early-cincinnati-breweries/"
GPF = "General Photograph files: Breweries"
# (page, image file name, caption text that must follow the image, record fields)
ITEMS = [
 (P_UT, "New_Image_2-1000px.jpg", "Cincinnati Union Terminal, c.1933.",
  dict(collection="", date_text="c.1933", year_min=1933, year_max=1933, location_text="Cincinnati Union Terminal",
       landmark="Cincinnati Union Terminal", relevance="west_end", notes=SEEN + "No collection or call number printed.")),
 (P_LI, "CharlesLindbergh-7.jpg", "at Redland Field, August 6, 1927. CMC Photograph Collection",
  dict(title="Lindbergh (third from right on platform) at Redland Field, August 6, 1927", collection="CMC Photograph Collection", date_text="August 6, 1927", year_min=1927, year_max=1927,
       location_text="Redland Field", landmark="Redland Field (later Crosley Field)", view_type="people",
       relevance="west_end", notes=SEEN + "A crowd event on a platform in the ballpark.")),
 (P_LI, "CharlesLindbergh-8.jpg", "Postcard of the Hotel Sinton at Fourth and Vine Streets. CMC Photograph Collection.",
  dict(collection="CMC Photograph Collection", location_text="Hotel Sinton at Fourth and Vine Streets",
       street="Fourth Street", cross_street="Vine Street", landmark="Hotel Sinton", relevance="other",
       notes=SEEN + "Undated postcard. The hotel stood on the east side of Vine, so it is marked other, "
             "but the view may include the Vine Street wall.")),
 (P_FF, "Oesterlein_building-1000px.jpg",
  "The Oesterlein Machine Company, 3301 Colerain Avenue, 1930. Cincinnati Museum Center. SC#296. Rombach & Groene Collection: item 1800.",
  dict(collection="Rombach & Groene Collection", item_id="SC#296 item 1800", call_number="SC#296",
       creator="Rombach & Groene", date_text="1930", year_min=1930, year_max=1930,
       location_text="3301 Colerain Avenue", street="Colerain Avenue", house_number="3301",
       landmark="The Oesterlein Machine Company", relevance="other",
       notes=SEEN + "Shows how a Rombach & Groene citation is written: SC#296, item <number>.")),
 (P_KO, "SC116_B2_B00261-w.jpg", 'Title: "Hearne Avenue, Avondale, May 1916"',
  dict(collection="Felix J. Koch Collection", call_number="SC 116", creator="Felix J. Koch", date_text="May 1916",
       year_min=1916, year_max=1916, location_text="Hearne Avenue, Avondale", street="Hearne Avenue",
       relevance="other", notes=SEEN + "Item number not printed; the image file name is SC116_B2_B00261-w.jpg.")),
 (P_KO, "SC116_116_114B_2520-w.jpg", 'Title: "Celtic Dance at May Day Celebration May 1921"',
  dict(collection="Felix J. Koch Collection", call_number="SC 116", creator="Felix J. Koch", date_text="May 1921",
       year_min=1921, year_max=1921, view_type="people", relevance="other",
       notes=NOLOC + "Item number not printed; the image file name is SC116_116_114B_2520-w.jpg.")),
 (P_KO, "SC116_51C_3272-w.jpg", 'Title: "Walnut Hills, January 2, 1921"',
  dict(collection="Felix J. Koch Collection", call_number="SC 116", creator="Felix J. Koch",
       date_text="January 2, 1921", year_min=1921, year_max=1921, location_text="Walnut Hills", relevance="other",
       notes=SEEN + "Item number not printed; the image file name is SC116_51C_3272-w.jpg.")),
 (P_KO, "SC116_49D_5050-w.jpg", "Title: \"Felix Koch on Porch of Craven's Boarding House, Clifton Ave., Sept. 1922\"",
  dict(collection="Felix J. Koch Collection", call_number="SC 116", creator="Felix J. Koch", date_text="Sept. 1922",
       year_min=1922, year_max=1922, location_text="Craven's Boarding House, Clifton Ave.", street="Clifton Avenue",
       landmark="Craven's Boarding House", view_type="people", relevance="other",
       notes=SEEN + "Item number not printed; the image file name is SC116_49D_5050-w.jpg.")),
]
for _n, _cap, _kw in [
 (2, "Jackson Brewery workers, ca. 1870.", dict(date_text="ca. 1870", year_min=1865, year_max=1875,
      landmark="Jackson Brewery", view_type="people", relevance="otr",
      notes=NOLOC + "Relevance otr is the cataloguer's assumption (Jackson Brewery stood in the Mohawk area of Over-the-Rhine); verify.")),
 (5, "Herancourt delivery wagon, n.d.", dict(date_text="n.d.", landmark="Herancourt brewery", notes=NOLOC)),
 (6, "Cold Storage, n.d.", dict(date_text="n.d.", view_type="interior", notes=NOLOC + "Brewery not named.")),
 (7, "Eagle Brewery, n.d.", dict(date_text="n.d.", landmark="Eagle Brewery", notes=NOLOC + SEEN)),
 (9, "Gerke Brewing employees, n.d.", dict(date_text="n.d.", landmark="Gerke Brewing", view_type="people", notes=NOLOC)),
 (11, "The Christian Moerlein Brewing Co., n.d.", dict(date_text="n.d.", landmark="The Christian Moerlein Brewing Co.",
      relevance="otr", notes=NOLOC + SEEN + "Relevance otr is the cataloguer's assumption (Moerlein brewery, Elm Street, Over-the-Rhine); verify.")),
 (12, "Moerlein Brewing smoke stack, n.d.", dict(date_text="n.d.", landmark="Moerlein Brewing", view_type="detail",
      relevance="otr", notes=NOLOC + "Relevance otr is the cataloguer's assumption; verify.")),
 (13, "Hauck Brewing Barrel Dept., n.d.", dict(date_text="n.d.", landmark="Hauck Brewing", relevance="west_end",
      notes=NOLOC + SEEN + "Relevance west_end is the cataloguer's assumption (John Hauck brewery, Dayton Street); verify.")),
 (14, "Hauck Brewing Grainery, n.d.", dict(date_text="n.d.", landmark="Hauck Brewing", relevance="west_end",
      notes=NOLOC + SEEN + "Relevance west_end is the cataloguer's assumption (John Hauck brewery, Dayton Street); verify.")),
 (15, "Hauck Brewing Interior Vats, n.d.", dict(date_text="n.d.", landmark="Hauck Brewing", view_type="interior",
      relevance="west_end", notes=NOLOC + "Relevance west_end is the cataloguer's assumption (John Hauck brewery, Dayton Street); verify.")),
]:
    ITEMS.append((P_BR, "Beer-%d.png" % _n, _cap, dict(collection=GPF, call_number=GPF, **_kw)))

P_PF = "/photograph-film/"
PTR = "COLLECTION-LEVEL POINTER, not an item. Items are in the museum catalogue, which robots.txt closes to scripts. "
# (page, phrase that must be on the page, record fields)
COLLECTIONS = [
 (P_PF, "West End Architectural Collection (over 3,500 architectural details of West End buildings plus 2,000 other photographs by George Rosenthal)",
  dict(item_id="collection:west-end-architectural", collection="West End Architectural Collection (George S. Rosenthal)",
       creator="George S. Rosenthal", location_text="West End", view_type="detail", relevance="west_end",
       notes=PTR + "Dates 1957 to 1959 come from press coverage, not this page. Call number not found. "
             "Not named among the collections the page lists as online.")),
 (P_PF, "Paul Briol Collection (over 6,000 8x10 negatives by Paul Briol",
  dict(item_id="collection:paul-briol", collection="Paul Briol Collection", creator="Paul Briol",
       date_text="1940s and 50s (photo assignments)", relevance="other",
       notes=PTR + "Call number not found. Not named among the collections the page lists as online.")),
 (P_PF, "Danny Ransohoff Collection (Danny Ransohoff’s 30,000 prints and negatives",
  dict(item_id="collection:danny-ransohoff", collection="Danny Ransohoff Collection", creator="Danny Ransohoff",
       date_text="1930s to 1980s", year_min=1930, year_max=1989, view_type="people", relevance="other",
       notes=PTR + "Social conditions and relief agencies; likely to include West End housing but the page does not say so. "
             "Call number not found. Not named among the collections the page lists as online.")),
 (P_PF, "Rombach and Groene",
  dict(item_id="collection:SC#296", collection="Rombach & Groene Collection", call_number="SC#296",
       creator="Rombach & Groene", relevance="other",
       notes=PTR + "Named on the page as having images online. Call number SC#296 is from the museum's Fashion Frocks blog post.")),
 (P_PF, "Lodder-Watson",
  dict(item_id="collection:lodder-watson", collection="Lodder-Watson Collection", relevance="other",
       notes=PTR + "Named on the page as having images online. Subject, dates and call number not stated.")),
 (P_KO, "Felix J. Koch Collection (SC 116). This treasure trove of 5,238 negatives document Cincinnati and the surrounding area between 1902 and 1933",
  dict(item_id="collection:SC116", collection="Felix J. Koch Collection", call_number="SC 116", creator="Felix J. Koch",
       date_text="between 1902 and 1933", year_min=1902, year_max=1933, relevance="other",
       notes=PTR + "5,238 negatives, arranged by subject. How many are online is not stated.")),
]

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("output")
    ap.add_argument("--raw", default="", help="folder for saved responses (optional cache)")
    a = ap.parse_args()
    if a.raw:
        os.makedirs(a.raw, exist_ok=True)
    if robots(CAT, a.raw).can_fetch(UA, CATALOGUE):
        print("NOTE: %s robots.txt now ALLOWS the portal. No catalogue parser exists yet; "
              "nothing fetched from it. Extend this script." % CAT, file=sys.stderr)
    else:
        print("%s: robots.txt disallows the portal; catalogue not harvested." % CAT, file=sys.stderr)
    rp = robots(WWW, a.raw)
    pages, out, missing = {}, [], []

    def lines(path):
        if path not in pages:
            t = get(WWW, path, a.raw) if rp.can_fetch(UA, "https://%s%s" % (WWW, path)) else None
            pages[path] = page_lines(t) if t else None
        return pages[path]

    for path, img, cap, kw in ITEMS:
        L = lines(path)
        hit = None
        for i, l in enumerate(L or []):
            if l.startswith("[IMG ") and l[5:-1].endswith("/" + img):
                after = " ".join(x for x in L[i + 1:i + 6] if not x.startswith("[IMG "))
                if cap in after:
                    hit = (l[5:-1], after)
                break
        if not hit:
            missing.append("%s %s" % (path, img))
            continue
        src, after = hit
        full = after[:after.find(cap) + len(cap)].strip()
        url = "https://%s%s" % (WWW, path)
        kw = dict(kw)
        title = kw.pop("title", "") or re.sub(r'^Title: "?|"$', "", cap).split(". CMC Photograph")[0].split(". Cincinnati Museum Center")[0].rstrip(".")
        out.append(rec(title=title, caption=full[:600], page_url=url,
                       image_url=src if src.startswith("http") else "https://%s%s" % (WWW, src),
                       rights_text="No rights statement on the page. Credit as printed in the caption. "
                                   "Reproductions: ask the library (library@cincymuseum.org).",
                       **dict(kw, item_id=kw.get("item_id") or "web:" + img)))
    for path, phrase, kw in COLLECTIONS:
        L = lines(path)
        para = next((l for l in (L or []) if phrase in l), None)
        if para is None:
            joined = " ".join(L or [])
            if phrase in joined:
                i = joined.find(phrase)
                para = joined[max(0, i - 100):i + 500]
        if para is None:
            missing.append("%s [%s]" % (path, phrase[:40]))
            continue
        i = para.find(phrase)
        out.append(rec(title=kw["collection"], caption=para[max(0, i - 200):i + 400][:600],
                       page_url="https://%s%s" % (WWW, path),
                       rights_text="No rights statement on the page.", **kw))
    os.makedirs(os.path.dirname(os.path.abspath(a.output)), exist_ok=True)
    seen = set()
    with open(a.output, "w", encoding="utf-8") as f:
        for r in out:
            if r["item_id"] in seen:
                continue
            seen.add(r["item_id"])
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print("wrote %d records (%d item rows, %d collection pointers) to %s" % (
        len(seen), sum(1 for i in seen if not i.startswith("collection:")),
        sum(1 for i in seen if i.startswith("collection:")), a.output), file=sys.stderr)
    for m in missing:
        print("NOT FOUND on page, no record written: " + m, file=sys.stderr)

if __name__ == "__main__":
    main()
