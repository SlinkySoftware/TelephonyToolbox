<!--
SPDX-FileCopyrightText: Copyright 2026, Slinky Software
SPDX-License-Identifier: GPL-3.0-only
-->

<template>
  <q-page class="page-frame soft-grid">
    <section class="page-hero">
      <div class="section-kicker">App Admin · AudioCodes CDR</div>
      <h1 class="page-title">
        SDR <span class="cdr-mono">{{ id }}</span>
      </h1>
      <div class="cdr-session-actions">
        <q-btn
          outline
          no-caps
          color="primary"
          icon="arrow_back"
          label="Back to search"
          :to="backLink"
        />
        <q-btn
          flat
          no-caps
          color="primary"
          icon="refresh"
          label="Reload"
          :disable="loading"
          @click="load"
        />
        <template v-if="detail">
          <CdrStatusBadge :outcome="detail.sdr.display.outcome" />
          <span class="cdr-anomaly-level" :class="`cdr-anomaly-level--${detail.anomaly_level}`">
            <q-icon
              :name="ANOMALY_LEVELS[detail.anomaly_level]?.icon"
              size="1em"
              aria-hidden="true"
            />
            <span>{{ ANOMALY_LEVELS[detail.anomaly_level]?.label }}</span>
          </span>
        </template>
      </div>
    </section>

    <CdrModuleTabs />
    <CdrSourceBanner :error="error" retry @retry="load" />

    <div v-if="loading" class="status-panel q-pa-lg cdr-loading" role="status">
      <q-spinner color="primary" size="1.6rem" />
      <span>Loading session details…</span>
    </div>

    <q-banner v-else-if="invalidId" rounded class="cdr-banner cdr-banner--danger" role="alert">
      <template #avatar><q-icon name="error_outline" /></template>
      "{{ id }}" is not a valid SDR ID.
    </q-banner>

    <q-banner
      v-else-if="error && !error.sourceIssue && !error.timeout"
      rounded
      class="cdr-banner cdr-banner--danger"
      role="alert"
    >
      <template #avatar
        ><q-icon :name="error.notFound ? 'search_off' : 'error_outline'"
      /></template>
      {{ error.notFound ? `SDR ${id} was not found in the AudioCodes source.` : error.message }}
    </q-banner>

    <template v-if="detail && !loading">
      <div class="cdr-detail-grid">
        <section class="card-panel q-pa-lg" aria-labelledby="cdr-overview-title">
          <h2 id="cdr-overview-title" class="cdr-section-title">Call overview</h2>
          <CdrFieldGrid :items="overviewItems" :help-source="helpVersion" />
        </section>

        <section class="card-panel q-pa-lg cdr-detail-grid__wide" aria-labelledby="cdr-path-title">
          <h2 id="cdr-path-title" class="cdr-section-title">Call path</h2>
          <CdrCallPath :raw="sdr" :changes="detail.sdr.display.number_changes" />
        </section>

        <section class="card-panel q-pa-lg" aria-labelledby="cdr-timing-title">
          <h2 id="cdr-timing-title" class="cdr-section-title">
            <span>Timing</span>
            <CdrHelp :text="topics.timing" label="Timing" :source="helpVersion" />
          </h2>
          <CdrFieldGrid :items="sectionItems('timing')" :help-source="helpVersion" />
        </section>

        <section class="card-panel q-pa-lg" aria-labelledby="cdr-termination-title">
          <h2 id="cdr-termination-title" class="cdr-section-title">
            <span>Termination</span>
            <CdrHelp :text="terminationHelp" label="Termination" :source="helpVersion" />
          </h2>
          <CdrFieldGrid :items="sectionItems('termination')" :help-source="helpVersion" />
        </section>

        <section class="card-panel q-pa-lg" aria-labelledby="cdr-media-title">
          <h2 id="cdr-media-title" class="cdr-section-title">
            <span>Media and RTP</span>
            <CdrHelp :text="topics.media_quality" label="Media and RTP" :source="helpVersion" />
          </h2>
          <CdrFieldGrid :items="sectionItems('media')" :help-source="helpVersion" />
          <div class="muted-copy text-caption q-mt-sm">
            Media-quality measurements are shown on each CDR leg below.
          </div>
        </section>

        <section class="card-panel q-pa-lg" aria-labelledby="cdr-identifiers-title">
          <h2 id="cdr-identifiers-title" class="cdr-section-title">Identifiers</h2>
          <CdrFieldGrid :items="sectionItems('identifiers')" :help-source="helpVersion" />
        </section>

        <section
          v-if="additionalItems.length"
          class="card-panel q-pa-lg"
          aria-labelledby="cdr-additional-title"
        >
          <h2 id="cdr-additional-title" class="cdr-section-title">Additional SDR fields</h2>
          <CdrFieldGrid :items="additionalItems" :help-source="helpVersion" />
        </section>

        <section
          class="card-panel q-pa-lg cdr-detail-grid__wide"
          aria-labelledby="cdr-anomaly-title"
        >
          <h2 id="cdr-anomaly-title" class="cdr-section-title">
            <span>Correlation anomalies</span>
            <CdrHelp :text="topics.correlation" label="Correlation" :source="helpVersion" />
          </h2>
          <CdrAnomalyList :anomalies="detail.anomalies" :incomplete="detail.cdrs === null" />
        </section>
      </div>

      <section class="table-panel q-pa-lg" aria-labelledby="cdr-legs-title">
        <div class="cdr-legs-header">
          <h2 id="cdr-legs-title" class="cdr-section-title">
            <span>CDR legs</span>
            <span v-if="detail.cdrs" class="muted-copy text-body2">({{ detail.cdrs.length }})</span>
            <CdrHelp :text="topics.direction" label="CDR direction" :source="helpVersion" />
          </h2>
          <div v-if="detail.cdrs?.length" class="row q-gutter-sm">
            <q-btn
              flat
              dense
              no-caps
              color="primary"
              icon="unfold_more"
              label="Expand all"
              @click="setAllExpanded(true)"
            />
            <q-btn
              flat
              dense
              no-caps
              color="primary"
              icon="unfold_less"
              label="Collapse all"
              @click="setAllExpanded(false)"
            />
          </div>
        </div>

        <q-banner
          v-if="detail.cdrs === null"
          rounded
          class="cdr-banner cdr-banner--warning"
          role="alert"
        >
          <template #avatar><q-icon name="hourglass_disabled" /></template>
          <div class="text-weight-medium">CDR legs could not be loaded</div>
          <div>{{ detail.cdrs_error?.detail || 'The CDR lookup failed.' }}</div>
          <div class="muted-copy">The SDR details above are complete.</div>
          <template #action>
            <q-btn flat no-caps icon="refresh" label="Retry" @click="load" />
          </template>
        </q-banner>

        <div v-if="detail.cdrs && !detail.cdrs.length" class="cdr-empty">
          <q-icon name="link_off" size="1.6rem" />
          <div>{{ noCdrMessage }}</div>
        </div>

        <div v-if="detail.cdrs?.length" class="cdr-leg-list">
          <CdrLegCard
            v-for="cdr in detail.cdrs"
            :key="cdr.raw.id"
            v-model="expanded[cdr.raw.id]"
            :cdr="cdr"
            :anomalies="anomaliesFor(cdr.raw.id)"
          />
        </div>
      </section>

      <div v-if="helpVersion" class="muted-copy text-caption">
        Field help: {{ helpVersion }}. {{ display.help.source }}
      </div>
    </template>
  </q-page>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'

import CdrAnomalyList from 'src/components/cdr/CdrAnomalyList.vue'
import CdrCallPath from 'src/components/cdr/CdrCallPath.vue'
import CdrFieldGrid from 'src/components/cdr/CdrFieldGrid.vue'
import CdrHelp from 'src/components/cdr/CdrHelp.vue'
import CdrLegCard from 'src/components/cdr/CdrLegCard.vue'
import CdrModuleTabs from 'src/components/cdr/CdrModuleTabs.vue'
import CdrSourceBanner from 'src/components/cdr/CdrSourceBanner.vue'
import CdrStatusBadge from 'src/components/cdr/CdrStatusBadge.vue'
import { describeCdrError, getSdrDetail, isCancelled } from 'src/services/cdrApi'
import { useCdrDisplayStore } from 'src/stores/cdrDisplay'
import { useCdrSearchStore } from 'src/stores/cdrSearch'
import { SDR_SECTIONS, buildFieldItems } from 'src/utils/cdrFields'
import { isBlank } from 'src/utils/cdrFormat'

const props = defineProps({
  id: { type: String, required: true },
})

const ANOMALY_LEVELS = {
  none: { label: 'No anomaly', icon: 'verified' },
  info: { label: 'Informational anomaly', icon: 'info' },
  warning: { label: 'Warning anomaly', icon: 'warning' },
}
const MAX_SDR_ID = 9223372036854775807n

const display = useCdrDisplayStore()
const search = useCdrSearchStore()

const detail = ref(null)
const loading = ref(false)
const error = ref(null)
const invalidId = ref(false)
const expanded = ref({})
let controller = null

const backLink = computed(() => ({ path: '/admin/cdr', query: search.lastQuery || {} }))
const sdr = computed(() => detail.value?.sdr.raw || {})
const helpVersion = computed(() => display.help.version || '')
const topics = computed(() => display.help.topics || {})
const terminationHelp = computed(() =>
  [topics.value.termination_reason, topics.value.sip_termination_reason, topics.value.success]
    .filter(Boolean)
    .join(' '),
)

const fieldContext = computed(() => ({ help: display.help }))

function sectionItems(section) {
  return buildFieldItems('sdr', SDR_SECTIONS[section], sdr.value, fieldContext.value)
}

const overviewItems = computed(() => {
  const [success, ...rest] = buildFieldItems(
    'sdr',
    ['issuccess', ...SDR_SECTIONS.overview],
    sdr.value,
    fieldContext.value,
  )
  const sdrDisplay = detail.value?.sdr.display || {}
  const effective = {
    key: 'effective_start',
    label: 'Displayed start time',
    sourceName: sdrDisplay.effective_start_source || 'derived',
    value: sdrDisplay.effective_start ?? null,
    timestampSource: sdrDisplay.effective_start_source,
    type: 'timestamp',
    help: 'Setup time when present; otherwise connect time, marked as a fallback.',
  }
  return [success, effective, ...rest]
})

const additionalItems = computed(() => {
  const assigned = new Set(Object.values(SDR_SECTIONS).flat())
  const keys = Object.keys(sdr.value).filter((key) => !assigned.has(key))
  return buildFieldItems('sdr', keys, sdr.value, fieldContext.value)
})

const noCdrMessage = computed(() =>
  isBlank(sdr.value.sessionid)
    ? 'This SDR has a blank session ID, so no CDRs can be correlated.'
    : 'No CDRs share this SDR session ID.',
)

function anomaliesFor(cdrId) {
  return (detail.value?.anomalies || []).filter((anomaly) => anomaly.cdr_ids?.includes(cdrId))
}

function setAllExpanded(value) {
  const next = {}
  for (const cdr of detail.value?.cdrs || []) {
    next[cdr.raw.id] = value
  }
  expanded.value = next
}

function isValidId(value) {
  return /^\d{1,19}$/.test(value) && BigInt(value) >= 1n && BigInt(value) <= MAX_SDR_ID
}

async function load() {
  controller?.abort()
  error.value = null
  invalidId.value = !isValidId(props.id)
  if (invalidId.value) {
    detail.value = null
    return
  }
  const current = new AbortController()
  controller = current
  loading.value = true
  try {
    const data = await getSdrDetail(props.id, { signal: current.signal })
    detail.value = data
    expanded.value = {}
  } catch (requestError) {
    if (isCancelled(requestError) || controller !== current) {
      return
    }
    detail.value = null
    error.value = describeCdrError(requestError, 'Unable to load the session details.')
  } finally {
    if (controller === current) {
      loading.value = false
      controller = null
    }
  }
}

watch(() => props.id, load)

onMounted(() => {
  display.load()
  load()
})

onBeforeUnmount(() => {
  controller?.abort()
})
</script>
