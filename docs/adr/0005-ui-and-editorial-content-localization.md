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
15. Localized public pages must distinguish missing data from example content. The
   home page renders explicit translated empty states when API data is unavailable
   or no records are published; it does not substitute fictional person, community
   or statistic values that could be mistaken for editorially verified data.
16. Public calendar UI copy, liturgical-rank and observance-type labels, metadata,
    accessibility labels and empty states live in the typed portal dictionary.
    Calendar date helpers require an explicit interface locale instead of assuming
    Polish. Stable calendar codes and API enum values remain untranslated. Localizing
    observance editorial content is a separate data-model migration and is not
    simulated by mixing the existing `_pl` and `_en` fields.
17. Public religious-community catalogue and profile UI copy, metadata, filters,
    cards, loading labels and empty states live in the typed portal dictionary.
    Order classifications keep their stable API keys and continue to resolve through
    shared domain-label dictionaries. Existing order editorial fields remain one
    language-neutral compatibility contract until their localization model is
    designed separately.
18. Cross-cutting public 404, route-error, loading and avatar accessibility copy
    lives in a typed `system` dictionary section. The root server layout passes only
    this serializable subset through a client context, so error boundaries and image
    fallback state do not import the server-only dictionary loader. Loading variants
    and locale-specific honorifics are data, not constants embedded in components.
19. The administrative shell uses its own typed dictionary and locale registry.
    Cross-cutting 404, route-error and loading copy is grouped under an administrative
    `system` section and passed from the root server layout as a serializable client
    context. The topbar resolves built-in role keys through its dictionary while
    preserving custom role names returned by the API. Feature-page copy continues to
    migrate independently and does not block this shell boundary.
20. The administrative login route loads metadata and typed copy on the server and
    passes only its `brand` and `login` dictionary sections to the interactive client
    form. Validation, accessibility labels, request states and session-verification
    copy are localized. Authentication failures are resolved from stable API error
    codes before any human-readable backend message, so backend prose is not an
    interface-locale contract. Password recovery is not presented as an available
    action until a recovery endpoint and workflow exist.
21. The editorial dashboard route is a server boundary that owns localized metadata
    and passes only typed `dashboard` and shared `domain` copy to its interactive
    query client. Number, date, month and relative-time formatting require an explicit
    interface locale. Known workflow statuses, completeness buckets and quality issues
    resolve from stable API keys through the shared domain dictionary; unknown future
    keys preserve the API label as a compatibility fallback. Dashboard queries, links
    and metric calculations are unaffected by localization.
22. The editorial review route keeps URL-filter parsing and dictionary loading on the
    server, then passes typed `review` and shared `domain` copy to the interactive
    queue. Person types, workflow priorities, completeness criteria and quality issues
    resolve from stable API keys; descriptive API labels are compatibility fallbacks
    only. Transition failures resolve from the canonical API error envelope before
    backend prose. Dashboard and review screens share locale-aware date and relative-
    time formatters, while permissions, query keys and transition payloads remain
    unchanged.
23. The data-quality report exposes additive stable `reason_code` and `issue_code`
    fields alongside its existing human-readable duplicate reasons and source-
    verification issues. Quality UI routing, labels and decisions use those codes;
    legacy prose remains a display fallback for rolling compatibility. Both quality
    routes load localized metadata and pass typed `quality` and shared `domain` copy
    to the client. The three tabs, metrics, tables, empty/error states and repair
    targets use explicit locale formatting and dictionary-backed accessibility copy.
24. The administrative person catalogue loads metadata and typed copy at its server
    route boundary and passes only the `persons` and shared `domain` sections to
    the interactive list. Filters, table states, pagination and profile-import dialog
    no longer own Polish UI copy. Person status, type and era labels resolve from
    stable API keys, while date and number formatting requires the explicit interface
    locale. Search debounce is component-owned and cancelled on cleanup rather than
    stored as mutable global browser state.
25. The administrative person-detail route follows the same server/client boundary.
    Its metadata, actions, empty states, hagiographic labels and history copy come from
    the typed `personDetail` section. Person status, type, era, gender, feast rank,
    liturgical colour and patronage type resolve from shared stable domain keys, with
    unknown values preserved as compatibility fallbacks. Liturgical, recognition and
    version dates are formatted with the explicit interface locale.
26. The administrative person-create and person-edit routes load metadata and editor
    copy on the server before rendering their permission-aware client boundaries. The
    shared form shell receives typed `personEditor` copy for navigation, prerequisite
    states, avatar-file validation and save actions. Stable tab identifiers and form
    field names remain independent of translated labels; field-section copy and schema
    validation messages migrate incrementally without changing payload contracts.
27. Every person-editor section now consumes a typed subsection of `personEditor`.
    Labels for person types, statuses, eras, genders, patronage types, aliases, image
    licences, community types and membership types resolve from the shared domain
    dictionary rather than component constants. Month and numeric formatting receive
    the explicit interface locale. The Zod schema is created from localized validation
    copy, while field names, enum values, normalization and API payloads remain stable.
28. The administrative geography and source/media routes load localized metadata at
    their server boundaries and pass typed feature copy, shared domain labels and an
    explicit locale to query clients. Church, source, document and image-licence labels
    resolve from stable API values. Dates and counts no longer use implicit Polish
    formatting. The legacy country-only route remains a compatible URL but redirects
    to the complete geography workspace, removing its duplicate query and table UI.
29. The administrative religious-community and controlled-dictionary routes follow
    the same server-page/client-query boundary. Community types and charisms resolve
    from shared stable domain keys in both the table and create/edit dialog; feature
    copy, metadata, dates and counts receive the explicit interface locale. The former
    Polish label constants have been removed from the generic utility module.
30. The administrative AI centre and suggestion queue load metadata and typed copy at
    their server route boundaries. Suggestion kinds, suggestion states and AI feature
    states resolve from shared stable keys; known capabilities resolve their title,
    description and live metric detail from the UI dictionary. Presentation strings
    already returned by the API remain compatibility fallbacks for unknown future
    capabilities. Dates and counts receive the explicit interface locale.
31. The administrative settings route loads localized metadata and typed copy at its
    server boundary. Environment and feature-flag labels resolve from stable keys;
    built-in account roles reuse the existing shared role labels while custom role
    names remain untouched. Profile, appearance, password and read-only runtime
    configuration states use feature copy, and dates and numbers receive the explicit
    interface locale. The API continues to expose configuration state without secrets.

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
   by home, calendar and religious-community screens. The complete home-page copy
   and its truthful empty states are also dictionary-backed. The complete public
   calendar feature (month, day and non-person observance) now uses the typed
   dictionary and explicit locale-aware date formatting. The public community
   catalogue and profile are also complete at the UI-copy boundary. Cross-cutting
   404, error, loading and avatar accessibility states complete the dictionary
   boundary for all currently implemented public routes. The administrative shell,
   system states, topbar role labels and complete login/authentication flow now use
   the separate typed admin dictionary. The complete editorial dashboard, including
   its metadata, operational states and shared workflow/quality labels, is also
   dictionary-backed. The review queue now has the same boundary for metadata, URL
   filters, tabular states, RBAC actions, pagination and return-to-editor dialog.
   The complete data-quality centre and all three tabs are dictionary-backed as well;
   stable duplicate/source-verification reason codes remove routing decisions based
   on Polish backend prose. The administrative person catalogue, including its JSON
   profile-import flow, metadata, filters, states, labels and locale-aware formatting,
   is also complete at the UI-copy boundary. The person-detail route now has the same
   boundary for metadata, actions, domain labels, dates, empty states and history.
   Person-create/edit routes and the shared editor shell now cover metadata,
   permissions, headings, tab navigation, prerequisite states, avatar validation and
   save actions. All person-editor field sections and schema-validation messages now
   use the same typed boundary, including aliases, patronages, media, communities and
   sources. The geography, source/media, religious-community and controlled-dictionary
   workspaces are also complete at the UI-copy boundary, including metadata, filters,
   metrics, tables, dialogs, domain labels and states. The AI centre and suggestion
   queue now have the same boundary for metadata, filters, operational states,
   stable status/kind labels and localized capability descriptions. Settings are also
   complete for account, appearance, password and safe runtime-configuration copy.
   Remaining administrative feature-page prose is incremental work.
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
