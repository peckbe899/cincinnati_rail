// Unit tests (test/unit). Node is the default environment; a test that needs a DOM says so with a
// `// @vitest-environment happy-dom` comment. HTTP is mocked with MSW (msw/node) against the section 5 routes.

import { defineConfig } from "vitest/config";

export default defineConfig({
  test: {
    include: ["test/unit/**/*.test.ts"],
    environment: "node",
    testTimeout: 15_000,
    restoreMocks: true,
  },
});
