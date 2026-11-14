import assert from "node:assert/strict";
import test from "node:test";
import { absoluteSiteUrl, getSiteUrl } from "./site-url.ts";

test("builds absolute canonical URLs from the configured site origin", () => {
  const previous = process.env.NEXT_PUBLIC_SITE_URL;
  process.env.NEXT_PUBLIC_SITE_URL = "https://example.test/";

  try {
    assert.equal(getSiteUrl().toString(), "https://example.test/");
    assert.equal(absoluteSiteUrl("/swieci/anna"), "https://example.test/swieci/anna");
  } finally {
    if (previous === undefined) delete process.env.NEXT_PUBLIC_SITE_URL;
    else process.env.NEXT_PUBLIC_SITE_URL = previous;
  }
});

test("falls back to the production origin for an invalid site URL", () => {
  const previous = process.env.NEXT_PUBLIC_SITE_URL;
  process.env.NEXT_PUBLIC_SITE_URL = "not a URL";

  try {
    assert.equal(getSiteUrl().origin, "https://encyklopediaswietych.pl");
  } finally {
    if (previous === undefined) delete process.env.NEXT_PUBLIC_SITE_URL;
    else process.env.NEXT_PUBLIC_SITE_URL = previous;
  }
});
