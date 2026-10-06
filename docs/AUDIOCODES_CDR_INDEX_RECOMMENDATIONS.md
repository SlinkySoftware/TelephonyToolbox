# AudioCodes CDR Source — Index Recommendations

Recommendations for the AudioCodes SDR/CDR source database (PostgreSQL 17) used by the Telephony Toolbox AudioCodes CDR module. See [audiocodes-cdr-manager-specification.md](audiocodes-cdr-manager-specification.md) §22.5.

> **The application never creates, alters or drops source indexes.** Everything in this document is a recommendation for the source-database DBA, to be applied (or not) through the DBA's own change process, on the **primary**, using a privileged account — never the application's read-only account.

## Table of Contents

1. [Current State](#current-state)
2. [Summary](#summary)
3. [Pre-flight Checks](#pre-flight-checks)
4. [Build Procedure](#build-procedure)
5. [IDX-1 cdr(sessionid)](#idx-1--cdrsessionid)
6. [IDX-2 sdr(setuptime, id)](#idx-2--sdrsetuptime-desc-id-desc)
7. [IDX-3 / IDX-4 SDR IP groups](#idx-3--idx-4--sdringressipgroup-sdregressipgroup)
8. [IDX-5 to IDX-8 ANI / DNIS](#idx-5-to-idx-8--ani--dnis-prefix-indexes)
9. [IDX-9 / IDX-10 Call-ID](#idx-9--idx-10--call-id-indexes)
10. [Not Recommended](#not-recommended)
11. [Behaviour Without Indexes](#behaviour-without-indexes)
12. [Full Rollback](#full-rollback)

## Current State

- `public.sdr` — ~5.93M rows, ~1,000 inserts/day, only the primary key `sdrid_pkey (id)`.
- `public.cdr` — ~1.23B rows, ~2,500 inserts/day, only the primary key `cdrid_pkey (id)`.
- No secondary indexes exist on either table.
- All timestamp columns are `timestamp with time zone`.
- All text columns are `varchar(255)`.

## Summary

| ID | Index | Priority | Serves | Est. size |
|---|---|---|---|---|
| IDX-1 | `cdr (sessionid)` | **P0 — prerequisite** | Session detail CDR retrieval | Tens of GB (measure) |
| IDX-2 | `sdr (setuptime DESC, id DESC)` | **P1 — strongly recommended** | Every search, count, statistics query | ~150–250 MB |
| IDX-3 | `sdr (ingressipgroup)` | P2 — recommended | Ingress IP-group lookup refresh, IP-group filter | Small (deduplicated) |
| IDX-4 | `sdr (egressipgroup)` | P2 — recommended | Egress IP-group lookup refresh, IP-group filter | Small (deduplicated) |
| IDX-5–8 | `sdr (ingressani / egressani / ingressdnis / egressdnis varchar_pattern_ops)` | P3 — evidence-based | Exact / starts-with number search over long ranges | ~150–300 MB each |
| IDX-9–10 | `sdr (ingresscallid / egresscallid varchar_pattern_ops)` | P3 — evidence-based | Exact / starts-with Call-ID search over long ranges | ~300–500 MB each |

Apply IDX-1 and IDX-2 before production use. Apply IDX-3/4 at the same time (cheap). Apply IDX-5 to IDX-10 only if `EXPLAIN (ANALYSE, BUFFERS)` on real searches shows they are needed.

## Pre-flight Checks

Run as the read-only account (all are `SELECT`s):

```sql
-- Table and existing index sizes
SELECT relname,
       pg_size_pretty(pg_table_size(oid))   AS table_size,
       pg_size_pretty(pg_indexes_size(oid)) AS index_size
FROM pg_class
WHERE oid IN ('public.sdr'::regclass, 'public.cdr'::regclass);

-- Collation: if not "C"/"POSIX", LIKE 'prefix%' needs varchar_pattern_ops (IDX-5 to IDX-10)
SELECT datcollate, datctype FROM pg_database WHERE datname = current_database();

-- Column width and distinctness, used for size estimates below
SELECT tablename, attname, avg_width, n_distinct, null_frac
FROM pg_stats
WHERE schemaname = 'public'
  AND (tablename, attname) IN (
    ('cdr','sessionid'),
    ('sdr','setuptime'), ('sdr','ingressipgroup'), ('sdr','egressipgroup'),
    ('sdr','ingressani'), ('sdr','egressani'), ('sdr','ingressdnis'), ('sdr','egressdnis'),
    ('sdr','ingresscallid'), ('sdr','egresscallid')
  )
ORDER BY 1, 2;
```

Rough B-tree size estimate (before deduplication):

```text
size_bytes ≈ row_count × (avg_width + 16) / 0.9
```

B-tree deduplication (PostgreSQL 13+) shrinks indexes substantially where values repeat (`n_distinct` small relative to row count) — IP groups especially.

## Build Procedure

Applies to every index below.

1. Build on the **primary**. Indexes reach replicas through WAL; `CREATE INDEX` cannot run on a hot standby.
2. Use a privileged DBA session — never the application's read-only account.
3. Use `CONCURRENTLY` so live ingestion is never blocked. It cannot run inside a transaction block.
4. Schedule off-peak. A concurrent build of IDX-1 on 1.2B rows can take hours and generates WAL roughly equal to the index size, which increases replica lag while it runs.
5. Session settings:

   ```sql
   SET statement_timeout = 0;
   SET lock_timeout = '5s';
   SET maintenance_work_mem = '2GB';          -- size to available RAM
   SET max_parallel_maintenance_workers = 4;  -- size to available cores
   ```

6. Monitor progress from another session:

   ```sql
   SELECT phase, blocks_done, blocks_total, tuples_done, tuples_total
   FROM pg_stat_progress_create_index;
   ```

7. Confirm the index is valid. A failed concurrent build leaves an `INVALID` index that must be dropped and rebuilt:

   ```sql
   SELECT c.relname, i.indisvalid, i.indisready
   FROM pg_index i JOIN pg_class c ON c.oid = i.indexrelid
   WHERE i.indrelid IN ('public.sdr'::regclass, 'public.cdr'::regclass);
   ```

8. Run `ANALYZE public.sdr;` / `ANALYZE public.cdr;` (the CDR `ANALYZE` samples, so it is not a full scan).
9. Confirm the index exists on the replica and replica lag has recovered before relying on it.

## IDX-1 — `cdr (sessionid)`

**Priority:** P0 — prerequisite for the session detail page.

```sql
CREATE INDEX CONCURRENTLY IF NOT EXISTS cdr_sessionid_idx
    ON public.cdr (sessionid);
```

- **Reason:** CDRs are correlated to an SDR solely by `cdr.sessionid = sdr.sessionid` (spec §10.1). Without an index each lookup is a sequential scan of ~1.2B rows, which will always exceed the 60-second statement timeout.
- **Affected query:**

  ```sql
  SELECT ... FROM public.cdr
  WHERE sessionid = $1
  ORDER BY legid ASC NULLS LAST, id ASC;
  ```

- **Expected benefit:** Index scan touching a handful of pages. Milliseconds instead of a guaranteed timeout. The `ORDER BY` sorts only the few matching rows, so `legid` / `id` are deliberately **not** added to the key — keeping the key single-column preserves B-tree deduplication and minimises size.
- **Storage impact:** The largest index proposed. Estimate with the formula above using `pg_stats.avg_width` for `cdr.sessionid` — e.g. a 20-byte average width gives roughly 45–50 GB before deduplication. Ensure free space for the index plus temporary sort files during the build.
- **Write impact:** Negligible at ~2,500 inserts/day.
- **Alternative if storage is critical:** `USING hash (sessionid)` — equality-only, WAL-logged and replicated since PostgreSQL 10, roughly constant ~16–20 bytes per row regardless of key length, but no deduplication. Prefer B-tree unless measured size is unacceptable.
- **Validation:**

  ```sql
  EXPLAIN (ANALYSE, BUFFERS)
  SELECT * FROM public.cdr
  WHERE sessionid = '<a known sessionid>'
  ORDER BY legid ASC NULLS LAST, id ASC;
  ```

  Expect `Index Scan` or `Bitmap Index Scan using cdr_sessionid_idx` and shared buffers in the tens, not millions.

- **Rollback:**

  ```sql
  DROP INDEX CONCURRENTLY IF EXISTS public.cdr_sessionid_idx;
  ```

## IDX-2 — `sdr (setuptime DESC, id DESC)`

**Priority:** P1 — strongly recommended.

```sql
CREATE INDEX CONCURRENTLY IF NOT EXISTS sdr_setuptime_id_desc_idx
    ON public.sdr (setuptime DESC, id DESC);
```

- **Reason:** Every search, count and statistics query starts with the mandatory bounded predicate `setuptime >= $start AND setuptime < $end` (spec §22.1). The default sort is `setuptime DESC, id DESC` (spec §15.6).
- **Affected queries:**
  - SDR search page: `WHERE setuptime >= $1 AND setuptime < $2 [AND ...] ORDER BY setuptime DESC, id DESC LIMIT $n OFFSET $m`.
  - Exact count: `SELECT count(*) FROM public.sdr WHERE setuptime >= $1 AND setuptime < $2 [AND ...]`.
  - Statistics: aggregations bucketed by `setuptime` over the same range.
  - Termination-reason lookup: DISTINCT over the last 30 days.
- **Expected benefit:**
  - Range scans read only the requested window instead of the whole table.
  - Default-sorted pages are returned in index order with no sort step.
  - Unfiltered counts can use an index-only scan.
  - A "today" search becomes milliseconds; a 12-month search reads only that year's entries.
- **Storage impact:** ~5.9M × (16 + 16) / 0.9 ≈ 200 MB.
- **Write impact:** Negligible at ~1,000 inserts/day. New rows are appended at the "latest" end of the index.
- **Validation:**

  ```sql
  EXPLAIN (ANALYSE, BUFFERS)
  SELECT id, setuptime, ingressani, egressani
  FROM public.sdr
  WHERE setuptime >= now() - interval '1 day' AND setuptime < now()
  ORDER BY setuptime DESC, id DESC
  LIMIT 100;

  EXPLAIN (ANALYSE, BUFFERS)
  SELECT count(*) FROM public.sdr
  WHERE setuptime >= now() - interval '12 months' AND setuptime < now();
  ```

  Expect `Index Scan using sdr_setuptime_id_desc_idx` with no `Sort` node for the first query, and an `Index Only Scan` (or bitmap scan) for the count.

- **Rollback:**

  ```sql
  DROP INDEX CONCURRENTLY IF EXISTS public.sdr_setuptime_id_desc_idx;
  ```

## IDX-3 / IDX-4 — `sdr (ingressipgroup)`, `sdr (egressipgroup)`

**Priority:** P2 — recommended.

```sql
CREATE INDEX CONCURRENTLY IF NOT EXISTS sdr_ingressipgroup_idx
    ON public.sdr (ingressipgroup);

CREATE INDEX CONCURRENTLY IF NOT EXISTS sdr_egressipgroup_idx
    ON public.sdr (egressipgroup);
```

- **Reason:** IP-group drop-downs are populated from all distinct values in the SDR table (spec §14), refreshed every 15 minutes (configurable). Without an index each refresh is a full sequential scan of the SDR heap.
- **Affected queries:**
  - Lookup refresh: `SELECT DISTINCT ingressipgroup FROM public.sdr WHERE ingressipgroup IS NOT NULL AND ingressipgroup <> '' ORDER BY 1` (and the egress equivalent).
  - IP-group filter: `ingressipgroup = ANY($1)` alongside the `setuptime` range.
- **Expected benefit:**
  - The lookup becomes an index-only scan of a heavily deduplicated index (few distinct values), instead of reading the full table.
  - For selective IP groups over long ranges, the planner can combine this index with IDX-2.
- **Storage impact:** Small. With few distinct values, deduplication typically gives single- to low-double-digit MB per index.
- **Write impact:** Negligible.
- **Validation:**

  ```sql
  EXPLAIN (ANALYSE, BUFFERS)
  SELECT DISTINCT ingressipgroup FROM public.sdr
  WHERE ingressipgroup IS NOT NULL AND ingressipgroup <> ''
  ORDER BY 1;
  ```

  Expect `Index Only Scan using sdr_ingressipgroup_idx` with `Heap Fetches` near zero (requires an up-to-date visibility map; autovacuum handles insert-only tables in PostgreSQL 13+).

- **Rollback:**

  ```sql
  DROP INDEX CONCURRENTLY IF EXISTS public.sdr_ingressipgroup_idx;
  DROP INDEX CONCURRENTLY IF EXISTS public.sdr_egressipgroup_idx;
  ```

## IDX-5 to IDX-8 — ANI / DNIS prefix indexes

**Priority:** P3 — apply only on evidence.

```sql
CREATE INDEX CONCURRENTLY IF NOT EXISTS sdr_ingressani_pattern_idx
    ON public.sdr (ingressani varchar_pattern_ops);
CREATE INDEX CONCURRENTLY IF NOT EXISTS sdr_egressani_pattern_idx
    ON public.sdr (egressani varchar_pattern_ops);
CREATE INDEX CONCURRENTLY IF NOT EXISTS sdr_ingressdnis_pattern_idx
    ON public.sdr (ingressdnis varchar_pattern_ops);
CREATE INDEX CONCURRENTLY IF NOT EXISTS sdr_egressdnis_pattern_idx
    ON public.sdr (egressdnis varchar_pattern_ops);
```

- **Reason:** ANI and DNIS searches OR the ingress and egress columns (spec §13.3). With these indexes, exact and starts-with matches can use a `BitmapOr` of two index scans. `varchar_pattern_ops` is required for `LIKE 'prefix%'` unless the database collation is `C`; it also serves `=`.
- **Why not P1/P2:** Every search is bounded by `setuptime` (IDX-2). For typical ranges (a day to a few weeks, thousands to tens of thousands of SDRs), filtering the range rows is already fast. These indexes help mainly when a selective number is searched over a long range (months), where IDX-2 alone reads hundreds of thousands of rows.
- **Contains / ends-with:** Not served by these indexes. They rely on the bounded `setuptime` scan and the 60-second timeout, as the spec permits (§22.2).
- **Affected query:** `... AND (ingressani LIKE $1 OR egressani LIKE $1)` where `$1` is `'value'` or `'value%'`.
- **Application requirement:** Django's psycopg 3 backend uses client-side parameter binding by default, so the literal prefix is visible to the planner. Keep `server_side_binding` disabled for the source connection.
- **Storage impact:** ~5.9M × (avg_width + 16) / 0.9 — roughly 150–300 MB each.
- **Write impact:** Negligible.
- **When to apply:** If `EXPLAIN (ANALYSE, BUFFERS)` of real exact or starts-with searches over long ranges approaches the 60-second timeout, or shows excessive buffers from IDX-2 range scans.
- **Validation:**

  ```sql
  EXPLAIN (ANALYSE, BUFFERS)
  SELECT id FROM public.sdr
  WHERE setuptime >= now() - interval '12 months' AND setuptime < now()
    AND (ingressani LIKE '0291234%' OR egressani LIKE '0291234%')
  ORDER BY setuptime DESC, id DESC
  LIMIT 100;
  ```

  Expect `BitmapOr` over the two ANI indexes (possibly `BitmapAnd` with IDX-2), and fewer buffers than the IDX-2-only plan.

- **Rollback:**

  ```sql
  DROP INDEX CONCURRENTLY IF EXISTS public.sdr_ingressani_pattern_idx;
  DROP INDEX CONCURRENTLY IF EXISTS public.sdr_egressani_pattern_idx;
  DROP INDEX CONCURRENTLY IF EXISTS public.sdr_ingressdnis_pattern_idx;
  DROP INDEX CONCURRENTLY IF EXISTS public.sdr_egressdnis_pattern_idx;
  ```

## IDX-9 / IDX-10 — Call-ID indexes

**Priority:** P3 — apply only on evidence.

```sql
CREATE INDEX CONCURRENTLY IF NOT EXISTS sdr_ingresscallid_pattern_idx
    ON public.sdr (ingresscallid varchar_pattern_ops);
CREATE INDEX CONCURRENTLY IF NOT EXISTS sdr_egresscallid_pattern_idx
    ON public.sdr (egresscallid varchar_pattern_ops);
```

- **Reason:** Call-ID search defaults to exact match (spec §13.2), and Call-IDs are near-unique. An engineer pasting a Call-ID from a SIP trace with a wide date range is the most likely long-range search.
- **Affected query:** `... AND (ingresscallid = $1 OR egresscallid = $1)` (or `LIKE 'prefix%'`).
- **Expected benefit:** Near-instant lookup regardless of range width.
- **Storage impact:** Call-IDs are long (often 30–60+ characters), so these are among the larger SDR indexes — roughly 300–500 MB each.
- **Write impact:** Negligible.
- **When to apply:** If engineers routinely search Call-IDs across ranges longer than a few weeks.
- **Validation:** As for IDX-5, substituting `ingresscallid = '<call-id>' OR egresscallid = '<call-id>'`.
- **Rollback:**

  ```sql
  DROP INDEX CONCURRENTLY IF EXISTS public.sdr_ingresscallid_pattern_idx;
  DROP INDEX CONCURRENTLY IF EXISTS public.sdr_egresscallid_pattern_idx;
  ```

## Not Recommended

| Candidate | Reason |
|---|---|
| `pg_trgm` GIN indexes on ANI / DNIS / Call-ID | Requires `CREATE EXTENSION` on the source and adds hundreds of MB per column. Contains/ends-with searches are bounded by `setuptime` and the 60s timeout. Revisit only if bounded contains searches routinely time out. |
| `reverse(col)` expression indexes for ends-with | Requires a non-standard query shape; same reasoning as trigram. |
| `sdr (issuccess)` | Three values; never selective enough to beat IDX-2. |
| SDR termination-reason columns | The lookup is limited to the last 30 days via IDX-2. The text filter is applied to range rows. |
| Composite `sdr (setuptime) INCLUDE (...)` for statistics | Statistics already read only the bounded range through IDX-2; covering indexes would duplicate most of the row. |
| `sdr (sessionid)`, `sdr (globalsessionid)` | Detail pages load SDRs by primary key; Global Session ID is display/diagnostic only (spec §10.2). |
| Any other `cdr` index (`globalsessionid`, `callid`, `ipgroupname`, ...) | Independent CDR search is Phase 2 (spec §13.4). Each index on 1.2B rows costs tens of GB. |
| `cdr (sessionid, legid, id)` | Defeats B-tree deduplication and increases size; the per-session sort is trivial. |

## Behaviour Without Indexes

The module still works without these indexes, but with the following consequences:

| Missing | Effect |
|---|---|
| IDX-1 | The session detail page shows the SDR, but CDR retrieval always hits the 60s statement timeout and shows a controlled "CDR legs unavailable (query timed out)" message. |
| IDX-2 | Every search runs two sequential scans of `sdr` (count + page); statistics do the same. These probably complete within 60s but add significant I/O load on the replica. |
| IDX-3/4 | Each IP-group lookup refresh (every 15 min by default, shared across workers via the database cache) runs sequential scans of `sdr`. |
| IDX-5–10 | Long-range number and Call-ID searches rely on the IDX-2 range scan. |

## Full Rollback

```sql
DROP INDEX CONCURRENTLY IF EXISTS public.cdr_sessionid_idx;
DROP INDEX CONCURRENTLY IF EXISTS public.sdr_setuptime_id_desc_idx;
DROP INDEX CONCURRENTLY IF EXISTS public.sdr_ingressipgroup_idx;
DROP INDEX CONCURRENTLY IF EXISTS public.sdr_egressipgroup_idx;
DROP INDEX CONCURRENTLY IF EXISTS public.sdr_ingressani_pattern_idx;
DROP INDEX CONCURRENTLY IF EXISTS public.sdr_egressani_pattern_idx;
DROP INDEX CONCURRENTLY IF EXISTS public.sdr_ingressdnis_pattern_idx;
DROP INDEX CONCURRENTLY IF EXISTS public.sdr_egressdnis_pattern_idx;
DROP INDEX CONCURRENTLY IF EXISTS public.sdr_ingresscallid_pattern_idx;
DROP INDEX CONCURRENTLY IF EXISTS public.sdr_egresscallid_pattern_idx;
```

Dropping indexes never affects source data; the application continues to function with the degraded behaviour described above.
