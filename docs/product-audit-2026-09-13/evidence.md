# Rejestr dowodów audytu — 13 września 2026

Commit bazowy: `6745a8d77a28c8032d5e480a6637047523071d53`. Audyt obejmuje aktualne pliki robocze i lokalną bazę development. Nie jest audytem wdrożenia produkcyjnego.

Na początku zastano zmodyfikowany `apps/admin/components/persons/person-form-model.ts` oraz nieśledzony `apps/admin/e2e/person-form-validation.spec.ts`; audyt ich nie edytuje.

## Weryfikacja wykonana

| Sprawdzenie | Wynik | Granica wniosku |
|---|---|---|
| Backend unit | 204 passed, 3,74 s | Bez integracji |
| Backend unit + integration, osobna losowa baza *_test | 282 passed, 32,11 s; coverage 85,34% | Fixture tworzy schemat przez metadata.create_all, to nie pełny test migracji |
| apps/web: npm run type-check; npm run lint | oba exit 0 | Nie zastępuje produkcyjnego build/E2E |
| apps/admin: npm run type-check; npm run lint | oba exit 0 | Obejmuje zastane lokalne zmiany |
| alembic check | No new upgrade operations detected | Nie dowodzi poprawności migracji danych z poprzednich wydań |
| DB migration head | 0018_person_translation_search | Lokalna baza |
| UI | Homepage desktop, profil Jana Chryzostoma i katalog 390×844, panel i formularz tworzenia desktop | Inspekcja wizualna i accessibility tree, bez zapisu danych |
| GET API | health 200, osoby 200, kalendarz today 200, sources/stats 200 | Kilka pojedynczych próbek, bez load testu |

## Lokalny zbiór danych

| Wielkość | Wynik |
|---|---|
| Aktywne osoby / opublikowane | 75 / 75 |
| Biografia PL / streszczenie PL | 75 / 75 |
| Opublikowane osoby z aktywnym PersonSource | 41/75 = 54,7% |
| Aktywne PersonSource | 155 przypisań, nie 155 niezależnych źródeł |
| Miejsca / miejsca z koordynatami | 0 / 0 |
| Osoby z miejscem urodzenia / śmierci | 0 / 0 |
| Osoby z nationality_id | 11 / 75 |
| Zakony / członkostwa | 12 / 19 |
| PersonRelationship | 0 |
| Aktywne Feast | 69 |
| PersonEmbedding | 0 |
| Aktywne PersonTranslation | 116, nie jest to miara kompletności tłumaczenia |
| Wpisy kalendarzy | universal 16, PL 19, martyrology 33, jesuit 1, pozostałe trzy 0 |

AI_PROVIDER=none; FEATURE_AI_SEARCH=false; Sentry DSN nieskonfigurowany lokalnie; storage MinIO. Sekrety i dane kont nie zostały skopiowane do raportu.

W pojedynczej próbie API: lista osób ~26 ms; „Jan Chryzostom” ~28 ms, 2 wyniki; „Chryzostmon” ~23 ms, 1 wynik; „polscy męczennicy XX wieku” ~21 ms, 0 wyników. Czasy klienta wewnątrz kontenera; bez percentyli i bez gwarancji wydajności produkcyjnej.

## Modele odtworzone z AST

- [UUIDMixin](/Users/mateuszfidura/Desktop/all-saints/apps/backend/src/domain/base.py:41): `id`
- [TimestampMixin](/Users/mateuszfidura/Desktop/all-saints/apps/backend/src/domain/base.py:52): `created_at`, `updated_at`
- [SoftDeleteMixin](/Users/mateuszfidura/Desktop/all-saints/apps/backend/src/domain/base.py:72): `deleted_at`
- [VersionMixin](/Users/mateuszfidura/Desktop/all-saints/apps/backend/src/domain/base.py:93): `version`
- [Country](/Users/mateuszfidura/Desktop/all-saints/apps/backend/src/domain/geography/models.py:97): `name_pl`, `name_en`, `name_la`, `name_local`, `iso_code_alpha2`, `iso_code_alpha3`, `continent`, `capital`, `flag_emoji`, `is_historical`, `historical_period`, `regions`, `places`, `dioceses`
- [Region](/Users/mateuszfidura/Desktop/all-saints/apps/backend/src/domain/geography/models.py:150): `name`, `name_local`, `country_id`, `country`, `places`
- [Diocese](/Users/mateuszfidura/Desktop/all-saints/apps/backend/src/domain/geography/models.py:177): `name`, `name_la`, `is_archdiocese`, `country_id`, `founded_year`, `suppressed_year`, `country`, `places`, `churches`
- [Place](/Users/mateuszfidura/Desktop/all-saints/apps/backend/src/domain/geography/models.py:210): `name`, `name_la`, `name_local`, `description`, `country_id`, `region_id`, `diocese_id`, `latitude`, `longitude`, `country`, `region`, `diocese`, `churches`
- [ReligiousOrder](/Users/mateuszfidura/Desktop/all-saints/apps/backend/src/domain/geography/models.py:266): `slug`, `name`, `name_la`, `name_local`, `abbreviation`, `community_type`, `spiritual_family`, `founded_year`, `founded_place_id`, `founder_id`, `founder_name`, `suppressed_year`, `charism`, `description`, `description_en`, `history`, `mission`, `motto`, `website_url`, `source_title`, `source_url`, `papal_approval_year`, `is_suppressed`, `is_featured`, `sort_order`, `founded_place`, `memberships`
- [Church](/Users/mateuszfidura/Desktop/all-saints/apps/backend/src/domain/geography/models.py:348): `name`, `name_la`, `church_type`, `description`, `place_id`, `diocese_id`, `address`, `latitude`, `longitude`, `construction_year`, `consecration_year`, `website_url`, `is_pilgrimage_site`, `is_national_sanctuary`, `place`, `diocese`
- [PersonEmbedding](/Users/mateuszfidura/Desktop/all-saints/apps/backend/src/domain/hagiography/embedding_model.py:27): `id`, `person_id`, `embedding`, `source_text`, `provider`, `model`, `created_at`, `updated_at`, `person`
- [StateOfLife](/Users/mateuszfidura/Desktop/all-saints/apps/backend/src/domain/hagiography/models.py:161): `name_pl`, `name_en`, `name_la`, `description`
- [Occupation](/Users/mateuszfidura/Desktop/all-saints/apps/backend/src/domain/hagiography/models.py:177): `name_pl`, `name_en`, `name_la`, `description`
- [Category](/Users/mateuszfidura/Desktop/all-saints/apps/backend/src/domain/hagiography/models.py:193): `name_pl`, `name_en`, `slug`, `description`, `parent_id`, `sort_order`, `parent`, `children`
- [Tag](/Users/mateuszfidura/Desktop/all-saints/apps/backend/src/domain/hagiography/models.py:221): `name_pl`, `name_en`, `slug`, `color`
- [Person](/Users/mateuszfidura/Desktop/all-saints/apps/backend/src/domain/hagiography/models.py:243): `person_type`, `status`, `canonical_name`, `canonical_name_en`, `latin_name`, `original_name`, `surnames`, `religious_name`, `epithets`, `slug`, `gender`, `era`, `century`, `birth_date`, `birth_year`, `death_date`, `death_year`, `birth_place_id`, `death_place_id`, `birth_country_id`, `death_country_id`, `nationality_id`, `state_of_life_id`, `summary_pl`, `biography_pl`, `summary_en`, `biography_en`, `iconographic_attributes`, `prayers`, `works`, `liturgical_color`, `search_vector`, `ai_summary`, `ai_tags`, `is_featured`, `sort_name`, `external_ids`, `birth_place`, `death_place`, `birth_country`, `nationality`, `state_of_life`, `canonization`, `beatification`, `miracles`, `patronages`, `translations`, `aliases`, `versions`, `occupations`, `orders`, `categories`, `tags`, `images`, `embedding`, `relationships_as_a`, `relationships_as_b`
- [PersonTranslation](/Users/mateuszfidura/Desktop/all-saints/apps/backend/src/domain/hagiography/models.py:531): `person_id`, `language_code`, `canonical_name`, `summary`, `biography`, `prayers`, `iconographic_attributes`, `search_vector`, `translated_by_id`, `person`
- [PersonName](/Users/mateuszfidura/Desktop/all-saints/apps/backend/src/domain/hagiography/models.py:586): `person_id`, `value`, `normalized_value`, `language_code`, `kind`, `person`
- [Pope](/Users/mateuszfidura/Desktop/all-saints/apps/backend/src/domain/hagiography/models.py:635): `person_id`, `papal_name`, `pontificate_start`, `pontificate_end`, `pontificate_start_year`, `pontificate_end_year`, `regnal_number`, `birth_name`, `nationality_id`, `description`, `person`
- [Canonization](/Users/mateuszfidura/Desktop/all-saints/apps/backend/src/domain/hagiography/models.py:681): `person_id`, `pope_id`, `canonization_date`, `canonization_year`, `place_id`, `decree_number`, `acta_reference`, `notes`, `person`, `pope`, `place`
- [Beatification](/Users/mateuszfidura/Desktop/all-saints/apps/backend/src/domain/hagiography/models.py:723): `person_id`, `pope_id`, `beatification_date`, `beatification_year`, `place_id`, `decree_number`, `notes`, `person`, `pope`, `place`
- [Miracle](/Users/mateuszfidura/Desktop/all-saints/apps/backend/src/domain/hagiography/models.py:762): `person_id`, `title`, `description`, `year`, `place_id`, `verification_status`, `used_for_beatification`, `used_for_canonization`, `source_reference`, `person`, `place`
- [Patronage](/Users/mateuszfidura/Desktop/all-saints/apps/backend/src/domain/hagiography/models.py:808): `person_id`, `patronage_type`, `name_pl`, `name_en`, `description`, `country_id`, `is_official`, `person`
- [Relic](/Users/mateuszfidura/Desktop/all-saints/apps/backend/src/domain/hagiography/models.py:873): `person_id`, `relic_class`, `description`, `church_id`, `place_id`, `is_authenticated`, `authentication_document`, `person`
- [PersonQuote](/Users/mateuszfidura/Desktop/all-saints/apps/backend/src/domain/hagiography/models.py:916): `person_id`, `quote_pl`, `quote_en`, `quote_la`, `source`, `is_attributed`, `person`
- [PersonRelationship](/Users/mateuszfidura/Desktop/all-saints/apps/backend/src/domain/hagiography/models.py:946): `person_a_id`, `person_b_id`, `relationship_type`, `description`, `is_bidirectional`, `person_a`, `person_b`
- [PersonVersion](/Users/mateuszfidura/Desktop/all-saints/apps/backend/src/domain/hagiography/models.py:993): `id`, `person_id`, `version_number`, `snapshot`, `changed_by_id`, `changed_at`, `change_summary`, `person`
- [PersonOccupation](/Users/mateuszfidura/Desktop/all-saints/apps/backend/src/domain/hagiography/models.py:1041): `person_id`, `occupation_id`, `person`, `occupation`
- [PersonOrder](/Users/mateuszfidura/Desktop/all-saints/apps/backend/src/domain/hagiography/models.py:1061): `person_id`, `order_id`, `entry_date`, `exit_date`, `is_founder`, `membership_type`, `notes`, `person`, `order`
- [PersonCategory](/Users/mateuszfidura/Desktop/all-saints/apps/backend/src/domain/hagiography/models.py:1093): `person_id`, `category_id`, `person`, `category`
- [PersonTag](/Users/mateuszfidura/Desktop/all-saints/apps/backend/src/domain/hagiography/models.py:1113): `person_id`, `tag_id`, `person`, `tag`
- [Permission](/Users/mateuszfidura/Desktop/all-saints/apps/backend/src/domain/identity/models.py:83): `resource`, `action`, `description`, `roles`
- [Role](/Users/mateuszfidura/Desktop/all-saints/apps/backend/src/domain/identity/models.py:123): `name`, `display_name`, `description`, `is_system`, `permissions`, `users`
- [RolePermission](/Users/mateuszfidura/Desktop/all-saints/apps/backend/src/domain/identity/models.py:176): `role_id`, `permission_id`, `granted_at`, `role`, `permission`
- [User](/Users/mateuszfidura/Desktop/all-saints/apps/backend/src/domain/identity/models.py:207): `email`, `hashed_password`, `full_name`, `status`, `avatar_url`, `bio`, `preferred_language`, `is_verified`, `is_two_factor_enabled`, `two_factor_secret`, `password_changed_at`, `last_login_at`, `failed_login_attempts`, `locked_until`, `roles`, `refresh_tokens`, `audit_logs`
- [UserRole](/Users/mateuszfidura/Desktop/all-saints/apps/backend/src/domain/identity/models.py:321): `user_id`, `role_id`, `assigned_at`, `assigned_by_id`, `user`, `role`
- [RefreshToken](/Users/mateuszfidura/Desktop/all-saints/apps/backend/src/domain/identity/models.py:354): `user_id`, `token_hash`, `expires_at`, `revoked_at`, `user_agent`, `ip_address`, `user`
- [AuditLog](/Users/mateuszfidura/Desktop/all-saints/apps/backend/src/domain/identity/models.py:401): `id`, `created_at`, `user_id`, `user_email`, `action`, `resource_type`, `resource_id`, `old_value`, `new_value`, `ip_address`, `user_agent`, `request_id`, `extra_metadata`, `user`
- [PermissionDefinition](/Users/mateuszfidura/Desktop/all-saints/apps/backend/src/domain/identity/rbac.py:16): `resource`, `action`, `description`, `group`
- [RoleDefinition](/Users/mateuszfidura/Desktop/all-saints/apps/backend/src/domain/identity/rbac.py:28): `display_name`, `description`
- [LiturgicalCalendar](/Users/mateuszfidura/Desktop/all-saints/apps/backend/src/domain/liturgy/models.py:65): `code`, `name`, `rite`, `scope`, `country_id`, `religious_order_id`, `description`, `is_active`, `feasts`
- [LiturgicalObservance](/Users/mateuszfidura/Desktop/all-saints/apps/backend/src/domain/liturgy/models.py:120): `slug`, `title_pl`, `title_en`, `latin_title`, `observance_type`, `summary_pl`, `description_pl`, `iconographic_attributes`, `is_featured`, `feasts`
- [Feast](/Users/mateuszfidura/Desktop/all-saints/apps/backend/src/domain/liturgy/models.py:155): `person_id`, `observance_id`, `calendar_id`, `month`, `day`, `day_of_year`, `date_note`, `is_moveable`, `rank`, `liturgical_color`, `is_primary`, `is_suppressed`, `notes`, `source_title`, `source_url`, `person`, `observance`, `calendar`
- [Bibliography](/Users/mateuszfidura/Desktop/all-saints/apps/backend/src/domain/sources/models.py:75): `source_type`, `title`, `subtitle`, `authors`, `editor`, `publisher`, `place_of_publication`, `year`, `edition`, `volume`, `pages`, `isbn`, `issn`, `doi`, `url`, `url_access_date`, `language`, `abstract`, `reliability_score`, `notes`, `person_sources`
- [HistoricalSource](/Users/mateuszfidura/Desktop/all-saints/apps/backend/src/domain/sources/models.py:141): `title`, `original_title`, `source_type`, `repository`, `call_number`, `date_range`, `language`, `description`, `digitization_url`, `is_digitized`, `person_sources`
- [PersonSource](/Users/mateuszfidura/Desktop/all-saints/apps/backend/src/domain/sources/models.py:186): `person_id`, `bibliography_id`, `historical_source_id`, `page_reference`, `quote`, `relevance_score`, `is_primary`, `notes`, `bibliography`, `historical_source`
- [Image](/Users/mateuszfidura/Desktop/all-saints/apps/backend/src/domain/sources/models.py:238): `person_id`, `url`, `thumbnail_url`, `storage_key`, `title`, `description`, `image_type`, `license`, `photographer`, `source_url`, `year_created`, `is_primary`, `sort_order`, `width_px`, `height_px`, `file_size_bytes`, `mime_type`, `person`
- [Document](/Users/mateuszfidura/Desktop/all-saints/apps/backend/src/domain/sources/models.py:313): `person_id`, `title`, `document_type`, `language_code`, `description`, `file_url`, `storage_key`, `file_size_bytes`, `mime_type`, `is_public`

## Publiczne strony i strony panelu

- [apps/admin/app/dashboard/ai/page.tsx](/Users/mateuszfidura/Desktop/all-saints/apps/admin/app/dashboard/ai/page.tsx)
- [apps/admin/app/dashboard/ai/suggestions/page.tsx](/Users/mateuszfidura/Desktop/all-saints/apps/admin/app/dashboard/ai/suggestions/page.tsx)
- [apps/admin/app/dashboard/dictionaries/page.tsx](/Users/mateuszfidura/Desktop/all-saints/apps/admin/app/dashboard/dictionaries/page.tsx)
- [apps/admin/app/dashboard/geography/countries/page.tsx](/Users/mateuszfidura/Desktop/all-saints/apps/admin/app/dashboard/geography/countries/page.tsx)
- [apps/admin/app/dashboard/geography/page.tsx](/Users/mateuszfidura/Desktop/all-saints/apps/admin/app/dashboard/geography/page.tsx)
- [apps/admin/app/dashboard/orders/page.tsx](/Users/mateuszfidura/Desktop/all-saints/apps/admin/app/dashboard/orders/page.tsx)
- [apps/admin/app/dashboard/page.tsx](/Users/mateuszfidura/Desktop/all-saints/apps/admin/app/dashboard/page.tsx)
- [apps/admin/app/dashboard/persons/[id]/edit/page.tsx](/Users/mateuszfidura/Desktop/all-saints/apps/admin/app/dashboard/persons/[id]/edit/page.tsx)
- [apps/admin/app/dashboard/persons/[id]/page.tsx](/Users/mateuszfidura/Desktop/all-saints/apps/admin/app/dashboard/persons/[id]/page.tsx)
- [apps/admin/app/dashboard/persons/new/page.tsx](/Users/mateuszfidura/Desktop/all-saints/apps/admin/app/dashboard/persons/new/page.tsx)
- [apps/admin/app/dashboard/persons/page.tsx](/Users/mateuszfidura/Desktop/all-saints/apps/admin/app/dashboard/persons/page.tsx)
- [apps/admin/app/dashboard/quality/[tab]/page.tsx](/Users/mateuszfidura/Desktop/all-saints/apps/admin/app/dashboard/quality/[tab]/page.tsx)
- [apps/admin/app/dashboard/quality/page.tsx](/Users/mateuszfidura/Desktop/all-saints/apps/admin/app/dashboard/quality/page.tsx)
- [apps/admin/app/dashboard/review/page.tsx](/Users/mateuszfidura/Desktop/all-saints/apps/admin/app/dashboard/review/page.tsx)
- [apps/admin/app/dashboard/settings/page.tsx](/Users/mateuszfidura/Desktop/all-saints/apps/admin/app/dashboard/settings/page.tsx)
- [apps/admin/app/dashboard/sources/page.tsx](/Users/mateuszfidura/Desktop/all-saints/apps/admin/app/dashboard/sources/page.tsx)
- [apps/admin/app/dashboard/users/page.tsx](/Users/mateuszfidura/Desktop/all-saints/apps/admin/app/dashboard/users/page.tsx)
- [apps/admin/app/login/page.tsx](/Users/mateuszfidura/Desktop/all-saints/apps/admin/app/login/page.tsx)
- [apps/admin/app/page.tsx](/Users/mateuszfidura/Desktop/all-saints/apps/admin/app/page.tsx)
- [apps/web/app/kalendarz/[data]/page.tsx](/Users/mateuszfidura/Desktop/all-saints/apps/web/app/kalendarz/[data]/page.tsx)
- [apps/web/app/kalendarz/obchody/[slug]/page.tsx](/Users/mateuszfidura/Desktop/all-saints/apps/web/app/kalendarz/obchody/[slug]/page.tsx)
- [apps/web/app/kalendarz/page.tsx](/Users/mateuszfidura/Desktop/all-saints/apps/web/app/kalendarz/page.tsx)
- [apps/web/app/page.tsx](/Users/mateuszfidura/Desktop/all-saints/apps/web/app/page.tsx)
- [apps/web/app/swieci/[slug]/page.tsx](/Users/mateuszfidura/Desktop/all-saints/apps/web/app/swieci/[slug]/page.tsx)
- [apps/web/app/swieci/page.tsx](/Users/mateuszfidura/Desktop/all-saints/apps/web/app/swieci/page.tsx)
- [apps/web/app/zakony/[slug]/page.tsx](/Users/mateuszfidura/Desktop/all-saints/apps/web/app/zakony/[slug]/page.tsx)
- [apps/web/app/zakony/page.tsx](/Users/mateuszfidura/Desktop/all-saints/apps/web/app/zakony/page.tsx)

## Migracje

- [0001_initial_schema.py](/Users/mateuszfidura/Desktop/all-saints/apps/backend/alembic/versions/0001_initial_schema.py)
- [0002_seed_person_reference_data.py](/Users/mateuszfidura/Desktop/all-saints/apps/backend/alembic/versions/0002_seed_person_reference_data.py)
- [0003_add_person_embeddings.py](/Users/mateuszfidura/Desktop/all-saints/apps/backend/alembic/versions/0003_add_person_embeddings.py)
- [0004_unique_primary_person_image.py](/Users/mateuszfidura/Desktop/all-saints/apps/backend/alembic/versions/0004_unique_primary_person_image.py)
- [0005_enrich_liturgical_feasts.py](/Users/mateuszfidura/Desktop/all-saints/apps/backend/alembic/versions/0005_enrich_liturgical_feasts.py)
- [0006_expand_religious_orders.py](/Users/mateuszfidura/Desktop/all-saints/apps/backend/alembic/versions/0006_expand_religious_orders.py)
- [0007_register_roman_martyrology.py](/Users/mateuszfidura/Desktop/all-saints/apps/backend/alembic/versions/0007_register_roman_martyrology.py)
- [0008_add_liturgical_observances.py](/Users/mateuszfidura/Desktop/all-saints/apps/backend/alembic/versions/0008_add_liturgical_observances.py)
- [0009_expand_countries.py](/Users/mateuszfidura/Desktop/all-saints/apps/backend/alembic/versions/0009_expand_countries.py)
- [0010_enable_person_search.py](/Users/mateuszfidura/Desktop/all-saints/apps/backend/alembic/versions/0010_enable_person_search.py)
- [0011_align_base_indexes.py](/Users/mateuszfidura/Desktop/all-saints/apps/backend/alembic/versions/0011_align_base_indexes.py)
- [0012_align_domain_indexes.py](/Users/mateuszfidura/Desktop/all-saints/apps/backend/alembic/versions/0012_align_domain_indexes.py)
- [0013_refine_editorial_rbac.py](/Users/mateuszfidura/Desktop/all-saints/apps/backend/alembic/versions/0013_refine_editorial_rbac.py)
- [0014_person_version_changed_at.py](/Users/mateuszfidura/Desktop/all-saints/apps/backend/alembic/versions/0014_person_version_changed_at.py)
- [0015_remove_legacy_person_embeddings.py](/Users/mateuszfidura/Desktop/all-saints/apps/backend/alembic/versions/0015_remove_legacy_person_embeddings.py)
- [0016_person_names.py](/Users/mateuszfidura/Desktop/all-saints/apps/backend/alembic/versions/0016_person_names.py)
- [0017_translation_workflow_rbac.py](/Users/mateuszfidura/Desktop/all-saints/apps/backend/alembic/versions/0017_translation_workflow_rbac.py)
- [0018_person_translation_search.py](/Users/mateuszfidura/Desktop/all-saints/apps/backend/alembic/versions/0018_person_translation_search.py)

## Zakres niezweryfikowany

Nie wykonano: produkcyjnego build, automatycznego Playwright E2E, audytu zależności przez sieć, prób ataków na żywej aplikacji, testów obciążeniowych, pełnego audytu WCAG, odtworzenia produkcyjnego backupu ani kontroli merytorycznej wszystkich biografii. Istnienie takich testów w CI oznacza konfigurację, a nie potwierdzony bieżący wynik CI. Nie uruchamiano płatnych providerów AI.
