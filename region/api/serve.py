"""``crhub serve``: start-up, serving and shutdown of the hub (decision 9.22). ``region/cli/serve.py`` is the
command; this module does the work, so tests can run a real server in a thread.

Start-up, in order (each step prints one line):

1. **Lock.** ``region.core.lock.acquire(var, port)``: a second serve, ``crhub jobs run`` or ``crhub restore`` in the
   same ``var`` makes this one exit with ``LockHeld``, naming the holder. The lock is held until shutdown.
2. **Database.** It must exist: serve never creates an empty one (``crhub setup`` does). A database outside
   ``var`` (``--db``, as the end-to-end tests use) has its folder added to the write roots for the server's life.
3. **Port.** The port must be free; a hub or the old hub already on it is named.
4. **quick_check**, then **migrate**: pending migrations run after a backup (``open_store`` backs up first).
5. **Backups.** The ``daily`` and ``weekly`` backups that are due are taken (``region.model.backup.auto``), then
   again once a day while the hub serves. Imports and seed imports that change records take a ``pre-import`` one.
6. **Seeds.** Pulled seeds (``region/seed``) are imported (``region.model.seed.import_seed``) and reported; any
   failure (a broken file included) is reported with its path and serving goes on. After a restore, or with a seed
   folder another checkout last used, nothing is taken silently: a banner says how many records are listed.
7. **Imports.** Each importer's sources are hashed and compared with its last applied run; for a changed one a
   dry run is made and its report printed (9.26), to be applied with ``crhub imports apply RUN``.
8. **Tiers.** The data tiers are scanned and counted.
9. **Engine, scheduler, app.** The engine pool starts in the background (the first sidecar's hello names the build;
   ``--no-engine`` leaves it out), the scheduler starts, and the app is served on 127.0.0.1 (port 8766 by
   default). A banner says when ``app/dist`` is older than ``app/src`` or missing.

Shutdown (Ctrl+C, SIGTERM, Ctrl+Break, or ``stop()``): the SSE streams end, the server stops, then the scheduler
stops, the engine pool closes, the WAL is checkpointed with TRUNCATE, the store closes and the lock is released.
"""

from __future__ import annotations

import contextlib
import logging
import signal
import sys
import threading
import time
import webbrowser
from collections.abc import Callable
from pathlib import Path
from typing import Any

from region.core import fsio, lock, paths
from region.core.errors import HubError, NotFound

log = logging.getLogger("region.api.serve")

LOOPBACK = ("127.0.0.1", "::1", "localhost")


class ServeRefused(HubError):
    """Serve cannot start (the port is taken, the database fails its check, a host that is not loopback)."""

    status = 409
    code = "serve_refused"
    title = "Serve refused"


def _within(path: Path, roots: tuple[Path, ...]) -> bool:
    import os

    target = os.path.realpath(path)
    return any(paths.names_below(os.path.realpath(r), target) is not None for r in roots)


class Serve:
    """One run of the hub. ``run()`` serves until a signal; ``start()`` and ``stop()`` serve from a thread."""

    def __init__(
        self,
        *,
        db: Path | None = None,
        port: int | None = None,
        host: str | None = None,
        engine: bool = True,
        browser: bool = False,
        seeds: bool = True,
        imports: bool | None = None,
        cfg: dict[str, Any] | None = None,
        out: Callable[[str], None] | None = None,
    ) -> None:
        self.cfg = dict(cfg) if cfg is not None else paths.config()
        self.var = paths.var_root(self.cfg)
        self.port = int(port if port is not None else self.cfg.get("port") or 8766)
        self.host = str(host or self.cfg.get("host") or "127.0.0.1")
        self.db = Path(db) if db is not None else self.var / "region.db"
        self.use_engine = engine
        self.browser = browser
        self.seeds = seeds
        # the start-up check of the importers' sources follows the seeds by default (--no-seeds skips both)
        self.check_imports = seeds if imports is None else imports
        self.stale_imports: list[dict[str, Any]] = []
        self._daily_stop = threading.Event()  # set at shutdown: ends the daily backups and the engine retries
        self.engine_retry_s: tuple[float, ...] = (5.0, 10.0, 30.0, 60.0, 120.0, 300.0)
        self._daily: threading.Thread | None = None
        self.out = out or (lambda line: print(line, flush=True))
        self.lock: lock.Lock | None = None
        self.store: Any = None
        self.jobs: Any = None
        self.engine: Any = None
        self.app: Any = None
        self.server: Any = None
        self._stack = contextlib.ExitStack()
        self._thread: threading.Thread | None = None
        self._closed = False
        # The engine pool starts in the background and the app's hub is made later, in either order: whichever comes
        # second hands the pool's answer (hello, error) to the hub (_hand_engine_to_hub).
        self._engine_lock = threading.Lock()
        self._engine_answer: tuple[dict[str, Any] | None, str | None] | None = None
        self._hub: Any = None

    @property
    def url(self) -> str:
        host = f"[{self.host}]" if ":" in self.host else self.host
        return f"http://{host}:{self.port}"

    def _say(self, what: str, text: str) -> None:
        self.out(f"{what:9} {text}")

    # ------------------------------------------------------------------------------------------------ start-up

    def prepare(self) -> None:
        """Every start-up step up to serving (see the module doc). Raises a ``HubError`` when serve must not start;
        what was taken by then (the lock) is let go."""
        try:
            self._prepare()
        except BaseException:
            self.shutdown(quiet=True)
            raise

    def _prepare(self) -> None:
        if self.host not in LOOPBACK:
            raise ServeRefused(f"the hub serves on loopback only (127.0.0.1, ::1), not {self.host}")
        # before the lock, which creates var and var/hub.lock: a refused start leaves nothing behind
        if not self.db.is_file():
            raise NotFound(f"no database at {self.db}: run crhub setup to create it (serve never creates an empty one)")
        self.lock = lock.acquire(self.var, self.port, host=self.host)
        self._say("lock", f"{lock.path_of(self.var)} (pid {self.lock.holder.pid})")
        if not _within(self.db.parent, fsio.write_roots()):
            self._stack.enter_context(fsio.allow_writes(self.db.parent))
        if not self.db.is_file():  # removed while the lock was taken
            raise NotFound(f"no database at {self.db}: run crhub setup to create it (serve never creates an empty one)")
        self._check_port()
        from region.model import backup as B
        from region.model import db as D
        from region.model.migrate import pending

        problems = B.quick_check(self.db)
        if problems:
            raise ServeRefused(
                f"{self.db} fails quick_check ({problems[0]}); restore a backup with crhub restore <file>"
            )
        con = D.connect(self.db, readonly=True)
        try:
            todo = [m.version for m in pending(con)]
        finally:
            con.close()
        self._say("database", f"{self.db} (quick_check ok)")
        from region.core import log as hub_log

        hub_log.setup(self.var / "logs", keep_days=int((self.cfg.get("logs") or {}).get("keep_days", 30)))
        from region.jobs.cache import default_cache_path
        from region.model import open_store

        cache_path = default_cache_path()
        self.store = open_store(self.db, create=False, cache=cache_path)
        if todo:
            self._say("migrate", f"applied {', '.join(map(str, todo))} after a backup to {self.store.backup_dir}")
        else:
            self._say("migrate", "up to date")
        self._backups()
        if self.seeds:
            self._import_seeds()
        if self.check_imports:
            self._check_imports()
        self._review_params()
        self._scan_tiers()
        self._start_engine()
        from region.ext.rules.params import resolve as resolve_param
        from region.jobs.scheduler import Scheduler

        pools = self.cfg.get("pools") or {}
        # the rules feature's resolver (9.25: section, then route, then system), the one the profiles router uses,
        # so a job and a route resolve a param the same way
        self.jobs = Scheduler(
            self.store,
            cache_path,
            self.engine,
            threads=int(pools.get("threads", 4)),
            processes=int(pools.get("processes", 2)),
            params=resolve_param,
        ).start()
        self._say("jobs", f"scheduler on {cache_path}")
        app_state = self._app_state()
        from region.api.app import create_app

        self.app = create_app(
            self.store, self.jobs, self.engine, {**self.cfg, "_app": app_state, "port": self.port, "host": self.host}
        )
        hub = self.app.state.hub
        if self.engine is not None:
            hub._engine_tried = True  # the background start fills the hello; no request waits for Node
            with self._engine_lock:
                self._hub = hub
            self._hand_engine_to_hub()
        self.server = self._uvicorn()

    def _check_port(self) -> None:
        from region.cli.doctor import bind_error, identify

        why = bind_error(self.host, self.port)
        if why is None:
            return
        who = None
        with contextlib.suppress(Exception):
            who = identify(self.host, self.port)
        named = f" ({who} is serving there)" if who else ""
        raise ServeRefused(
            f"port {self.port} on {self.host} is not free{named}: {why}. Stop that program, or set \"port\" in "
            "configs/local.json (or pass --port)"
        )

    def _import_seeds(self) -> None:
        from region.model import seed

        try:
            rep = seed.import_seed(self.store, seed.SEED, keep_going=True)
        except HubError as e:
            self._say("seeds", f"NOT imported: {e.detail}")
            log.warning("seed import at start failed: %s", e.detail)
            return
        except Exception as e:  # a broken file must never stop the hub; the import changed nothing
            self._say("seeds", f"NOT imported from {seed.SEED}: {type(e).__name__}: {e}")
            log.exception("seed import at start failed")
            return
        layers = rep.get("layers") or {}
        if not layers:
            self._say("seeds", f"none in {seed.SEED}")
            return
        for slug, st in layers.items():
            if st.get("error"):
                self._say("seeds", f"{slug}: NOT imported ({st['error']}); the database is unchanged for it")
                continue
            if st.get("skipped"):
                self._say("seeds", f"{slug}: skipped ({st['skipped']})")
                continue
            dangling = len(st.get("dangling") or [])
            self._say(
                "seeds",
                f"{slug}: taken {st.get('taken', 0)}, added {st.get('added', 0)}, kept {st.get('kept', 0)}, "
                f"same {st.get('same', 0)}, conflicts {len(st.get('conflicts') or [])}"
                + (f", dangling refs {dangling}" if dangling else ""),
            )
            n = len(st.get("conflicts") or [])
            if st.get("restored"):
                self._banner(
                    f"{slug} was restored from a backup: nothing was taken from region/seed. {n} record(s) differ "
                    "and are listed as seed conflicts (crhub conflicts list). Keep the restored state with crhub "
                    "conflicts resolve --all --take ours, or take region/seed's with --take theirs."
                )
            elif st.get("foreign_root"):
                self._banner(
                    f"{slug} was last exported to or imported from {st['foreign_root']}, another checkout's "
                    f"region/seed: nothing was taken from this one. {n} record(s) differ and are listed as seed "
                    "conflicts (crhub conflicts list); resolve them, or run the hub from that checkout."
                )

    def _backups(self) -> None:
        """The daily and weekly backups that are due, now and then once a day while serving (section 9)."""
        from region.model import backup as B

        dest = Path(self.store.backup_dir)
        try:
            made = B.auto(self.db, dest)
        except Exception as e:
            self._say("backups", f"NOT taken: {type(e).__name__}: {e}")
            log.exception("the daily backup failed")
            return
        what = ", ".join(p.name for p in made) if made else "daily and weekly are current"
        self._say("backups", f"{what} in {dest}")

        def daily() -> None:
            while not self._daily_stop.wait(3600):
                try:
                    B.auto(self.db, dest)
                except Exception:
                    log.exception("the daily backup failed")

        self._daily = threading.Thread(target=daily, name="daily-backup", daemon=True)
        self._daily.start()

    def _review_params(self) -> None:
        """Design rule 4: an override of a registry param names its ruling. Says how many do not, and how many equal
        the registry again (redundant); silent when there are none."""
        try:
            from region.ext.rules.params import review

            got = review(self.store)
        except Exception:
            log.exception("the param review failed")
            return
        bad, same = got["unratified"], got["redundant"]
        if bad:
            names = ", ".join(f"{e['path']} = {e['value']} on {e['layer']}" for e in bad[:4])
            self._say("params", f"{len(bad)} override(s) of the registry name no ruling (unratified): {names}")
        if same:
            names = ", ".join(f"{e['path']} on {e['layer']}" for e in same[:4])
            self._say("params", f"{len(same)} revision(s) equal the registry's value again (redundant): {names}")

    def _check_imports(self) -> None:
        """9.26: an importer whose sources changed since its last applied run gets a dry run, reported here."""
        try:
            from region.cli import imports as I

            self.stale_imports = I.check_sources(self.store)
        except Exception as e:
            self._say("imports", f"sources NOT checked: {type(e).__name__}: {e}")
            log.exception("the import source check failed")
            return
        if not self.stale_imports:
            self._say("imports", "every importer's sources are as last applied")
            return
        for st in self.stale_imports:
            self._say("imports", I.describe_stale(st))
        self._banner(
            "an import source changed since it was last applied (the old hub's seed, the line files or the "
            "registry): the map and sheets show the old import until you apply it. Review the dry run above, then "
            "crhub imports apply RUN."
        )

    def _scan_tiers(self) -> None:
        from region import tiers as T

        reports = T.scan(self.cfg)
        c = T.counts(reports)
        odd = [f"{r.name} {r.status}" + (f": {r.detail}" if r.detail else "") for r in reports.values()]
        odd = [o for o, r in zip(odd, reports.values(), strict=True) if r.status != "present"]
        line = f"{c['present']} present, {c['partial']} partial, {c['missing']} missing"
        self._say("tiers", line + (f" ({'; '.join(odd)})" if odd else ""))

    def _start_engine(self) -> None:
        if not self.use_engine:
            self._say("engine", "off (--no-engine): engine jobs fail as unavailable")
            return
        from region.enginehost import Pool

        self.engine = Pool(size=None, timeout_s=None)
        self._say("engine", f"starting {self.engine.size} sidecar(s) in the background")

        def warm() -> None:
            # a failed start (a cold Windows start can take longer than the hello timeout) is tried again with a
            # growing pause until it answers or the hub stops, so /meta and the SSE hello never keep an old error
            tries = 0
            while True:
                answer: tuple[dict[str, Any] | None, str | None]
                try:
                    answer = (dict(self.engine.start()), None)
                except HubError as e:
                    log.warning("engine: %s", e.detail)
                    answer = (None, e.detail)
                except Exception as e:
                    log.exception("engine: the pool failed to start")
                    answer = (None, f"{type(e).__name__}: {e}")
                with self._engine_lock:
                    self._engine_answer = answer
                self._hand_engine_to_hub()
                if answer[0] is not None:
                    return
                pause = self.engine_retry_s[min(tries, len(self.engine_retry_s) - 1)]
                tries += 1
                if self._daily_stop.wait(pause):
                    return

        threading.Thread(target=warm, name="engine-start", daemon=True).start()

    def _hand_engine_to_hub(self) -> None:
        """Give the pool's hello (or why it failed) to the app's hub, once both exist. The pool can answer before or
        after the app is made (a slow start-up on Windows can take seconds), so both sides call this; a later
        answer (a retry that succeeded) replaces an earlier one."""
        with self._engine_lock:
            hub, answer = self._hub, self._engine_answer
            if hub is None or answer is None:
                return
        hub.set_engine(*answer)  # outside the lock: it publishes to the event loop

    def _app_state(self) -> dict[str, Any]:
        from region.cli.doctor import app_build

        repo = Path(self.cfg.get("_repo") or paths.REPO)
        try:
            state = app_build(repo)
        except Exception:
            return {}
        if not state.get("built"):
            self._say("app", "NOT BUILT: app/dist is missing, so / shows how to build it (crhub setup)")
        elif state.get("stale"):
            self._banner(
                f"app/dist is older than {state.get('newest')}: the pages are out of date. "
                "Run npm run build -w app (crhub setup runs it), then reload."
            )
        else:
            self._say("app", "app/dist is current")
        return state

    def _banner(self, text: str) -> None:
        bar = "=" * min(100, len(text) + 4)
        self.out(bar)
        self.out(f"  {text}")
        self.out(bar)

    def _uvicorn(self) -> Any:
        import uvicorn

        config = uvicorn.Config(
            self.app,
            host=self.host,
            port=self.port,
            log_level="warning",
            access_log=False,
            log_config=None,
            lifespan="on",
            timeout_graceful_shutdown=5,
            ws="none",
            http="h11",
            loop="asyncio",
            server_header=False,
        )
        on_exit = self._end_streams

        class _Server(uvicorn.Server):
            def handle_exit(self, sig: int, frame: Any) -> None:  # end SSE streams, or shutdown waits on them
                on_exit()
                super().handle_exit(sig, frame)

        return _Server(config)

    def _end_streams(self) -> None:
        hub = getattr(self.app, "state", None) and self.app.state.hub
        if hub is not None and hub.events is not None:
            hub.events.close_streams()

    # ---------------------------------------------------------------------------------------------- serving

    def run(self) -> int:
        """Prepare, serve until a signal, shut down. The exit code."""
        self.prepare()
        saved = self._quiet_signals()
        try:
            self._say("serving", f"{self.url}  (Ctrl+C stops)")
            if self.browser:
                threading.Thread(target=self._open_browser, name="browser", daemon=True).start()
            self.server.run()
        finally:
            self.shutdown()
            for sig, handler in saved.items():
                with contextlib.suppress(Exception):
                    signal.signal(sig, handler)
        return 0

    def _quiet_signals(self) -> dict[int, Any]:
        """Handlers that ignore SIGINT, SIGTERM and SIGBREAK outside uvicorn's own: uvicorn raises the signal again
        after it stops, and the default handler would then end the process before the shutdown steps."""
        if threading.current_thread() is not threading.main_thread():
            return {}
        saved: dict[int, Any] = {}
        sigs = [signal.SIGINT, signal.SIGTERM]
        if sys.platform == "win32":
            sigs.append(signal.SIGBREAK)
        for sig in sigs:
            with contextlib.suppress(Exception):
                saved[sig] = signal.signal(sig, lambda *_: None)
        return saved

    def _open_browser(self) -> None:
        for _ in range(300):
            if getattr(self.server, "started", False):
                break
            time.sleep(0.05)
        with contextlib.suppress(Exception):
            webbrowser.open(self.url + "/")

    def start(self, timeout: float = 30.0) -> str:
        """Prepare and serve from a thread; the URL once it answers."""
        self.prepare()
        self._thread = threading.Thread(target=self.server.run, name="serve", daemon=True)
        self._thread.start()
        deadline = time.monotonic() + timeout
        while not self.server.started:
            if not self._thread.is_alive() or time.monotonic() > deadline:
                self.shutdown(quiet=True)
                raise ServeRefused("the server did not start")
            time.sleep(0.01)
        return self.url

    def stop(self) -> None:
        """Stop a server started with ``start()``, then shut down."""
        if self.server is not None:
            self._end_streams()
            self.server.should_exit = True
        if self._thread is not None:
            self._thread.join(timeout=30)
        self.shutdown()

    def shutdown(self, *, quiet: bool = False) -> None:
        """Stop the scheduler, close the engine pool, checkpoint the WAL (TRUNCATE), close the store and release the
        lock. Safe to call twice."""
        if self._closed:
            return
        self._closed = True
        self._daily_stop.set()
        steps: list[tuple[str, Callable[[], Any]]] = []
        if self.jobs is not None:
            steps.append(("scheduler", self.jobs.stop))
        if self.engine is not None:
            steps.append(("engine", self.engine.close))
        if self.store is not None:
            steps.append(("checkpoint", self.store.checkpoint))
            steps.append(("store", self.store.close))
        for name, fn in steps:
            try:
                fn()
            except Exception:
                log.exception("shutdown: %s failed", name)
        self._stack.close()
        if self.lock is not None:
            self.lock.release()
        if not quiet and self.store is not None:
            done = ["scheduler stopped"] + (["engine closed"] if self.engine is not None else [])
            self._say("stopped", ", ".join([*done, "WAL truncated", "lock released"]))


__all__ = ["LOOPBACK", "Serve", "ServeRefused"]
