import assert from "node:assert/strict";
import test from "node:test";
import { buildSaintsDirectoryHref } from "./directory-state.ts";

test("keeps all saints catalogue filters in a shareable URL", () => {
  assert.equal(
    buildSaintsDirectoryHref({
      search: "Jan Paweł",
      typeFilters: ["saint", "blessed"],
      genderFilters: ["male"],
      periodFilters: ["modern"],
      eraFilters: ["xx_century"],
      patronageFilters: ["family", "health"],
      orderId: "order-1",
      occupationId: "occupation-1",
      birthCountryId: "country-pl",
      deathCountryId: "country-it",
      nationalityId: "country-pl",
      page: 3,
    }),
    "/swieci?search=Jan+Pawe%C5%82&type=saint&type=blessed&gender=male&period=modern&era=xx_century&patronage=family&patronage=health&order_id=order-1&occupation_id=occupation-1&birth_country_id=country-pl&death_country_id=country-it&nationality_id=country-pl&page=3",
  );
});

test("omits the first page and empty catalogue state", () => {
  assert.equal(buildSaintsDirectoryHref({ page: 1 }), "/swieci");
  assert.equal(buildSaintsDirectoryHref({ search: "", page: 0 }), "/swieci");
});
