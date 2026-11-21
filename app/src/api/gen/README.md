# Generated API types

This folder holds the TypeScript types that `@hey-api/openapi-ts` generates from `region/api/openapi.json`. Do not
edit it by hand. Regenerate with `npm run gen:api -w app` after the server's routes change, and commit the result.

Until `region/api/openapi.json` exists (WP2 writes it), the app uses the hand-written shapes in `src/api/types.ts`,
and the drift test `test/unit/api_drift.test.ts` is skipped. Once the file exists the drift test runs and fails
whenever this folder differs from a fresh generation.

Generation replaces the whole folder, this file included; the drift test compares only the `.ts` files.
