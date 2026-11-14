import assert from "node:assert/strict";
import test from "node:test";
import { directoryRobots, hasDirectoryState } from "./directory-metadata.ts";

test("base saints directory remains indexable", () => {
  assert.equal(hasDirectoryState({}), false);
  assert.deepEqual(directoryRobots({}), { index: true, follow: true });
});

test("search, filters and pagination are followed but not indexed", () => {
  const cases = [
    [{ search: "Franciszek" }, true],
    [{ patronage: ["health", "family"] }, true],
    [{ page: "2" }, true],
    [{ search: "  " }, false],
  ] as const;

  for (const [params, hasState] of cases) {
    assert.equal(hasDirectoryState(params), hasState);
    assert.deepEqual(directoryRobots(params), {
      index: !hasState,
      follow: true,
    });
  }
});
