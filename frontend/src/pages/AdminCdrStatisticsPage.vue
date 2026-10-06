<!--
SPDX-FileCopyrightText: Copyright 2026, Slinky Software
SPDX-License-Identifier: GPL-3.0-only
-->

<template>
  <q-page class="page-frame soft-grid">
    <section class="page-hero">
      <div class="section-kicker">App Admin · AudioCodes CDR</div>
      <h1 class="page-title">Call Statistics</h1>
      <p class="page-subtitle">
        One SDR is one call. Calls are bucketed by setup time in Australia/Sydney; records without a
        setup time are excluded.
      </p>
    </section>

    <CdrModuleTabs />
    <CdrSourceBanner :error="stats.sourceError" retry @retry="reload" />

    <section class="form-panel q-pa-lg soft-grid" aria-label="Statistics filters">
      <div class="cdr-preset-row">
        <span id="cdr-preset-label" class="text-subtitle2">Range</span>
        <q-btn-toggle
          :model-value="preset"
          :options="STATISTICS_PRESETS"
          no-caps
          unelevated
          dense
          toggle-color="primary"
          color="white"
          text-color="primary"
          class="cdr-preset-toggle"
          aria-labelledby="cdr-preset-label"
          @update:model-value="changePreset"
        />
      </div>
      <CdrFilterPanel
        v-model="draft"
        :show-range="preset === 'custom'"
        submit-label="Apply"
        submit-icon="insights"
        :server-errors="fieldErrors"
        @submit="apply"
        @clear="clearFilters"
      />
    </section>

    <q-banner
      v-for="message in otherErrorMessages"
      :key="message"
      rounded
      class="cdr-banner cdr-banner--danger"
      role="alert"
    >
      <template #avatar><q-icon name="error_outline" /></template>
      {{ message }}
    </q-banner>

    <section class="status-panel q-pa-md cdr-stats-meta" aria-live="polite">
      <div v-if="stats.loading" class="cdr-loading">
        <q-spinner color="primary" size="1.2rem" />
        <span>Loading statistics…</span>
      </div>
      <template v-else-if="range">
        <div>
          <span class="text-weight-medium">Range:</span>
          {{ formatSydneyTimestamp(range.start) }} to {{ formatSydneyTimestamp(range.end) }}
        </div>
        <q-chip v-if="bucket" dense square icon="view_week" class="cdr-bucket-chip">
          {{ bucket === 'hour' ? 'Hourly intervals' : 'Daily intervals' }}
          <q-tooltip>
            Hourly for ranges up to {{ hourlyMaxHours }} hours; daily for longer ranges.
          </q-tooltip>
        </q-chip>
        <span v-if="generatedAt" class="muted-copy text-caption">
          {{ cached ? 'Cached result generated' : 'Generated' }}
          {{ formatSydneyTimestamp(generatedAt) }}
        </span>
      </template>
    </section>

    <q-banner v-if="summary && summary.total === 0 && !stats.loading" rounded class="cdr-banner">
      <template #avatar><q-icon name="info" color="primary" /></template>
      No calls with a setup time were found for this range and these filters.
    </q-banner>

    <div v-if="summary" class="metric-grid">
      <div class="card-panel metric-card">
        <div class="muted-copy">Total calls</div>
        <div class="metric-value">{{ formatCount(summary.total) }}</div>
      </div>
      <div class="card-panel metric-card">
        <div class="muted-copy">Success rate</div>
        <div class="metric-value">{{ formatPercent(summary.success_rate) || 'n/a' }}</div>
        <div class="muted-copy text-caption">Unknown outcomes are excluded from the rate.</div>
      </div>
      <div class="card-panel metric-card">
        <div class="muted-copy">Outcomes</div>
        <div class="cdr-outcome-list">
          <span><CdrStatusBadge outcome="successful" /> {{ formatCount(summary.successful) }}</span>
          <span
            ><CdrStatusBadge outcome="unsuccessful" /> {{ formatCount(summary.unsuccessful) }}</span
          >
          <span><CdrStatusBadge outcome="unknown" /> {{ formatCount(summary.unknown) }}</span>
        </div>
      </div>
      <div class="card-panel metric-card">
        <div class="muted-copy">Average call duration</div>
        <div class="metric-value cdr-mono">
          {{ durationText(summary.avg_call_duration) || 'n/a' }}
        </div>
        <div class="muted-copy text-caption">
          {{ formatCount(summary.call_duration_samples) }} averaged ·
          {{ formatCount(summary.call_duration_excluded) }} excluded (blank or invalid)
        </div>
      </div>
      <div class="card-panel metric-card">
        <div class="muted-copy">Average time to connect</div>
        <div class="metric-value cdr-mono">
          {{ durationText(summary.avg_time_to_connect) || 'n/a' }}
        </div>
        <div class="muted-copy text-caption">
          {{ formatCount(summary.time_to_connect_samples) }} averaged ·
          {{ formatCount(summary.time_to_connect_excluded) }} excluded (blank)
        </div>
      </div>
    </div>

    <template v-if="points.length">
      <section class="card-panel q-pa-lg" aria-labelledby="cdr-chart-calls">
        <h2 id="cdr-chart-calls" class="cdr-section-title">Calls per interval</h2>
        <div class="muted-copy text-caption q-mb-sm">
          Select an interval to open the matching SDR search.
        </div>
        <EChart :option="callsOption" height="340px" @grid-click="onIntervalClick" />
      </section>

      <div class="cdr-chart-pair">
        <section class="card-panel q-pa-lg" aria-labelledby="cdr-chart-rate">
          <h2 id="cdr-chart-rate" class="cdr-section-title">Success rate</h2>
          <EChart :option="successRateOption" height="260px" @grid-click="onIntervalClick" />
        </section>
        <section class="card-panel q-pa-lg" aria-labelledby="cdr-chart-durations">
          <h2 id="cdr-chart-durations" class="cdr-section-title">Average durations</h2>
          <EChart :option="durationOption" height="260px" @grid-click="onIntervalClick" />
        </section>
      </div>

      <section class="table-panel q-pa-md">
        <q-expansion-item
          icon="table_rows"
          label="Interval data table"
          caption="Accessible view of every interval, including zero-call intervals"
          header-class="text-primary"
        >
          <q-table
            :rows="points"
            :columns="intervalColumns"
            row-key="start"
            flat
            dense
            :rows-per-page-options="[24, 48, 100, 0]"
            :pagination="{ rowsPerPage: 24 }"
          >
            <template #body-cell-interval="props">
              <q-td :props="props" class="cdr-mono cdr-nowrap">
                {{ formatSydneyTimestamp(props.row.start) }} –
                {{ formatSydneyTimestamp(props.row.end) }}
              </q-td>
            </template>
            <template #body-cell-actions="props">
              <q-td :props="props">
                <q-btn
                  flat
                  dense
                  no-caps
                  color="primary"
                  icon="manage_search"
                  label="View calls"
                  @click="drillDown({ start: props.row.start, end: props.row.end })"
                />
              </q-td>
            </template>
          </q-table>
        </q-expansion-item>
      </section>
    </template>

    <div v-if="ipGroups" class="cdr-chart-pair">
      <section
        v-for="side in IP_GROUP_SIDES"
        :key="side.key"
        class="card-panel q-pa-lg"
        :aria-labelledby="`cdr-chart-${side.key}`"
      >
        <h2 :id="`cdr-chart-${side.key}`" class="cdr-section-title">{{ side.label }}</h2>
        <div class="muted-copy text-caption q-mb-sm">
          Top {{ ipGroups.limit }} by calls. Select a group to search its calls in this range.
        </div>
        <EChart
          v-if="ipGroups[side.key]?.length"
          :option="ipGroupOptions[side.key]"
          :height="chartHeight(ipGroups[side.key].length)"
          @item-click="(params) => onIpGroupClick(side, ipGroups[side.key], params)"
        />
        <div v-else class="cdr-empty">No calls in this range.</div>
      </section>
    </div>

    <section v-if="terminationReasons" class="card-panel q-pa-lg" aria-labelledby="cdr-chart-term">
      <div class="cdr-legs-header">
        <h2 id="cdr-chart-term" class="cdr-section-title">
          <span>Top termination reasons</span>
          <CdrHelp
            :text="display.help.topics?.termination_reason"
            label="Termination reasons"
            :source="display.help.version"
          />
        </h2>
        <q-btn-toggle
          v-model="terminationField"
          :options="TERMINATION_OPTIONS"
          no-caps
          unelevated
          dense
          toggle-color="primary"
          color="white"
          text-color="primary"
          aria-label="Termination field"
        />
      </div>
      <div class="muted-copy text-caption q-mb-sm">
        Top {{ terminationReasons.limit }} values reported in
        <span class="cdr-mono">{{ terminationField }}</span
        >, shown exactly as recorded.
      </div>
      <EChart
        v-if="terminationRows.length"
        :option="terminationOption"
        :height="chartHeight(terminationRows.length)"
      />
      <div v-else class="cdr-empty">No termination reasons recorded for this field.</div>
    </section>
  </q-page>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'

import CdrFilterPanel from 'src/components/cdr/CdrFilterPanel.vue'
import CdrHelp from 'src/components/cdr/CdrHelp.vue'
import CdrModuleTabs from 'src/components/cdr/CdrModuleTabs.vue'
import CdrSourceBanner from 'src/components/cdr/CdrSourceBanner.vue'
import CdrStatusBadge from 'src/components/cdr/CdrStatusBadge.vue'
import EChart from 'src/components/cdr/EChart.vue'
import { useCdrDisplayStore } from 'src/stores/cdrDisplay'
import { useCdrLookupsStore } from 'src/stores/cdrLookups'
import { useCdrStatisticsStore } from 'src/stores/cdrStatistics'
import { SDR_TERMINATION_FIELDS, TERMINATION_FIELD_SHORT_LABELS } from 'src/utils/cdrFields'
import {
  escapeHtml,
  formatBucketLabel,
  formatCount,
  formatDurationText,
  formatPercent,
  formatSydneyTimestamp,
} from 'src/utils/cdrFormat'
import {
  DEFAULT_DIRECTION,
  DEFAULT_SORT,
  STATISTICS_PRESETS,
  cloneFilters,
  emptyCriteria,
  searchStateToQuery,
} from 'src/utils/cdrQuery'
import { toSydneyIso } from 'src/utils/cdrTime'

const COLORS = {
  successful: '#2f855a',
  unsuccessful: '#c53030',
  unknown: '#718096',
  total: '#0066cc',
  secondary: '#dd6b20',
}
const IP_GROUP_SIDES = [
  { key: 'ingress', label: 'Calls by ingress IP group', filter: 'ingress_ip_group' },
  { key: 'egress', label: 'Calls by egress IP group', filter: 'egress_ip_group' },
]
const TERMINATION_OPTIONS = SDR_TERMINATION_FIELDS.map((field) => ({
  value: field,
  label: TERMINATION_FIELD_SHORT_LABELS[field],
}))
const NO_GROUP_LABEL = '(no IP group)'

const router = useRouter()
const display = useCdrDisplayStore()
const lookups = useCdrLookupsStore()
const stats = useCdrStatisticsStore()

const preset = ref(stats.applied.preset)
const draft = ref({
  start: stats.applied.start,
  end: stats.applied.end,
  ...cloneFilters(stats.applied.criteria),
})
const terminationField = ref(SDR_TERMINATION_FIELDS[0])

const summary = computed(() => stats.data.summary?.summary || null)
const timeseries = computed(() => stats.data.timeseries)
const ipGroups = computed(() => stats.data.ipGroups)
const terminationReasons = computed(() => stats.data.terminationReasons)
const points = computed(() => timeseries.value?.points || [])
const bucket = computed(() => timeseries.value?.bucket || null)
const range = computed(() => stats.resolvedRange)
const hourlyMaxHours = computed(
  () => timeseries.value?.hourly_bucket_max_hours || display.hourlyBucketMaxHours,
)
const generatedAt = computed(() => stats.data.summary?.generated_at || null)
const cached = computed(() => Boolean(stats.data.summary?.cached))
const fieldErrors = computed(
  () => Object.values(stats.errors).find((error) => error?.fieldErrors)?.fieldErrors || null,
)
const otherErrorMessages = computed(() => [
  ...new Set(stats.otherErrors.map((error) => error.message)),
])
const terminationRows = computed(
  () => terminationReasons.value?.fields?.[terminationField.value] || [],
)

const intervalColumns = [
  { name: 'interval', label: 'Interval (Australia/Sydney)', field: 'start', align: 'left' },
  { name: 'total', label: 'Total', field: 'total', align: 'right', format: formatCount },
  {
    name: 'successful',
    label: 'Successful',
    field: 'successful',
    align: 'right',
    format: formatCount,
  },
  {
    name: 'unsuccessful',
    label: 'Unsuccessful',
    field: 'unsuccessful',
    align: 'right',
    format: formatCount,
  },
  { name: 'unknown', label: 'Unknown', field: 'unknown', align: 'right', format: formatCount },
  {
    name: 'success_rate',
    label: 'Success rate',
    field: 'success_rate',
    align: 'right',
    format: formatPercent,
  },
  {
    name: 'avg_call_duration',
    label: 'Avg duration',
    field: 'avg_call_duration',
    align: 'right',
    format: (value) => durationText(value),
  },
  {
    name: 'avg_time_to_connect',
    label: 'Avg time to connect',
    field: 'avg_time_to_connect',
    align: 'right',
    format: (value) => durationText(value),
  },
  { name: 'actions', label: 'Drill down', field: 'start', align: 'right' },
]

onMounted(async () => {
  lookups.loadAll()
  await display.load()
  stats.load(currentSelection())
})

function currentSelection() {
  const { start, end, ...criteria } = draft.value
  return { preset: preset.value, start, end, criteria }
}

function apply() {
  stats.load(currentSelection(), { force: true })
}

function reload() {
  stats.load(stats.applied, { force: true })
}

function changePreset(value) {
  preset.value = value
  if (value === 'custom') {
    // Start from the range currently on screen, or the last 7 days.
    const now = new Date()
    draft.value = {
      ...draft.value,
      start: range.value?.start || toSydneyIso(new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000)),
      end: range.value?.end || toSydneyIso(now),
    }
    return
  }
  apply()
}

function clearFilters() {
  draft.value = { ...draft.value, ...emptyCriteria() }
}

function durationText(value) {
  return value === null || value === undefined
    ? ''
    : formatDurationText(value, display.durationFormat)
}

function secondsAxisLabel(value, format) {
  return formatDurationText(Math.round(value * 100), format)
}

function intervalHeading(point) {
  return escapeHtml(`${formatSydneyTimestamp(point.start)} – ${formatSydneyTimestamp(point.end)}`)
}

function drillDown({ start, end, extra = {} }) {
  const filters = { start, end, ...cloneFilters(stats.applied.criteria), ...extra }
  router.push({
    path: '/admin/cdr',
    query: searchStateToQuery({
      filters,
      sort: DEFAULT_SORT,
      direction: DEFAULT_DIRECTION,
      page: 1,
      pageSize: display.defaultPageSize,
    }),
  })
}

function onIntervalClick({ x }) {
  const point = points.value[Math.round(x)]
  if (point) {
    drillDown({ start: point.start, end: point.end })
  }
}

function onIpGroupClick(side, rows, params) {
  const row = rows[params.dataIndex]
  if (!row || row.ip_group === null || !range.value) {
    return
  }
  drillDown({
    start: range.value.start,
    end: range.value.end,
    extra: { [side.filter]: [row.ip_group] },
  })
}

function chartHeight(count) {
  return `${Math.max(200, count * 26 + 80)}px`
}

const categories = computed(() =>
  points.value.map((point) => formatBucketLabel(point.start, bucket.value)),
)

function axisTooltip(lines) {
  return {
    trigger: 'axis',
    axisPointer: { type: 'shadow' },
    formatter: (params) => {
      const point = points.value[params[0]?.dataIndex]
      return point ? [intervalHeading(point), ...lines(point)].join('<br/>') : ''
    },
  }
}

const baseGrid = { left: 16, right: 24, top: 48, bottom: 16 }

const callsOption = computed(() => ({
  color: [COLORS.successful, COLORS.unsuccessful, COLORS.unknown, COLORS.total],
  tooltip: axisTooltip((point) => [
    `Total: ${formatCount(point.total)}`,
    `Successful: ${formatCount(point.successful)}`,
    `Unsuccessful: ${formatCount(point.unsuccessful)}`,
    `Unknown: ${formatCount(point.unknown)}`,
    'Click to view these calls',
  ]),
  legend: { top: 0 },
  grid: baseGrid,
  xAxis: { type: 'category', data: categories.value, axisLabel: { hideOverlap: true } },
  yAxis: { type: 'value', name: 'Calls', minInterval: 1 },
  series: [
    ...['successful', 'unsuccessful', 'unknown'].map((key) => ({
      name: key.charAt(0).toUpperCase() + key.slice(1),
      type: 'bar',
      stack: 'calls',
      data: points.value.map((point) => point[key]),
    })),
    {
      name: 'Total',
      type: 'line',
      symbolSize: 5,
      lineStyle: { type: 'dashed' },
      data: points.value.map((point) => point.total),
    },
  ],
}))

const successRateOption = computed(() => ({
  color: [COLORS.total],
  tooltip: axisTooltip((point) => [
    `Success rate: ${formatPercent(point.success_rate) || 'n/a'}`,
    `Calls with a known outcome: ${formatCount(point.successful + point.unsuccessful)}`,
  ]),
  grid: baseGrid,
  xAxis: { type: 'category', data: categories.value, axisLabel: { hideOverlap: true } },
  yAxis: {
    type: 'value',
    name: 'Success rate',
    min: 0,
    max: 100,
    axisLabel: { formatter: '{value}%' },
  },
  series: [
    {
      name: 'Success rate',
      type: 'line',
      symbolSize: 5,
      connectNulls: false,
      data: points.value.map((point) => point.success_rate),
    },
  ],
}))

const durationOption = computed(() => {
  const format = display.durationFormat
  return {
    color: [COLORS.total, COLORS.secondary],
    tooltip: axisTooltip((point) => [
      `Average call duration: ${durationText(point.avg_call_duration) || 'n/a'} (${formatCount(point.call_duration_samples)} averaged, ${formatCount(point.call_duration_excluded)} excluded)`,
      `Average time to connect: ${durationText(point.avg_time_to_connect) || 'n/a'} (${formatCount(point.time_to_connect_samples)} averaged)`,
    ]),
    legend: { top: 0 },
    grid: baseGrid,
    xAxis: { type: 'category', data: categories.value, axisLabel: { hideOverlap: true } },
    yAxis: { type: 'value', axisLabel: { formatter: (value) => secondsAxisLabel(value, format) } },
    series: [
      {
        name: 'Average call duration',
        type: 'line',
        symbolSize: 5,
        data: points.value.map((point) =>
          point.avg_call_duration === null ? null : point.avg_call_duration / 100,
        ),
      },
      {
        name: 'Average time to connect',
        type: 'line',
        symbolSize: 5,
        data: points.value.map((point) =>
          point.avg_time_to_connect === null ? null : point.avg_time_to_connect / 100,
        ),
      },
    ],
  }
})

function ipGroupOption(rows) {
  const labels = rows.map((row) => row.ip_group ?? NO_GROUP_LABEL)
  return {
    color: [COLORS.successful, COLORS.unsuccessful, COLORS.unknown],
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'shadow' },
      formatter: (params) => {
        const row = rows[params[0]?.dataIndex]
        if (!row) {
          return ''
        }
        return [
          escapeHtml(row.ip_group ?? NO_GROUP_LABEL),
          `Total: ${formatCount(row.total)}`,
          `Successful: ${formatCount(row.successful)}`,
          `Unsuccessful: ${formatCount(row.unsuccessful)}`,
          `Unknown: ${formatCount(row.unknown)}`,
        ].join('<br/>')
      },
    },
    legend: { top: 0 },
    grid: { left: 16, right: 24, top: 36, bottom: 8 },
    xAxis: { type: 'value', minInterval: 1 },
    yAxis: {
      type: 'category',
      inverse: true,
      data: labels,
      axisLabel: { width: 180, overflow: 'truncate' },
    },
    series: ['successful', 'unsuccessful', 'unknown'].map((key) => ({
      name: key.charAt(0).toUpperCase() + key.slice(1),
      type: 'bar',
      stack: 'calls',
      cursor: 'pointer',
      data: rows.map((row) => row[key]),
    })),
  }
}

const ipGroupOptions = computed(() => ({
  ingress: ipGroupOption(ipGroups.value?.ingress || []),
  egress: ipGroupOption(ipGroups.value?.egress || []),
}))

const terminationOption = computed(() => {
  const rows = terminationRows.value
  return {
    color: [COLORS.total],
    tooltip: {
      trigger: 'item',
      formatter: (params) => {
        const row = rows[params.dataIndex]
        return row ? `${escapeHtml(row.value)}<br/>Calls: ${formatCount(row.total)}` : ''
      },
    },
    grid: { left: 16, right: 24, top: 8, bottom: 8 },
    xAxis: { type: 'value', minInterval: 1 },
    yAxis: {
      type: 'category',
      inverse: true,
      data: rows.map((row) => row.value),
      axisLabel: { width: 220, overflow: 'truncate' },
    },
    series: [{ name: 'Calls', type: 'bar', data: rows.map((row) => row.total) }],
  }
})
</script>
