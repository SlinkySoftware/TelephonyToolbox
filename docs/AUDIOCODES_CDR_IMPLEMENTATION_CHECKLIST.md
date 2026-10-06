# AudioCodes CDR Module — Implementation Checklist

Working checklist for implementing [audiocodes-cdr-manager-specification.md](audiocodes-cdr-manager-specification.md) inside Telephony Toolbox. Checkboxes below reflect the repository state verified on 2026-10-07.

**Status:** Backend, frontend, documentation and deployment-script work is complete. Session detail returns every associated CDR. Remaining differences from the specification are accepted decisions recorded under [known implementation differences](#known-implementation-differences).

## Table of Contents

1. [Scan Findings](#0-scan-findings-that-shape-the-design)
2. [Decisions](#1-decisions)
3. [Backend — New App](#2-backend--new-app-backendaudiocodes_cdr)
4. [Backend — Modify Existing](#3-backend--modify-existing)
5. [Frontend — New Files](#4-frontend--new-files)
6. [Frontend — Modify Existing](#5-frontend--modify-existing)
7. [Deployment / Scripts](#6-deployment--scripts)
8. [Documentation](#7-documentation)
9. [Implementation Order](#8-implementation-order)

## 0. Scan findings that shape the design

| # | Finding | Impact |
|---|---|---|
| F1 | Gunicorn was `--timeout 60`, `sync`, 4 workers; nginx `/api/` had no `proxy_read_timeout` (default 60s) | **Implemented:** [rhel-deploy-common.sh](../scripts/rhel-deploy-common.sh) uses `gthread` 4 × 4, `--timeout 150` and `proxy_read_timeout 150s` (shared `BACKEND_REQUEST_TIMEOUT`). |
| F2 | No shared cache was configured at scan time | **Implemented:** `DatabaseCache` uses the application DB; `run_migrations` runs `createcachetable`. |
| F3 | `cryptography` was absent at scan time | **Implemented:** pinned backend dependency and Fernet/MultiFernet credential protection. |
| F4 | ECharts was absent at scan time; deploy uses npm + `package-lock.json` | **Implemented:** ECharts is in frontend dependencies and used by statistics charts. |
| F5 | Existing [health/services.py](../backend/health/services.py) `_database_status()` returns `str(exc)` | **Implemented for CDR:** AudioCodes source status uses safe generic errors. Pre-existing application DB/CUCM health messages intentionally unchanged (D19). |
| F6 | [middleware.py](../backend/telephony_toolbox/middleware.py) and access logs could expose CDR query values | **Implemented:** Django timing middleware, the Gunicorn `RedactingLogger` (enabled by the deploy script) and an Nginx redacted `log_format` strip CDR query strings from request URIs and referers. |
| F7 | `formatDateTime` in [format.js](../frontend/src/utils/format.js) uses browser TZ, no ms | **Implemented:** CDR-specific Sydney timestamp formatting preserves millisecond precision. |
| F8 | Tests run on SQLite unless `DATABASE_NAME` is set | **Implemented:** unmanaged test tables are created in fixtures and statistics use portable ORM aggregation. |
| F9 | Source credential lives in the app DB | **Implemented:** runtime source alias activation reads encrypted profiles from the app DB. |
| F10 | No server-side `q-table` existed at scan time | **Implemented:** SDR search uses server-side pagination and sorting. |
| F11 | Sydney-truncated hourly buckets can merge repeated 02:00 during DST fall-back | **Implemented:** hourly buckets truncate in UTC; daily buckets use Sydney boundaries. |

## 1. Decisions

Status: **confirmed** (2026-10-06).

| ID | Decision | Answer |
|---|---|---|
| D1 | Source schema | Confirmed — see [Source schema mapping](#source-schema-mapping) |
| D1b | Source timestamp semantics | `timestamp with time zone` (absolute instants) |
| D1c | Existing source indexes | None beyond primary keys. Recommendations in [AUDIOCODES_CDR_INDEX_RECOMMENDATIONS.md](AUDIOCODES_CDR_INDEX_RECOMMENDATIONS.md); `cdr(sessionid)` is a prerequisite for usable session detail |
| D2 | "12 months" definition | 12 calendar months in Australia/Sydney (`end <= start + 12 months`, day clamped to month end) |
| D3 | Termination-reason lookup | Cached DISTINCT across the 4 SDR termination columns over a recent window; `termination_lookup_days` default 30 |
| D4 | Cache backend | Django `DatabaseCache` in the app DB; deploy scripts run `createcachetable` after migrations. |
| D5 | Gunicorn / nginx | `gthread`, 4 workers × 4 threads, timeout 150s; nginx `proxy_read_timeout 150s`. Implemented in the deploy script and systemd template. |
| D6 | Log redaction | Django timing middleware, Gunicorn `RedactingLogger` and an Nginx `map` + redacted `log_format` strip query strings from `/admin/cdr` and `/api/admin/cdr/` URIs and referers. Search filters remain in browser route query state; Nginx error-log entries for upstream failures still contain the request line. |
| D7 | Encryption key | `CDR_SOURCE_ENCRYPTION_KEY`, comma-separated `MultiFernet` (first key encrypts, all decrypt) |
| D7b | Key provisioning | Install/upgrade scripts generate the key when missing or blank (D17) and never overwrite a non-empty value. |
| D8 | Source connectivity | Direct connection, no PgBouncer, server currently without TLS |
| D8b | `sslmode` | Selectable per profile (`disable`/`prefer`/`require`/`verify-ca`/`verify-full`), default `prefer` |
| D9 | Hourly/daily threshold | Hourly up to and including 7 days (`hourly_bucket_max_hours = 168`); daily beyond |
| D10 | Default duration format | `HH:MM:SS.ff` (`hms`) |
| D11 | Page sizes / multi-select | Page sizes 25/50/100/250/500, default 100, max 500; multi-select defaults to 50, but the settings API permits configuration up to 200. |
| D12 | Cache lifetimes | Lookups 900s, statistics 300s |
| D13 | Help content | Concise help written from public AudioCodes 7.4 SBC CDR documentation; no termination-reason explanations unless configured |
| D14 | Dev source DB | Test fixtures only (unmanaged tables created in the test DB) |
| D15 | CDR legs per session | No cap; session detail returns every CDR sharing the SDR `sessionid` (spec §10.1). |
| D16 | Default-today end | Keep rounding up to the next minute for cache-key reuse. |
| D17 | Blank encryption key in an existing env file | Treated as absent and generated. |
| D18 | In-app source privilege check | None; SELECT-only provisioning and verification remain a DBA responsibility. |
| D19 | Pre-existing app DB/CUCM health `str(exc)` messages | Leave unchanged (outside CDR scope). |

### Known implementation differences

Accepted on 2026-10-07:

- The default-today range ends at the next minute boundary rather than the exact current instant, to improve cache-key reuse (D16).
- IP-group lookups return no more than 1,000 values. Statistics return at most 100 groups per direction and 10 values per termination field.
- Source connection SSL mode is configurable, but the settings page does not verify effective PostgreSQL permissions. The DBA must provision and verify a dedicated SELECT-only role (D18).
- CDR search filters are held in route query parameters, so they appear in browser history. Django, Gunicorn and Nginx access logs redact them; Nginx error-log entries for upstream failures do not.

### Source schema mapping

Tables and columns were created unquoted, so PostgreSQL names are lowercase (`public.sdr`, `public.cdr`, `setuptime`, …), matching spec §6. All columns except `id` are nullable.

| Source type | Django field | Columns |
|---|---|---|
| `bigint` PK (sequence default) | `BigIntegerField(primary_key=True)` | `sdr.id`, `cdr.id` |
| `timestamptz` | `DateTimeField(null=True)` | `setuptime`, `connecttime`, `releasetime` (both tables) |
| `bigint` | `BigIntegerField(null=True)` | SDR: `timetoconnect`, `ingressremotertpport`, `egressremotertpport`. CDR: `legid`, `remoteport`, `remotertpport`, `alertingtime`, `callduration`, `terminationreasonvalue`, `localjitter`, `localpacketloss`, `localroundtripdelay`, `remotejitter`, `remotepacketloss`, `remoteroundtripdelay` |
| `varchar(255)` | `CharField(max_length=255, null=True)` | SDR `callduration` (**text — numeric-cast only when valid**) and all remaining text columns |
| `boolean` | `BooleanField(null=True)` | SDR: `issuccess`. CDR: `wascallstarted`, `callsuccess`, `terminationsideyesno` |

Implications:

- Only SDR `callduration` needs the defensive numeric handling of spec §11.3 / §20.5. `timetoconnect`, CDR `callduration` and `alertingtime` are already integers.
- Timestamps are absolute instants, so `USE_TZ = True` works natively; there is no DST ambiguity in stored data.
- Number and Call-ID matching is case-sensitive `LIKE` / `=` to stay index-compatible.

## 2. Backend — new app `backend/audiocodes_cdr/`

### Models & migrations

- [x] `__init__.py`
- [x] `apps.py` — `AudiocodesCdrConfig.ready()`: `connection_created` receiver (`SET statement_timeout=60000`, `SET default_transaction_read_only=on`), `pre_migrate` guard aborting when `using == 'audiocodes_source'`, system checks for encryption key
- [x] `source_models.py` — unmanaged `Sdr`, `Cdr`
  - `managed = False`, `db_table = 'sdr'` / `'cdr'`, exact field names per spec §6
  - `ReadOnlySourceQuerySet` blocks `update` / `delete` / `bulk_create` / `select_for_update`; `save()` / `delete()` raise
- [x] `models.py` — app DB models
  - `CdrSourceProfile` (`UUIDTimestampedModel`): `role` (`replica` | `primary`, unique), `host`, `port`, `database_name`, `username`, `password_encrypted`, `sslmode` (default `prefer`), `sslrootcert`, `connect_timeout`, `is_enabled`
  - `CdrModuleSettings` (singleton) with defaults:
    - `active_source`: `replica`
    - `max_page_size`: 500
    - `max_multiselect_values`: 50
    - `lookup_cache_seconds`: 900
    - `statistics_cache_seconds`: 300
    - `termination_lookup_days`: 30
    - `hourly_bucket_max_hours`: 168
    - `user_defined_fields` (JSON), `media_quality` (JSON, all thresholds `null`), `field_help_overrides` (JSON)
    - `config_version`, `updated_by_text`
  - `CdrUserPreference`: `user` (OneToOne, CASCADE), `duration_format` (`seconds` | `hms`, default `hms`)
- [x] `migrations/0001_initial.py` (generated; unmanaged models create no source DDL)

### Source protection & connection

- [x] `routers.py` — `AudioCodesSourceRouter`
  - `db_for_read`: source models → `audiocodes_source`
  - `db_for_write`: source models → raise (never fall back to `default`)
  - `allow_relation`: `False` across source/app models
  - `allow_migrate`: `False` for the source alias and for source models
- [x] `crypto.py` — `MultiFernet` built from comma-separated `CDR_SOURCE_ENCRYPTION_KEY`; first key encrypts, all decrypt; missing/invalid key fails closed
- [x] `connection.py`
  - `activate_source()`: load active profile (cached by `config_version`), decrypt, populate `connections.settings['audiocodes_source']`, close stale connection on version change
  - Thread-safe for gthread workers (D5): lock around settings mutation; each thread's connection is stamped with the `config_version` it opened under and closed when stale
  - OPTIONS: `-c statement_timeout=60000 -c default_transaction_read_only=on -c search_path=public`, `application_name=telephony-toolbox-cdr`, `sslmode` from profile, `connect_timeout`; leave `server_side_binding` off (planner needs literal prefixes)
  - `source_errors()` context manager: `QueryCanceled` (statement timeout) → `SourceTimeout`; replica conflict-with-recovery cancellation → `SourceTimeout` with a retry hint; `OperationalError` → `SourceUnavailable`
  - `probe()`: `SELECT 1` for health
- [x] `exceptions.py` — DRF `APIException` subclasses with safe messages + `error_code`
  - `SourceNotConfigured` (503), `SourceUnavailable` (503), `SourceTimeout` (504), `SourceConfigurationError` (503), `SourceWriteForbidden`

### Services

- [x] `timeutils.py` — Australia/Sydney parsing (DST `fold`), presets (today, last 24h/48h/7d, previous calendar month), 12-month validation, bucket generation with zero-fill
- [x] `search.py` — Q builder (`setuptime` range first; match modes exact/startswith/endswith/contains OR'd across ingress/egress; IP-group `IN`; status incl. null), sort allow-list + `id DESC` tie-break, exact count then page, applied-filter summary
- [x] `detail.py` — SDR by `id`; every CDR by `sessionid` ordered `legid ASC NULLS LAST, id ASC` (no cap, D15); direction from `callorig`; tag parser (split on first `=`, preserve malformed); correlation anomaly checks with info/warning severity; `raw` / `display` separation
  - A CDR query timeout/failure must not lose the SDR: return the SDR with `cdrs: null` and a `cdrs_error` code (needed until `cdr(sessionid)` index exists)
- [x] `lookups.py` — cached DISTINCT ingress/egress IP groups (SDR only); termination reasons = DISTINCT over 4 SDR termination columns within the last `termination_lookup_days`
- [x] `statistics.py` — ORM aggregations: summary, timeseries, IP groups, top termination reasons; numeric-only duration averages + excluded counts; unknown `issuccess` bucket; cached
- [x] `field_help.py` — static AudioCodes 7.4 field/direction/termination/timing/media help, merged with overrides
- [x] `settings_service.py` — read/update settings, encrypt credential, bump `config_version`, cache keys versioned, `AuditService.record_event('cdr.settings.updated', …)` with no secrets

### API

- [x] `serializers.py` — input serializers (search, statistics, preferences, settings); `password` write-only with `has_password` flag; threshold validation (critical ≥ warning, unit required when thresholds set); output structures preserving raw values
- [x] `views.py` — base view: `permission_classes = [IsAppAdmin]`, `Cache-Control: no-store, private`, source-error translation

| View | Endpoint (prefix `/api/admin/cdr/`) |
|---|---|
| `SdrListView` | `GET sdr/` |
| `SdrDetailView` | `GET sdr/<int:sdr_id>/` |
| `IngressIpGroupLookupView` | `GET lookups/ingress-ip-groups/` |
| `EgressIpGroupLookupView` | `GET lookups/egress-ip-groups/` |
| `TerminationReasonLookupView` | `GET lookups/termination-reasons/` |
| `StatisticsSummaryView` | `GET statistics/summary/` |
| `StatisticsTimeseriesView` | `GET statistics/timeseries/` |
| `StatisticsIpGroupsView` | `GET statistics/ip-groups/` |
| `StatisticsTerminationReasonsView` | `GET statistics/termination-reasons/` |
| `DisplayConfigView` | `GET config/display/` |
| `PreferencesView` | `GET`, `PUT preferences/` |
| `ModuleSettingsView` | `GET`, `PUT settings/` |

- [x] `urls.py`

### Tests — `audiocodes_cdr/tests/`

- [x] `conftest.py` — create unmanaged tables via `schema_editor`, seed SDR/CDR rows, monkeypatch `activate_source`
- [x] `test_router.py` — writes raise, `allow_migrate` false, `pre_migrate` guard
- [x] `test_permissions.py` — endpoint permission coverage for anonymous/Standard User; CSRF on PUT
- [x] `test_search_validation.py` — missing/reversed range, >12 months, bad match mode/status/sort/page size, multi-select limit, TZ handling
- [x] `test_search_query.py` — AND/OR semantics, `setuptime` predicate first, default sort, exact count
- [x] `test_detail.py` — ordering, >2 legs, direction, tag parsing, correlation anomalies
- [x] `test_statistics.py` — zero-fill, DST, previous calendar month, invalid durations excluded + counted
- [x] `test_settings_api.py` — credential encrypted, never returned, audit event recorded, `config_version` bump
- [x] `test_crypto.py`
- [x] `test_health_source_status.py`

## 3. Backend — modify existing

- [x] [settings.py](../backend/telephony_toolbox/settings.py)
  - Add app to `INSTALLED_APPS`; `DATABASE_ROUTERS`
  - Placeholder `DATABASES['audiocodes_source']` (empty `NAME`, `TEST: {'MIRROR': 'default'}`)
  - `CDR_SOURCE_ENCRYPTION_KEY` env var
  - `CACHES = {'default': {'BACKEND': 'django.core.cache.backends.db.DatabaseCache', 'LOCATION': 'telephony_toolbox_cache'}}`
- [x] New `backend/telephony_toolbox/gunicorn_logging.py` — redacting Gunicorn `Logger` subclass, enabled by the deploy script via `--logger-class` (D6)
- [x] [urls.py](../backend/telephony_toolbox/urls.py) — `path('api/', include('audiocodes_cdr.urls'))`
- [x] [requirements.txt](../backend/requirements.txt) — add `cryptography`
- [x] [health/services.py](../backend/health/services.py) — AudioCodes source status in `build_admin_health_report()` only (generic messages); liveness unaffected
- [x] [test_healthcheck_api.py](../backend/health/tests/test_healthcheck_api.py) — assert liveness ignores source status
- [x] [middleware.py](../backend/telephony_toolbox/middleware.py) — redact query strings from CDR paths in timing logs (D6); Gunicorn and Nginx access logs are redacted by deployment configuration
- [x] [api.py](../backend/telephony_toolbox/api.py) — safety net maps unhandled CDR `DatabaseError` to a generic 503

## 4. Frontend — new files

### Pages

- [x] `src/pages/AdminCdrSearchPage.vue` — filter panel, server-side `q-table` (`@request`, default 100 rows), failure highlighting, View action, Clear / Reset to today
- [x] `src/pages/AdminCdrSessionPage.vue` — overview, call path, timing, termination, media/RTP, identifiers, additional SDR fields, anomalies, CDR leg cards
- [x] `src/pages/AdminCdrStatisticsPage.vue` — presets, bucket indicator, summary cards, ECharts, ISO-timestamp drill-down
- [x] `src/pages/AdminCdrSettingsPage.vue` — source profiles + active source, write-only password, limits, cache lifetimes, bucket threshold, user-defined labels, media thresholds, help overrides

### Pinia stores

- [x] `src/stores/cdrSearch.js` — filters, match modes, sort, page, page size, results, total; route-query sync; in-flight dedupe; `AbortController`
- [x] `src/stores/cdrStatistics.js` — preset/custom range, shared filters, results, loading
- [x] `src/stores/cdrLookups.js` — IP groups, termination reasons, error state
- [x] `src/stores/cdrDisplay.js` — display config (labels, thresholds, help) + duration preference via `PUT preferences/` (no localStorage)

### Services / utilities

- [x] `src/services/cdrApi.js` — endpoint functions using `api` from `boot/api`; accept `signal`
- [x] `src/utils/cdrFormat.js` — Sydney timestamp and duration formatters, null/blank/non-numeric safe, media status
- [x] `src/utils/cdrQuery.js` — filters ⇄ route query serialisation

### Components — `src/components/cdr/`

- [x] `CdrFilterPanel.vue` — shared by search and statistics
- [x] `CdrModuleTabs.vue` — Search / Statistics / Settings
- [x] `CdrSourceBanner.vue` — source unavailable / active source
- [x] `CdrStatusBadge.vue` — icon + text + colour; success / failure / unknown
- [x] `CdrTimestamp.vue` — connect-time fallback indicator
- [x] `CdrDuration.vue` — formatted value, raw tooltip, unformatted marker
- [x] `CdrCopyValue.vue` — Quasar `copyToClipboard`
- [x] `CdrFieldGrid.vue` — label / value / help; null renders blank
- [x] `CdrCallPath.vue` — ingress vs egress side by side
- [x] `CdrAnomalyList.vue`
- [x] `CdrLegCard.vue` — `q-expansion-item`, logical field groups
- [x] `CdrTagTable.vue` — parsed tags + original string
- [x] `CdrMediaMetric.vue` — threshold status (icon + text + colour)
- [x] `EChart.vue` — tree-shaken `echarts/core` wrapper, resize observer, click events

## 5. Frontend — modify existing

- [x] [package.json](../frontend/package.json) + `package-lock.json` — ECharts dependency
- [x] [routes.js](../frontend/src/router/routes.js) — `admin/cdr`, `admin/cdr/sessions/:id`, `admin/cdr/statistics`, `admin/cdr/settings`, admin-only route metadata
- [x] [MainLayout.vue](../frontend/src/layouts/MainLayout.vue) — AudioCodes CDR entry in admin navigation
- [x] [AdminHealthPage.vue](../frontend/src/pages/AdminHealthPage.vue) — AudioCodes source status card
- [x] [app.scss](../frontend/src/css/app.scss) — CDR-specific identifiers, status and threshold styles

## 6. Deployment / scripts

Verified by syntax check (`bash -n`) and by rendering the env, systemd and Nginx output in a sandbox. `nginx -t` has not been run locally; the script still validates with `nginx -t` and rolls back an invalid site on deployment.

- [x] [rhel-deploy-common.sh](../scripts/rhel-deploy-common.sh)
  - `ensure_cdr_source_encryption_key` generates `CDR_SOURCE_ENCRYPTION_KEY` (`openssl rand -base64 32 | tr '+/' '-_'`) when missing or blank; any non-empty value is left untouched. New env files include a commented placeholder.
  - Gunicorn: `--worker-class gthread --workers 4 --threads 4 --timeout 150 --logger-class telephony_toolbox.gunicorn_logging.RedactingLogger`
  - nginx `/api/`: `proxy_read_timeout 150s;` (`BACKEND_REQUEST_TIMEOUT` shared with Gunicorn)
  - nginx redaction: site-level `map $request_uri` / `map $http_referer` and a `log_format` (names derived from `NGINX_SITE_NAME`) that drop query strings for `/admin/cdr` and `/api/admin/cdr/`. `$request_uri` is used rather than `$uri` because SPA routes are rewritten to `/index.html`.
  - `run_migrations`: runs `manage.py createcachetable` after a successful `migrate`
- [x] [telephonytoolbox-gunicorn.service.template](../scripts/templates/telephonytoolbox-gunicorn.service.template) — same Gunicorn flags
- [x] [env.example](../scripts/env.example) — encryption key variable
- [x] [upgrade-rhel-baremetal-stage2.sh](../scripts/upgrade-rhel-baremetal-stage2.sh) picks up the changes through `write_backend_env`, `run_migrations`, `write_systemd_service` and `write_nginx_site` (summary text only updated); [install-rhel-baremetal-stage2.sh](../scripts/install-rhel-baremetal-stage2.sh) next steps mention `createcachetable` and key backup

## 7. Documentation

- [x] [ARCHITECTURE.md](ARCHITECTURE.md) — source alias, router/guards, data separation, query flow and operational differences
- [x] [API_SPECIFICATION.md](API_SPECIFICATION.md) — `/api/admin/cdr/` endpoints, validation, response shapes and error codes
- [x] [CONFIGURATION.md](CONFIGURATION.md) — encryption key, in-app settings, limits and cache
- [x] [DEPLOYMENT.md](DEPLOYMENT.md) — read-only PG role DBA steps, automated key/cache/timeout/log-redaction provisioning and source DB backup/migration exclusion
- [x] [DEVELOPMENT.md](DEVELOPMENT.md) — unmanaged-table fixtures, `manage.py createcachetable`, and local source guidance
- [x] [README.md](../README.md) — module summary and documentation links
- [x] [AUDIOCODES_CDR_INDEX_RECOMMENDATIONS.md](AUDIOCODES_CDR_INDEX_RECOMMENDATIONS.md) (spec §22.5) — SQL, rationale, `EXPLAIN (ANALYSE, BUFFERS)`, rollback

## 8. Implementation order

Mapped to spec §34. All stages are complete.

1. [x] Source protection + connection → source models → app DB models + migration
2. [x] Exceptions + base view → search + lookups → routes, stores, search page
3. [x] Detail service → session page + leg cards → formatting utilities
4. [x] Statistics service → statistics page + ECharts
5. [x] Settings service + audit → settings page
6. [x] Health, logging, deployment scripts, docs, index recommendations
7. [x] Verify (2026-10-07): `pytest` 243 passed, 1 pre-existing unrelated failure (`branding` `test_default_asset_is_blank_transparent_png`, caused by local `BRAND_*` overrides); ESLint passes; `npm run build` passes. `npm run lint:check` reports Prettier issues only in 6 pre-existing non-CDR files.
