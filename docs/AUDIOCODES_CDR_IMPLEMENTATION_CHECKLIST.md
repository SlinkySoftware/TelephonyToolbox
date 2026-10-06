# AudioCodes CDR Module — Implementation Checklist

Working checklist for implementing [audiocodes-cdr-manager-specification.md](audiocodes-cdr-manager-specification.md) inside Telephony Toolbox. Tick items as they land.

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
| F1 | Gunicorn `--timeout 60`, `sync`, 4 workers ([rhel-deploy-common.sh](../scripts/rhel-deploy-common.sh#L509)); nginx `/api/` has no `proxy_read_timeout` (default 60s) ([L572](../scripts/rhel-deploy-common.sh#L572)) | Count + page queries each get 60s → worker killed before a controlled timeout response; long queries can starve the whole app |
| F2 | No `CACHES` configured → per-worker LocMem | Lookup/stat caches are per worker; settings changes need cross-worker invalidation (`config_version`) or a shared cache |
| F3 | No `cryptography` in [requirements.txt](../backend/requirements.txt) | Needed for Fernet credential encryption |
| F4 | No `echarts`; deploy uses npm + `package-lock.json` (not pnpm) | Add via `npm install echarts` |
| F5 | [health/services.py](../backend/health/services.py) `_database_status()` returns `str(exc)` | New source check must return generic messages only |
| F6 | [middleware.py](../backend/telephony_toolbox/middleware.py) logs `get_full_path()`; gunicorn/nginx access logs log full request line | ANI/DNIS GET params leak into logs (spec §24) |
| F7 | `formatDateTime` in [format.js](../frontend/src/utils/format.js) uses browser TZ, no ms | Need an Australia/Sydney ms-precision formatter |
| F8 | Tests run on SQLite unless `DATABASE_NAME` is set | Unmanaged tables must be created in test fixtures; statistics must use ORM (`Trunc`, `Cast`, `__regex`) not raw PG SQL |
| F9 | Source credential lives in the app DB | Source DB alias must be registered/activated at runtime, not from env |
| F10 | No server-side `q-table` exists yet | Search page introduces the `@request` pattern |
| F11 | Sydney-truncated hourly buckets merge the two 02:00 hours at DST fall-back | Truncate hourly in UTC (Sydney offsets are whole hours); daily in Sydney |

## 1. Decisions

Status: **confirmed** (2026-10-06).

| ID | Decision | Answer |
|---|---|---|
| D1 | Source schema | Confirmed — see [Source schema mapping](#source-schema-mapping) |
| D1b | Source timestamp semantics | `timestamp with time zone` (absolute instants) |
| D1c | Existing source indexes | None beyond primary keys. Recommendations in [AUDIOCODES_CDR_INDEX_RECOMMENDATIONS.md](AUDIOCODES_CDR_INDEX_RECOMMENDATIONS.md); `cdr(sessionid)` is a prerequisite for usable session detail |
| D2 | "12 months" definition | 12 calendar months in Australia/Sydney (`end <= start + 12 months`, day clamped to month end) |
| D3 | Termination-reason lookup | Cached DISTINCT across the 4 SDR termination columns over a recent window; `termination_lookup_days` default 30 |
| D4 | Cache backend | Django `DatabaseCache` in the app PostgreSQL DB; `createcachetable` added to deploy |
| D5 | Gunicorn / nginx | `--worker-class gthread --workers 4 --threads 4 --timeout 150`; nginx `proxy_read_timeout 150s` |
| D6 | Log redaction | Strip query strings for `/api/admin/cdr/` (and SPA `/admin/cdr`) only, in perf middleware, gunicorn access log and nginx access log |
| D7 | Encryption key | `CDR_SOURCE_ENCRYPTION_KEY`, comma-separated `MultiFernet` (first key encrypts, all decrypt) |
| D7b | Key provisioning | Install/upgrade scripts generate the key only when absent; never overwrite |
| D8 | Source connectivity | Direct connection, no PgBouncer, server currently without TLS |
| D8b | `sslmode` | Selectable per profile (`disable`/`prefer`/`require`/`verify-ca`/`verify-full`), default `prefer` |
| D9 | Hourly/daily threshold | Hourly up to and including 7 days (`hourly_bucket_max_hours = 168`); daily beyond |
| D10 | Default duration format | `HH:MM:SS.ff` (`hms`) |
| D11 | Page sizes / multi-select | Page sizes 25/50/100/250/500, default 100, max 500; max 50 values per IP-group filter |
| D12 | Cache lifetimes | Lookups 900s, statistics 300s |
| D13 | Help content | Concise help written from public AudioCodes 7.4 SBC CDR documentation; no termination-reason explanations unless configured |
| D14 | Dev source DB | Test fixtures only (unmanaged tables created in the test DB) |

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

- [ ] `__init__.py`
- [ ] `apps.py` — `AudiocodesCdrConfig.ready()`: `connection_created` receiver (`SET statement_timeout=60000`, `SET default_transaction_read_only=on`), `pre_migrate` guard aborting when `using == 'audiocodes_source'`, system checks for encryption key
- [ ] `source_models.py` — unmanaged `Sdr`, `Cdr`
  - `managed = False`, `db_table = 'sdr'` / `'cdr'`, exact field names per spec §6
  - `ReadOnlySourceQuerySet` blocks `update` / `delete` / `bulk_create` / `select_for_update`; `save()` / `delete()` raise
- [ ] `models.py` — app DB models
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
- [ ] `migrations/0001_initial.py` (generated; unmanaged models create no DDL)

### Source protection & connection

- [ ] `routers.py` — `AudioCodesSourceRouter`
  - `db_for_read`: source models → `audiocodes_source`
  - `db_for_write`: source models → raise (never fall back to `default`)
  - `allow_relation`: `False` across source/app models
  - `allow_migrate`: `False` for the source alias and for source models
- [ ] `crypto.py` — `MultiFernet` built from comma-separated `CDR_SOURCE_ENCRYPTION_KEY`; first key encrypts, all decrypt; missing/invalid key fails closed
- [ ] `connection.py`
  - `activate_source()`: load active profile (cached by `config_version`), decrypt, populate `connections.settings['audiocodes_source']`, close stale connection on version change
  - Thread-safe for gthread workers (D5): lock around settings mutation; each thread's connection is stamped with the `config_version` it opened under and closed when stale
  - OPTIONS: `-c statement_timeout=60000 -c default_transaction_read_only=on -c search_path=public`, `application_name=telephony-toolbox-cdr`, `sslmode` from profile, `connect_timeout`; leave `server_side_binding` off (planner needs literal prefixes)
  - `source_errors()` context manager: `QueryCanceled` (statement timeout) → `SourceTimeout`; replica conflict-with-recovery cancellation → `SourceTimeout` with a retry hint; `OperationalError` → `SourceUnavailable`
  - `probe()`: `SELECT 1` for health
- [ ] `exceptions.py` — DRF `APIException` subclasses with safe messages + `error_code`
  - `SourceNotConfigured` (503), `SourceUnavailable` (503), `SourceTimeout` (504), `SourceConfigurationError` (503), `SourceWriteForbidden`

### Services

- [ ] `timeutils.py` — Australia/Sydney parsing (DST `fold`), presets (today, last 24h/48h/7d, previous calendar month), 12-month validation, bucket generation with zero-fill
- [ ] `search.py` — Q builder (`setuptime` range first; match modes exact/startswith/endswith/contains OR'd across ingress/egress; IP-group `IN`; status incl. null), sort allow-list + `id DESC` tie-break, exact count then page, applied-filter summary
- [ ] `detail.py` — SDR by `id`; CDRs by `sessionid` ordered `legid ASC NULLS LAST, id ASC`; direction from `callorig`; tag parser (split on first `=`, preserve malformed); 8 anomaly checks with info/warning severity; `raw` / `display` separation
  - A CDR query timeout/failure must not lose the SDR: return the SDR with `cdrs: null` and a `cdrs_error` code (needed until `cdr(sessionid)` index exists)
- [ ] `lookups.py` — cached DISTINCT ingress/egress IP groups (SDR only); termination reasons = DISTINCT over 4 SDR termination columns within the last `termination_lookup_days`
- [ ] `statistics.py` — ORM aggregations: summary, timeseries, IP groups, top termination reasons; numeric-only duration averages + excluded counts; unknown `issuccess` bucket; cached
- [ ] `field_help.py` — static AudioCodes 7.4 field/direction/termination/timing/media help, merged with overrides
- [ ] `settings_service.py` — read/update settings, encrypt credential, bump `config_version`, invalidate caches, `AuditService.record_event('cdr.settings.updated', …)` with no secrets

### API

- [ ] `serializers.py` — input serializers (search, statistics, preferences, settings); `password` write-only with `has_password` flag; threshold validation (critical ≥ warning, unit required when thresholds set); output serializers preserving raw values
- [ ] `views.py` — base view: `permission_classes = [IsAppAdmin]`, `Cache-Control: no-store, private`, source-error translation

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

- [ ] `urls.py`

### Tests — `audiocodes_cdr/tests/`

- [ ] `conftest.py` — create unmanaged tables via `schema_editor`, seed SDR/CDR rows, monkeypatch `activate_source`
- [ ] `test_router.py` — writes raise, `allow_migrate` false, `pre_migrate` guard
- [ ] `test_permissions.py` — every endpoint: 401 anonymous, 403 Standard User; CSRF on PUT
- [ ] `test_search_validation.py` — missing/reversed range, >12 months, bad match mode/status/sort/page size, multi-select limit, TZ handling
- [ ] `test_search_query.py` — AND/OR semantics, `setuptime` predicate first, default sort, exact count
- [ ] `test_detail.py` — ordering, >2 legs, direction, tag parsing, every anomaly
- [ ] `test_statistics.py` — zero-fill, DST transition days, previous calendar month, invalid durations excluded + counted
- [ ] `test_settings_api.py` — credential encrypted, never returned, audit event recorded, `config_version` bump
- [ ] `test_crypto.py`
- [ ] `test_health_source_status.py`

## 3. Backend — modify existing

- [ ] [settings.py](../backend/telephony_toolbox/settings.py)
  - Add app to `INSTALLED_APPS`; `DATABASE_ROUTERS`
  - Placeholder `DATABASES['audiocodes_source']` (empty `NAME`, `TEST: {'MIRROR': 'default'}`)
  - `CDR_SOURCE_ENCRYPTION_KEY` env var
  - `CACHES = {'default': {'BACKEND': 'django.core.cache.backends.db.DatabaseCache', 'LOCATION': 'telephony_toolbox_cache'}}`
- [ ] New `backend/telephony_toolbox/gunicorn_logging.py` — gunicorn `Logger` subclass that drops the query string from access-log lines for `/api/admin/cdr/` (D6)
- [ ] [urls.py](../backend/telephony_toolbox/urls.py) — `path('api/', include('audiocodes_cdr.urls'))`
- [ ] [requirements.txt](../backend/requirements.txt) — add `cryptography`
- [ ] [health/services.py](../backend/health/services.py) — AudioCodes source status in `build_admin_health_report()` only (generic messages); liveness unaffected
- [ ] [test_healthcheck_api.py](../backend/health/tests/test_healthcheck_api.py) — assert liveness ignores source status
- [ ] [middleware.py](../backend/telephony_toolbox/middleware.py) — log `request.path` instead of `get_full_path()` for `/api/admin/cdr/` (D6)
- [ ] [api.py](../backend/telephony_toolbox/api.py) — optional safety net mapping unhandled source `DatabaseError` → 503

## 4. Frontend — new files

### Pages

- [ ] `src/pages/AdminCdrSearchPage.vue` — filter panel, server-side `q-table` (`@request`, default 100 rows), failure highlighting, View action, Clear / Reset to today
- [ ] `src/pages/AdminCdrSessionPage.vue` — overview, call path, timing, termination, media/RTP, identifiers, additional SDR fields, anomalies, CDR leg cards
- [ ] `src/pages/AdminCdrStatisticsPage.vue` — presets, bucket indicator, summary cards, ECharts, ISO-timestamp drill-down
- [ ] `src/pages/AdminCdrSettingsPage.vue` — source profiles + active source, write-only password, limits, cache lifetimes, bucket threshold, user-defined labels, media thresholds, help overrides

### Pinia stores

- [ ] `src/stores/cdrSearch.js` — filters, match modes, sort, page, page size, results, total; route-query sync; in-flight dedupe; `AbortController`
- [ ] `src/stores/cdrStatistics.js` — preset/custom range, shared filters, results, loading
- [ ] `src/stores/cdrLookups.js` — IP groups, termination reasons, error state
- [ ] `src/stores/cdrDisplay.js` — display config (labels, thresholds, help) + duration preference via `PUT preferences/` (no localStorage)

### Services / utilities

- [ ] `src/services/cdrApi.js` — endpoint functions using `api` from `boot/api`; accept `signal`
- [ ] `src/utils/cdrFormat.js` — `formatSydneyTimestamp` (`DD/MM/YYYY HH:mm:ss.SSS z`), `formatDuration` (hundredths; null/blank/non-numeric safe), `mediaStatus`
- [ ] `src/utils/cdrQuery.js` — filters ⇄ route query serialisation

### Components — `src/components/cdr/`

- [ ] `CdrFilterPanel.vue` — shared by search and statistics
- [ ] `CdrModuleTabs.vue` — Search / Statistics / Settings
- [ ] `CdrSourceBanner.vue` — source unavailable / active source
- [ ] `CdrStatusBadge.vue` — icon + text + colour; success / failure / unknown
- [ ] `CdrTimestamp.vue` — connect-time fallback indicator
- [ ] `CdrDuration.vue` — formatted value, raw tooltip, unformatted marker
- [ ] `CdrCopyValue.vue` — Quasar `copyToClipboard`
- [ ] `CdrFieldGrid.vue` — label / value / help; null renders blank
- [ ] `CdrCallPath.vue` — ingress vs egress side by side
- [ ] `CdrAnomalyList.vue`
- [ ] `CdrLegCard.vue` — `q-expansion-item`, 7 field groups
- [ ] `CdrTagTable.vue` — parsed tags + original string
- [ ] `CdrMediaMetric.vue` — threshold status (icon + text + colour)
- [ ] `EChart.vue` — tree-shaken `echarts/core` wrapper, resize observer, click events

## 5. Frontend — modify existing

- [ ] [package.json](../frontend/package.json) + `package-lock.json` — `npm install echarts`
- [ ] [routes.js](../frontend/src/router/routes.js) — `admin/cdr`, `admin/cdr/sessions/:id` (`props: true`), `admin/cdr/statistics`, `admin/cdr/settings`, all `meta: { adminOnly: true }`
- [ ] [MainLayout.vue](../frontend/src/layouts/MainLayout.vue) — "AudioCodes CDR" entry in `adminLinks` (review `exact` for child-route highlighting)
- [ ] [AdminHealthPage.vue](../frontend/src/pages/AdminHealthPage.vue) — AudioCodes source status card
- [ ] [app.scss](../frontend/src/css/app.scss) — monospace identifiers, status / threshold classes

## 6. Deployment / scripts

- [ ] [rhel-deploy-common.sh](../scripts/rhel-deploy-common.sh)
  - Generate `CDR_SOURCE_ENCRYPTION_KEY` only when absent, never overwrite (near [L401](../scripts/rhel-deploy-common.sh#L401)); Fernet key without Python: `openssl rand -base64 32 | tr '+/' '-_'`
  - Gunicorn ([L509](../scripts/rhel-deploy-common.sh#L509)): `--worker-class gthread --workers 4 --threads 4 --timeout 150 --logger-class telephony_toolbox.gunicorn_logging.RedactingLogger`
  - nginx `/api/` ([L572](../scripts/rhel-deploy-common.sh#L572)): `proxy_read_timeout 150s;`
  - nginx redaction: site-file-level `map $request_uri` + uniquely named `log_format` that logs `$uri` (no query) for `/api/admin/cdr/` and `/admin/cdr`; use it on `access_log`
  - `run_migrations`: add `manage.py createcachetable`
- [ ] [env.example](../scripts/env.example) — encryption key variable
- [ ] Verify [upgrade-rhel-baremetal-stage2.sh](../scripts/upgrade-rhel-baremetal-stage2.sh) picks up changes via `write_backend_env` (expected: no edit)

## 7. Documentation

- [ ] [ARCHITECTURE.md](ARCHITECTURE.md) — source alias, router/guards, data separation
- [ ] [API_SPECIFICATION.md](API_SPECIFICATION.md) — `/api/admin/cdr/` endpoints and error codes
- [ ] [CONFIGURATION.md](CONFIGURATION.md) — encryption key, settings page, limits
- [ ] [DEPLOYMENT.md](DEPLOYMENT.md) — read-only PG role DBA steps, timeouts, source DB excluded from backup/migration
- [ ] [DEVELOPMENT.md](DEVELOPMENT.md) — unmanaged-table test fixtures, `manage.py createcachetable` for local dev, no dev source DB (D14)
- [ ] [README.md](../README.md) — module summary
- [x] [AUDIOCODES_CDR_INDEX_RECOMMENDATIONS.md](AUDIOCODES_CDR_INDEX_RECOMMENDATIONS.md) (spec §22.5) — SQL, rationale, `EXPLAIN (ANALYSE, BUFFERS)`, rollback

## 8. Implementation order

Mapped to spec §34.

1. Source protection + connection → source models → app DB models + migration
2. Exceptions + base view → search + lookups → routes, stores, search page
3. Detail service → session page + leg cards → formatting utilities
4. Statistics service → statistics page + ECharts
5. Settings service + audit → settings page
6. Health, logging, deployment scripts, docs, index recommendations
7. Verify: `pytest`, `npm run lint:check`, `npm run build`
