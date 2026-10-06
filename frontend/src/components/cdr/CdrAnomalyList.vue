<!--
SPDX-FileCopyrightText: Copyright 2026, Slinky Software
SPDX-License-Identifier: GPL-3.0-only
-->

<template>
  <div class="cdr-anomalies">
    <div v-if="incomplete" class="cdr-anomaly cdr-anomaly--warning">
      <q-icon name="pending" size="1.2em" aria-hidden="true" />
      <div>
        <div class="text-weight-medium">Correlation checks incomplete</div>
        <div class="muted-copy">CDR checks could not run because the CDR lookup failed.</div>
      </div>
    </div>

    <div v-if="!anomalies.length && !incomplete" class="cdr-anomaly cdr-anomaly--none">
      <q-icon name="verified" size="1.2em" aria-hidden="true" />
      <div>
        <div class="text-weight-medium">No anomaly</div>
        <div class="muted-copy">The associated CDRs correlate cleanly with this SDR.</div>
      </div>
    </div>

    <ul v-if="anomalies.length" class="cdr-anomaly-list">
      <li
        v-for="anomaly in sorted"
        :key="anomaly.code"
        class="cdr-anomaly"
        :class="`cdr-anomaly--${anomaly.severity}`"
      >
        <q-icon
          :name="SEVERITY[anomaly.severity]?.icon || 'info'"
          size="1.2em"
          aria-hidden="true"
        />
        <div>
          <div class="text-weight-medium">
            {{ SEVERITY[anomaly.severity]?.label || anomaly.severity }}: {{ anomaly.message }}
          </div>
          <div v-if="anomaly.cdr_ids?.length" class="muted-copy cdr-mono">
            CDR {{ anomaly.cdr_ids.length === 1 ? 'ID' : 'IDs' }}: {{ anomaly.cdr_ids.join(', ') }}
          </div>
          <div class="cdr-anomaly__code">{{ anomaly.code }}</div>
        </div>
      </li>
    </ul>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  anomalies: { type: Array, default: () => [] },
  incomplete: { type: Boolean, default: false },
})

const SEVERITY = {
  warning: { label: 'Warning', icon: 'warning' },
  info: { label: 'Information', icon: 'info' },
}

const sorted = computed(() =>
  [...props.anomalies].sort(
    (a, b) => (a.severity === 'warning' ? 0 : 1) - (b.severity === 'warning' ? 0 : 1),
  ),
)
</script>
