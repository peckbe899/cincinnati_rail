"""Polite cached fetcher for drc.libraries.uc.edu (UC Libraries DSpace repository).

Rules built in: robots.txt is read first and obeyed (it disallows the REST API
except /server/api/core/bitstreams, the OAI endpoint, /search and /browse, and
asks for a 10 second crawl delay), honest generic User-Agent, GET only, never
parallel, stop for good on 401/403/429 or a challenge page, hard cap on
requests per run. Every response is cached on disk so nothing is fetched twice.

The public pages are server rendered and carry the page's data as JSON in a
<script id="dspace-angular-state"> block; state() returns that JSON.
"""
import hashlib
import json
import os
import re
import time
import urllib.error
import urllib.request
import urllib.robotparser

UA = "research-catalogue-script/0.1"
HOST = "https://drc.libraries.uc.edu"
STATE_RE = re.compile(r'<script id="dspace-angular-state" type="application/json">(.*?)</script>', re.S)


class Refused(Exception):
    pass


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *a, **k):
        return None


class DrcClient:
    def __init__(self, raw_dir, delay=10.0, cap=1200, offline=False):
        self.raw_dir = raw_dir
        os.makedirs(raw_dir, exist_ok=True)
        self.delay = max(delay, 3.0)
        self.cap = cap
        # the request count persists across runs so the per-host cap holds overall
        self.count_path = os.path.join(raw_dir, "requests_made.txt")
        try:
            self.n_requests = int(open(self.count_path).read().strip())
        except (OSError, ValueError):
            self.n_requests = 0
        self.last = 0.0
        self.stopped = ""
        self.login_run = 0  # item pages in a row that showed a log-in form instead of the record
        self.offline = offline
        self.robots = urllib.robotparser.RobotFileParser()
        rp = os.path.join(raw_dir, "robots.txt")
        if os.path.exists(rp):
            body = open(rp).read()
        elif offline:
            raise Refused("offline and no cached robots.txt")
        else:
            body = self._raw_get(HOST + "/robots.txt").decode("utf-8", "replace")
            with open(rp, "w") as f:
                f.write(body)
        self.robots.parse(body.splitlines())
        cd = self.robots.crawl_delay(UA)
        if cd and float(cd) > self.delay:
            self.delay = float(cd)

    def _raw_get(self, url, follow=True):
        if self.n_requests >= self.cap:
            raise Refused("request cap reached")
        wait = self.delay - (time.time() - self.last)
        if wait > 0:
            time.sleep(wait)
        req = urllib.request.Request(url, headers={"User-Agent": UA}, method="GET")
        self.n_requests += 1
        with open(self.count_path, "w") as f:
            f.write(str(self.n_requests))
        opener = urllib.request.build_opener() if follow else urllib.request.build_opener(_NoRedirect)
        try:
            with opener.open(req, timeout=120) as r:
                return r.read()
        finally:
            self.last = time.time()

    def resolve_handle(self, handle):
        """Map a handle such as 2374.UC/730333 to its site path (/items/<uuid>,
        /collections/<uuid>, ...) from the 301 the site answers; "" when the
        handle does not exist. One request, cached."""
        p = os.path.join(self.raw_dir, "handle_" + re.sub(r"[^A-Za-z0-9]+", "_", handle) + ".txt")
        if os.path.exists(p):
            return open(p).read().strip()
        if self.stopped:
            raise Refused(self.stopped)
        if self.offline:
            return ""
        url = HOST + "/handle/" + handle
        if not self.allowed(url):
            raise Refused("robots.txt disallows " + url)
        loc = ""
        try:
            body = self._raw_get(url, follow=False)
            loc = "" if len(body) < 2000 else "RENDERED"
        except urllib.error.HTTPError as e:
            if e.code in (401, 403, 429):
                self.stopped = "HTTP %d from host at %s" % (e.code, url)
                raise Refused(self.stopped)
            if e.code in (301, 302, 303, 307, 308):
                loc = e.headers.get("Location", "")
            elif e.code >= 500:
                return ""  # not cached, may be retried on a later run
        except (urllib.error.URLError, OSError):
            return ""
        with open(p, "w") as f:
            f.write(loc)
        return loc

    def cache_path(self, url):
        name = re.sub(r"[^A-Za-z0-9]+", "_", url.split("//", 1)[1])[:120]
        return os.path.join(self.raw_dir, name + "_" + hashlib.sha1(url.encode()).hexdigest()[:8] + ".html")

    def allowed(self, url):
        return self.robots.can_fetch(UA, url)

    def get(self, url):
        """Return page text, or None on 404/5xx. Raises Refused to stop the run."""
        p = self.cache_path(url)
        if os.path.exists(p):
            with open(p, encoding="utf-8", errors="replace") as f:
                return f.read()
        if self.stopped:
            raise Refused(self.stopped)
        if self.offline:
            return None
        if not self.allowed(url):
            raise Refused("robots.txt disallows " + url)
        try:
            data = self._raw_get(url)
        except urllib.error.HTTPError as e:
            if e.code in (401, 403, 429):
                self.stopped = "HTTP %d from host at %s" % (e.code, url)
                raise Refused(self.stopped)
            return None
        except (urllib.error.URLError, OSError):
            return None
        text = data.decode("utf-8", "replace")
        low = text[:3000].lower()
        if "captcha" in low or "just a moment" in low or "access denied" in low:
            self.stopped = "challenge page at " + url
            raise Refused(self.stopped)
        with open(p, "w", encoding="utf-8") as f:
            f.write(text)
        # A single record that is not public renders a log-in form in place of
        # the record; that page is kept and reported. Three in a row is read as
        # the host declining this client, and the run stops.
        if "/items/" in url:
            st = state(text)
            if st is not None and not objects(st, "item"):
                self.login_run += 1
                if self.login_run >= 3:
                    self.stopped = "three item pages in a row came back without a public record, last " + url
                    raise Refused(self.stopped)
            else:
                self.login_run = 0
        return text


def state(text):
    """Parse the embedded page state; None when the page was not server rendered."""
    if not text:
        return None
    m = STATE_RE.search(text)
    if not m:
        return None
    t = m.group(1)
    for a, b in (("&q;", '"'), ("&s;", "'"), ("&l;", "<"), ("&g;", ">"), ("&a;", "&")):
        t = t.replace(a, b)
    try:
        return json.loads(t)
    except ValueError:
        return None


def objects(st, kind=None):
    """All DSpace objects (dicts with uuid and metadata) found in a page state."""
    out, seen = [], set()

    def walk(o):
        if isinstance(o, dict):
            if "uuid" in o and "metadata" in o and isinstance(o["metadata"], dict):
                if (kind is None or o.get("type") == kind) and o["uuid"] not in seen:
                    seen.add(o["uuid"])
                    out.append(o)
            for v in o.values():
                walk(v)
        elif isinstance(o, list):
            for v in o:
                walk(v)

    walk(st)
    return out


def md(obj, key):
    return [v.get("value", "") for v in obj.get("metadata", {}).get(key, []) if v.get("value")]
