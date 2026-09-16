import { expect, test } from "@playwright/test";

import { normalizeAliasForComparison } from "../components/persons/person-form-model";

test("walidacja aliasu akceptuje alfabet grecki", () => {
  expect(normalizeAliasForComparison("Ἰωάννης ὁ Χρυσόστομος")).toBe(
    "ιωαννης ο χρυσοστομος",
  );
});
