# @cr/app: the hub's web app

React 19 hosts dockview; every pane mounts on a plain DOM node, so a pane picks its own framework (the first panes
use none). The hub serves the build from `app/dist` (`crhub serve` never runs npm). Spec: section 8 of
`claude/Hub_Region_Architecture.md`.

## Commands

| Command | Does |
|---|---|
| `npm run build -w app` | Build into `app/dist` |
| `npm run check:size -w app` | Check the first chunk is under 400 KB gzipped (after a build) |
| `npm test -w app` | Unit tests (vitest, MSW mocks of the section 5 routes) |
| `npm run typecheck -w app` | `tsc --noEmit` over `src`, `test`, `e2e` and the configs |
| `npm run e2e -w app` | Playwright against a hub: set `CRHUB_E2E_URL`, or `CRHUB_E2E_DB` to start one (see `playwright.config.ts`) |
| `npm run gen:api -w app` | Regenerate `src/api/gen` from `region/api/openapi.json`, then commit it |
| `npm run gen:map -w app` | Regenerate the offline map assets in `public/map` (glyphs, sprite, style) |
| `npm run dev -w app` | Vite dev server on 5173, proxying `/api` to the hub on 8766 (`CRHUB_URL` overrides) |

## Layout

- `src/core/`: the plugin contract (`plugin.ts`), the registry, the URL codec and its zustand store, units, JSON
  Patch, the record cache (TanStack query-core), drafts, undo, the 412 flow (`save.ts`) and the host.
- `src/api/`: the transport (`client.ts`), the SSE client (`stream.ts`), the SharedWorker and its relay, the
  hand-written types (`types.ts`) and the ones generated from `region/api/openapi.json` in `gen/` (see
  `src/api/README.md`; `gen/` is replaced whole by `npm run gen:api`).
- `src/engine/`: the Comlink worker over `@cr/engine`, behind `EngineHandle`, with a main-thread fallback and an
  "unavailable" state when the engine cannot load.
- `src/plugins/<feature>/index.ts`: one `Plugin` each, found by `import.meta.glob`. Keep `index.ts` small and
  import the pane code inside `mount()`.
- `public/map/`: the local MapLibre style, DejaVu Sans glyph PBFs and the sprite (decision 9.30).

## Adding a pane, map layer, sheet band or command

Make `src/plugins/<feature>/index.ts` export a `Plugin` with unique ids. The registry test fails on a duplicate;
the shell offers the pane in the palette (Ctrl+K) and opens it for a selection its `accepts()` takes.

## Rules the panes keep

- **Names, not ids.** A pane shows a record by its name through `host.names` (`src/core/names.ts`): "Line 6",
  "Bond Hill (Line 6)", "Line 6 profile". An id shows only short ("…N14PM3") while its name is read.
- **One rule for the stations.** The line sheet rebuilds the stations and PVIs of the input it solves from the
  draft by the server's rule (`stationsOf` in `src/plugins/line-sheet/model.ts`, the twin of
  `region/ext/profiles/inputs.py` `build`). `test/unit/inputs_parity.test.ts` runs both on the same drafts; it
  needs a Python 3.12 (`CRHUB_PYTHON`, else `python3`, `python` or `py`).
- **Keep mine is a rebase, never a whole-document save.** After a 412 only the fields this tab changed go onto
  their version (`rebase3` in `src/core/jsonpatch.ts`); the banner names what each side changed and the fields
  both changed before Ben chooses.
- **Enter saves and leaves the cell**, so the next Ctrl+Z is the hub's undo. In a field still showing what it was
  drawn with (`data-drawn`), Ctrl+Z is the hub's undo too; a field with typed text keeps it.
- **Unsaved edits are not lost silently.** Closing or reloading the tab asks first; the drafts are kept in
  sessionStorage and offered back after a reload. Reset the pane layout lays the panes out again in place.
- **Read-only where a save would be refused**: an import or legacy layer, and main for a kind the old hub owns
  (`host.editable`, from main's authority records). Save covers the current layer's drafts only.
