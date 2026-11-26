"""Polite cached fetcher for www.loc.gov JSON API (shared by the LoC harvesters).

Rules built in: robots.txt is read first and obeyed, honest generic User-Agent,
GET only, one request every 6 seconds, never parallel, on HTTP 429 wait 60 s
once and stop if it repeats, stop for good on 401/403 or a non-JSON challenge
page, hard cap on requests per run. Every parsed response is cached on disk so
nothing is fetched twice.
"""
import hashlib
import http.client
import json
import os
import re
import time
import urllib.error
import urllib.request
import urllib.robotparser

UA = "research-catalogue-script/0.1"
HOST = "https://www.loc.gov"


class Refused(Exception):
    pass


class LocClient:
    def __init__(self, raw_dir, delay=6.0, cap=1200, offline=False):
        self.raw_dir = raw_dir
        os.makedirs(raw_dir, exist_ok=True)
        self.delay = max(delay, 6.0)
        self.cap = cap
        self.n_requests = 0
        self.last = 0.0
        self.had_429 = False
        self.stopped = ""
        self.robots = urllib.robotparser.RobotFileParser()
        self.offline = offline
        rp = os.path.join(raw_dir, "robots.txt")
        if offline and os.path.exists(rp):
            body = open(rp).read()
        elif offline:
            body = ""
        else:
            body = self._raw_get(HOST + "/robots.txt").decode("utf-8", "replace")
            with open(rp, "w") as f:
                f.write(body)
        self.robots.parse(body.splitlines())
        cd = self.robots.crawl_delay(UA)
        if cd and float(cd) > self.delay:
            self.delay = float(cd)

    def _raw_get(self, url):
        if self.n_requests >= self.cap:
            raise Refused("request cap reached")
        wait = self.delay - (time.time() - self.last)
        if wait > 0:
            time.sleep(wait)
        req = urllib.request.Request(url, headers={"User-Agent": UA}, method="GET")
        self.n_requests += 1
        try:
            with urllib.request.urlopen(req, timeout=90) as r:
                data = r.read()
        finally:
            self.last = time.time()
        return data

    def cache_path(self, url):
        name = re.sub(r"[^A-Za-z0-9]+", "_", url.split("//", 1)[1])[:120]
        return os.path.join(self.raw_dir, name + "_" + hashlib.sha1(url.encode()).hexdigest()[:8] + ".json")

    def get_json(self, url):
        """Return parsed JSON, or None if not found. Raises Refused to stop the run."""
        p = self.cache_path(url)
        if os.path.exists(p):
            with open(p) as f:
                return json.load(f)
        if self.stopped:
            raise Refused(self.stopped)
        if self.offline:
            raise Refused("offline mode: not in cache: " + url)
        if not self.robots.can_fetch(UA, url):
            raise Refused("robots.txt disallows " + url)
        data = None
        for attempt in (0, 1, 2):
            try:
                data = self._raw_get(url)
                break
            except urllib.error.HTTPError as e:
                if e.code == 429 and not self.had_429:
                    self.had_429 = True
                    time.sleep(60)
                    continue
                if e.code in (401, 403, 429):
                    self.stopped = "HTTP %d on %s" % (e.code, url)
                    raise Refused(self.stopped)
                if e.code == 404:
                    return None
                raise
            except (http.client.IncompleteRead, ConnectionError, TimeoutError, urllib.error.URLError):
                # transfer cut off mid-body: not a refusal, try again (max 2 retries)
                if attempt == 2:
                    raise
                continue
        if data is None:
            raise Refused("no answer from " + url)
        try:
            obj = json.loads(data)
        except ValueError:
            self.stopped = "non-JSON answer (possible challenge page) on " + url
            raise Refused(self.stopped)
        with open(p, "w") as f:
            json.dump(obj, f)
        return obj
