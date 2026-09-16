import { expect, test } from "@playwright/test";
import { sourceDoiUrl, sourceHttpUrl } from "../../web/lib/person-sources";

test("odsyłacze źródeł dopuszczają wyłącznie bezpieczne adresy HTTP", () => {
  expect(sourceHttpUrl(" https://example.org/rita ")).toBe("https://example.org/rita");
  for (const value of [null, "", "javascript:alert(1)", "data:text/html,test", "file:///etc/passwd", "//example.org", "https://user:password@example.org", "to nie jest URL"]) {
    expect(sourceHttpUrl(value)).toBeNull();
  }
});

test("DOI jest odsyłaczem do publikacji bez wykonywania tekstu ze źródła", () => {
  for (const value of ["10.1234/rita", "doi:10.1234/rita", "https://doi.org/10.1234/rita", "http://dx.doi.org/10.1234/rita"]) {
    expect(sourceDoiUrl(value)).toBe("https://doi.org/10.1234/rita");
  }
  expect(sourceDoiUrl("10.1234/rita#fragment")).toBe("https://doi.org/10.1234/rita%23fragment");
  expect(sourceDoiUrl("10.1234/\ud800")).toBeNull();
  expect(sourceDoiUrl("javascript:alert(1)")).toBeNull();
});
