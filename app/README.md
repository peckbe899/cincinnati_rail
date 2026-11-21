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
  hand-written types (`types.ts`) and, once WP2 writes `region/api/openapi.json`, the generated ones in `gen/`.
- `src/engine/`: the Comlink worker over `@cr/engine`, behind `EngineHandle`, with a main-thread fallback and an
  "unavailable" state when the engine cannot load.
- `src/plugins/<feature>/index.ts`: one `Plugin` each, found by `import.meta.glob`. Keep `index.ts` small and
  import the pane code inside `mount()`.
- `public/map/`: the local MapLibre style, DejaVu Sans glyph PBFs and the sprite (decision 9.30).

## Adding a pane, map layer, sheet band or command

Make `src/plugins/<feature>/index.ts` export a `Plugin` with unique ids. The registry test fails on a duplicate;
the shell offers the pane in the palette (Ctrl+K) and opens it for a selection its `accepts()` takes.
