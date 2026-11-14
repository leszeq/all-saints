import assert from "node:assert/strict";
import test from "node:test";

import { serializeJsonLd } from "./json-ld.ts";

test("escapes script-closing content while preserving parsed JSON-LD", () => {
  const value = {
    name: "Święty </script><script>alert(\"x\")</script>",
    description: "Treść <redakcyjna> & Unicode \u2028",
  };

  const serialized = serializeJsonLd(value);

  assert.equal(serialized.includes("</script>"), false);
  assert.equal(serialized.includes("\\u003c/script\\u003e"), true);
  assert.equal(serialized.includes("\\u003cscript\\u003e"), true);
  assert.equal(JSON.parse(serialized).name, value.name);
  assert.equal(JSON.parse(serialized).description, value.description);
});

test("keeps ordinary names, quotes and ampersands valid JSON", () => {
  const value = { name: 'Michał "Dobry" & przyjaciele', position: 1 };

  const serialized = serializeJsonLd(value);

  assert.deepEqual(JSON.parse(serialized), value);
  assert.equal(serialized.includes('\\"Dobry\\"'), true);
  assert.equal(serialized.includes("\\u0026"), true);
});
