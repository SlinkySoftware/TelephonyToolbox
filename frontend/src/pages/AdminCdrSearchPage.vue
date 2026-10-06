<!--
SPDX-FileCopyrightText: Copyright 2026, Slinky Software
SPDX-License-Identifier: GPL-3.0-only
-->

<template>
  <q-page class="page-frame soft-grid">
    <section class="page-hero">
      <div class="section-kicker">App Admin · AudioCodes CDR</div>
      <h1 class="page-title">SDR Search</h1>
      <p class="page-subtitle">
        Search AudioCodes Session Detail Records by setup time. The source data is read-only.
      </p>
    </section>

    <CdrModuleTabs />
    <CdrSourceBanner :error="search.error" retry @retry="retry" />

    <section class="form-panel q-pa-lg" aria-label="Search filters">
      <CdrFilterPanel
        v-model="draft"
        show-reset
        :server-errors="search.error?.fieldErrors"
        @submit="submitSearch"
        @clear="clearFilters"
        @reset="resetToToday"
      />
    </section>

    <section class="table-panel q-pa-md" aria-label="Search results">
      <div class="cdr-results-header">
        <div>
          <h2 class="cdr-section-title">Results</h2>
          <div class="muted-copy" aria-live="polite">{{ resultSummary }}</div>
        </div>
        <div v-if="appliedChips.length" class="cdr-applied" aria-label="Applied filters">
          <q-chip v-for="chip in appliedChips" :key="chip" dense square class="cdr-applied__chip">
            {{ chip }}
          </q-chip>
        </div>
      </div>

      <q-banner
        v-if="search.error && !search.error.sourceIssue && !search.error.timeout"
        dense
        rounded
        class="cdr-banner cdr-banner--danger q-mb-md"
        role="alert"
      >
        <template #avatar><q-icon name="error_outline" /></template>
        {{ search.error.message }}
      </q-banner>

      <q-table
        v-model:pagination="pagination"
        class="cdr-results-table"
        :rows="search.results"
        :columns="columns"
        row-key="id"
        flat
        dense
        binary-state-sort
        :loading="search.loading"
        :rows-per-page-options="display.pageSizeOptions"
        rows-per-page-label="SDRs per page"
        :table-row-class-fn="rowClass"
        @request="onRequest"
      >
        <template #body-cell-setuptime="props">
          <q-td :props="props" class="cdr-nowrap">
            <CdrTimestamp
              :value="props.row.display?.effective_start"
              :source="props.row.display?.effective_start_source"
            />
          </q-td>
        </template>

        <template #body-cell-callduration="props">
          <q-td :props="props" class="cdr-nowrap">
            <CdrDuration :value="props.row.callduration" />
          </q-td>
        </template>

        <template #body-cell-issuccess="props">
          <q-td :props="props" class="cdr-nowrap">
            <CdrStatusBadge :outcome="props.row.display?.outcome" />
          </q-td>
        </template>

        <template #body-cell-termination="props">
          <q-td :props="props" class="cdr-termination-cell">
            <div
              v-for="entry in props.row.display?.termination_summary || []"
              :key="entry.value"
              class="cdr-termination-entry"
            >
              <span>{{ entry.value }}</span>
              <span class="cdr-termination-entry__fields">{{ terminationFields(entry) }}</span>
            </div>
          </q-td>
        </template>

        <template #body-cell-actions="props">
          <q-td :props="props">
            <q-btn
              flat
              dense
              no-caps
              color="primary"
              icon="visibility"
              label="View"
              :to="`/admin/cdr/sessions/${props.row.id}`"
              :aria-label="`View SDR ${props.row.id}`"
            />
          </q-td>
        </template>

        <template #no-data>
          <div class="cdr-empty full-width">
            <q-icon :name="search.error ? 'error_outline' : 'search_off'" size="1.6rem" />
            <div>{{ emptyMessage }}</div>
          </div>
        </template>
      </q-table>
    </section>
  </q-page>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import CdrDuration from 'src/components/cdr/CdrDuration.vue'
import CdrFilterPanel from 'src/components/cdr/CdrFilterPanel.vue'
import CdrModuleTabs from 'src/components/cdr/CdrModuleTabs.vue'
import CdrSourceBanner from 'src/components/cdr/CdrSourceBanner.vue'
import CdrStatusBadge from 'src/components/cdr/CdrStatusBadge.vue'
import CdrTimestamp from 'src/components/cdr/CdrTimestamp.vue'
import { useCdrDisplayStore } from 'src/stores/cdrDisplay'
import { useCdrLookupsStore } from 'src/stores/cdrLookups'
import { useCdrSearchStore } from 'src/stores/cdrSearch'
import { TERMINATION_FIELD_SHORT_LABELS } from 'src/utils/cdrFields'
import { formatCount, formatSydneyTimestamp } from 'src/utils/cdrFormat'
import {
  DEFAULT_DIRECTION,
  DEFAULT_SORT,
  MATCH_MODE_OPTIONS,
  STATUS_OPTIONS,
  cloneFilters,
  defaultFilters,
  emptyCriteria,
  hasQuery,
  sameQuery,
  searchStateFromQuery,
  searchStateToQuery,
} from 'src/utils/cdrQuery'

const SEARCH_PATH = '/admin/cdr'

const route = useRoute()
const router = useRouter()
const display = useCdrDisplayStore()
const lookups = useCdrLookupsStore()
const search = useCdrSearchStore()

const draft = ref(search.filters ? cloneFilters(search.filters) : defaultFilters())
const pagination = ref({
  page: search.page,
  rowsPerPage: search.pageSize,
  rowsNumber: search.total,
  sortBy: search.sort,
  descending: search.direction === 'desc',
})

const columns = [
  { name: 'setuptime', label: 'Start time', field: 'setuptime', align: 'left', sortable: true },
  {
    name: 'ingressani',
    label: 'Ingress ANI',
    field: 'ingressani',
    align: 'left',
    sortable: true,
    classes: 'cdr-mono',
  },
  {
    name: 'ingressdnis',
    label: 'Ingress DNIS',
    field: 'ingressdnis',
    align: 'left',
    sortable: true,
    classes: 'cdr-mono',
  },
  {
    name: 'egressani',
    label: 'Egress ANI',
    field: 'egressani',
    align: 'left',
    sortable: true,
    classes: 'cdr-mono',
  },
  {
    name: 'egressdnis',
    label: 'Egress DNIS',
    field: 'egressdnis',
    align: 'left',
    sortable: true,
    classes: 'cdr-mono',
  },
  {
    name: 'ingressipgroup',
    label: 'Ingress IP group',
    field: 'ingressipgroup',
    align: 'left',
    sortable: true,
  },
  {
    name: 'egressipgroup',
    label: 'Egress IP group',
    field: 'egressipgroup',
    align: 'left',
    sortable: true,
  },
  { name: 'callduration', label: 'Duration', field: 'callduration', align: 'right' },
  { name: 'issuccess', label: 'Status', field: 'issuccess', align: 'left', sortable: true },
  { name: 'termination', label: 'Termination', field: 'id', align: 'left' },
  { name: 'actions', label: 'Action', field: 'id', align: 'right' },
]

const MATCH_LABELS = Object.fromEntries(
  MATCH_MODE_OPTIONS.map((option) => [option.value, option.label]),
)
const STATUS_LABELS = Object.fromEntries(
  STATUS_OPTIONS.map((option) => [option.value, option.label]),
)
const APPLIED_LABELS = {
  ingress_ip_group: 'Ingress IP group',
  egress_ip_group: 'Egress IP group',
  termination_reason: 'Termination reason',
  ani: 'ANI',
  dnis: 'DNIS',
  call_id: 'Call-ID',
  termination_text: 'Termination text',
}

watch(
  () => [search.page, search.pageSize, search.total, search.sort, search.direction, search.error],
  () => {
    // After a failure the table collapses to one empty page so QTable never re-requests by itself.
    pagination.value = {
      page: search.error ? 1 : search.page,
      rowsPerPage: search.pageSize,
      rowsNumber: search.error ? 0 : search.total,
      sortBy: search.sort,
      descending: search.direction === 'desc',
    }
  },
)

watch(
  () => route.query,
  (query) => {
    if (route.path === SEARCH_PATH) {
      applyRoute(query)
    }
  },
)

onMounted(async () => {
  lookups.loadAll()
  await display.load()
  applyRoute(route.query)
})

function currentState(overrides = {}) {
  return {
    filters: search.filters ? cloneFilters(search.filters) : cloneFilters(draft.value),
    sort: search.sort,
    direction: search.direction,
    page: search.page,
    pageSize: search.pageSize,
    ...overrides,
  }
}

function defaultState() {
  return {
    filters: defaultFilters(),
    sort: DEFAULT_SORT,
    direction: DEFAULT_DIRECTION,
    page: 1,
    pageSize: display.defaultPageSize,
  }
}

function applyRoute(query) {
  if (!hasQuery(query)) {
    router.replace({
      path: SEARCH_PATH,
      query: search.lastQuery || searchStateToQuery(defaultState()),
    })
    return
  }
  const state = searchStateFromQuery(query, { pageSizeOptions: display.pageSizeOptions })
  const normalised = searchStateToQuery(state)
  if (!sameQuery(normalised, query)) {
    router.replace({ path: SEARCH_PATH, query: normalised })
    return
  }
  draft.value = cloneFilters(state.filters)
  search.run(state)
}

function navigate(state, { force = false } = {}) {
  const query = searchStateToQuery(state)
  if (sameQuery(query, route.query)) {
    search.run(state, { force })
    return
  }
  router.replace({ path: SEARCH_PATH, query })
}

function submitSearch() {
  navigate(currentState({ filters: cloneFilters(draft.value), page: 1 }), { force: true })
}

function clearFilters() {
  draft.value = { ...draft.value, ...emptyCriteria() }
}

function resetToToday() {
  draft.value = defaultFilters()
  navigate({ ...defaultState(), filters: cloneFilters(draft.value) }, { force: true })
}

function retry() {
  search.run(currentState(), { force: true })
}

function onRequest({ pagination: next }) {
  const sort = next.sortBy || DEFAULT_SORT
  const direction = next.sortBy ? (next.descending ? 'desc' : 'asc') : DEFAULT_DIRECTION
  const resetPage =
    sort !== search.sort || direction !== search.direction || next.rowsPerPage !== search.pageSize
  navigate(
    currentState({ sort, direction, page: resetPage ? 1 : next.page, pageSize: next.rowsPerPage }),
  )
}

function rowClass(row) {
  if (row.issuccess === false) {
    return 'cdr-row--failed'
  }
  return row.issuccess === null || row.issuccess === undefined ? 'cdr-row--unknown' : ''
}

function terminationFields(entry) {
  return entry.fields.map((field) => TERMINATION_FIELD_SHORT_LABELS[field] || field).join(', ')
}

const resultSummary = computed(() => {
  if (search.loading) {
    return 'Searching…'
  }
  if (search.error || !search.resultKey) {
    return ''
  }
  const count = `${formatCount(search.total)} matching SDR${search.total === 1 ? '' : 's'}`
  if (!search.applied) {
    return count
  }
  return `${count} with setup time from ${formatSydneyTimestamp(search.applied.start)} to ${formatSydneyTimestamp(search.applied.end)}`
})

const appliedChips = computed(() => {
  const applied = search.applied
  if (!applied) {
    return []
  }
  const chips = []
  if (applied.status && applied.status !== 'all') {
    chips.push(`Status: ${STATUS_LABELS[applied.status] || applied.status}`)
  }
  Object.entries(APPLIED_LABELS).forEach(([key, label]) => {
    const value = applied[key]
    if (Array.isArray(value)) {
      chips.push(`${label}: ${value.join(', ')}`)
    } else if (value?.value) {
      chips.push(
        `${label} ${(MATCH_LABELS[value.match] || value.match).toLowerCase()} "${value.value}"`,
      )
    }
  })
  return chips
})

const emptyMessage = computed(() => {
  if (search.loading) {
    return 'Searching…'
  }
  if (search.error) {
    return 'No results are available because the search failed.'
  }
  return 'No SDRs match these filters. Records without a setup time never match a setup-time search.'
})
</script>
