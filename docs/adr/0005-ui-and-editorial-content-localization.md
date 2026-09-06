# ADR 0005: UI and editorial content localization

- Status: Accepted
- Date: 2026-09-06

## Context

The public portal and editorial panel currently render Polish strings directly in
components. Hagiographic content uses both legacy language-specific columns on
`Person` (`canonical_name_en`, `summary_pl`, `summary_en`, `biography_pl`,
`biography_en`) and the generic `PersonTranslation` table. Extending both patterns
would create a new schema migration and a growing set of optional fields for every
language.

UI copy and editorial content also have different lifecycles. UI copy is released
with application code and must be complete for a supported interface locale.
Editorial translations are versioned records, can be incomplete, and require source
and review metadata.

The existing Polish routes and API response fields are already public contracts and
must remain compatible while localization is introduced incrementally.

## Options considered

### Add another column for every language

This keeps reads simple, but every language changes the database, API schemas,
search triggers, forms and imports. Sparse columns and duplicated application logic
grow without a natural limit.

### Store every translation in unstructured JSON

This avoids migrations for new languages, but weakens constraints, indexing,
editorial ownership and field-level review. It also makes search and audit queries
harder to reason about.

### Separate code dictionaries from normalized editorial translations

Typed dictionaries own UI copy. `PersonTranslation` owns localized editorial fields.
Legacy columns remain as a compatibility projection during a measured migration.
This introduces an explicit resolution layer but preserves validation, indexing and
the existing public API.

## Decision

1. UI localization and editorial-content localization are separate concerns.
2. Each frontend owns a typed dictionary because the portal and panel are different
   products. A locale is advertised as supported only when its complete dictionary
   passes TypeScript and its critical routes pass build/E2E checks.
3. Polish (`pl`) is the only supported UI locale in the first migration stage.
   Hardcoded copy is moved by vertical slice; an incomplete English dictionary must
   not be selectable.
4. Public locale-aware URLs will use a path segment when the first additional locale
   is ready. Existing unprefixed Polish URLs remain valid and canonical during that
   rollout. The editorial panel will resolve locale from the authenticated user's
   preference and fall back to Polish; its routes are not localized.
5. Language identifiers use normalized BCP 47 tags. Resolution checks the exact tag,
   then its primary language subtag, then Polish.
6. `PersonTranslation` is the target source of truth for localized person name,
   summary, biography, prayers and iconographic attributes. No new language-specific
   columns such as `summary_it` or `biography_de` may be added.
7. Existing Polish and English columns remain temporarily readable and writable for
   API compatibility. During migration, a localization projection will prefer an
   active translation row and fall back to the legacy columns. A later ADR and
   deprecation window are required before removing legacy fields.
8. A localized API projection must eventually expose the requested locale, resolved
   locale and whether fallback occurred. It must not silently combine fields from
   different languages into one apparently complete translation.
9. Latin (`la`) is a valid content language. It is not automatically an interface
   locale.
10. A translation shares its parent person's editorial lifecycle. Authors may
    create, update or soft-delete translations only while the person is a draft.
    Every mutation increments the parent revision and is included in the same
    version snapshot and audit trail. Reviewers can read translations but cannot
    edit them, so localized content cannot bypass review or publication.
11. Legacy-column backfill is an explicit maintenance operation and defaults to a
    read-only dry run. It creates only absent `pl`/`en` rows, treats every existing
    or soft-deleted row as editorially authoritative, and reports differences
    without merging or overwriting them. Because copied values are a compatibility
    projection rather than a content edit, this one-time operation does not create
    person revisions; all later mutations use the protected workflow.
12. Public text search evaluates active translations as weighted, language-neutral
    PostgreSQL search documents. Names have the highest weight, followed by summary
    and iconographic attributes, prayers, and biography. Translation matches use a
    correlated subquery so multiple matching locales cannot duplicate a person in
    pagination; soft-deleted translations never participate.
13. Public person consumers request an explicit content locale and render the
    `localized_content` projection for names and editorial text. They may use legacy
    fields only when talking to an older backend that does not return the projection;
    fields missing from an existing translation are not silently filled from another
    language. Catalogue projections include summary and iconographic attributes but
    continue to omit biography and prayers.
14. Stable API/filter values are not UI copy. Person types, eras, public time and
    patronage groups, and religious-community classifications keep their existing
    language-neutral keys while every visible label lives in the typed UI dictionary.
    Compatibility aliases for historical Polish query values are isolated from the
    translated labels and remain accepted during the URL migration window.

## Consequences

### Advantages

- New content languages do not require widening `persons`.
- Missing UI keys fail during type checking instead of at runtime.
- Existing routes, payloads and stored records remain compatible.
- Editorial translations keep relational constraints and can gain workflow metadata.
- Locale fallback becomes deterministic and observable.

### Disadvantages

- The transition temporarily maintains legacy columns and translation rows.
- Frontend copy must be migrated in several small commits.
- Search and API serialization need an explicit localized-content projection.
- Supporting a locale requires complete UI, SEO and accessibility verification.

## Migration path

1. Introduce typed Polish dictionaries and migrate global application shells.
2. Move remaining page copy by feature, keeping UI behaviour unchanged. Completed
   for the global shell, person catalogue/profile and shared domain labels consumed
   by home, calendar and religious-community screens; remaining page prose and
   administrative feature screens remain incremental work.
3. Add application-layer commands and protected endpoints for translation workflow.
4. Backfill `pl` and `en` translation rows idempotently from legacy columns and
   report conflicts without overwriting reviewed translations. The maintenance
   command and conflict report are implemented; applying it is an explicit
   environment-level decision after reviewing a dry run.
5. Add localized public projections and extend search indexes to active translation
   rows, with explicit fallback metadata. Completed for person list/detail and
   weighted translated-content search.
6. Ship the first additional UI locale and locale-aware public routing only after
   dictionary, metadata, canonical/hreflang and E2E coverage are complete.
7. Deprecate legacy language-specific API fields; remove columns only in a separate,
   reversible migration after all consumers have moved.

## Verification

- TypeScript checks require complete dictionaries for every declared UI locale.
- ESLint and production builds verify the migrated server/client boundary.
- Backend tests will cover resolution and backfill before any data migration ships.
- No database or public API contract changes are part of this ADR's first stage.
