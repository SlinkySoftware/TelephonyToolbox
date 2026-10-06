<!--
SPDX-FileCopyrightText: Copyright 2026, Slinky Software
SPDX-License-Identifier: GPL-3.0-only
-->

<template>
  <span v-if="!blank" class="cdr-media cdr-mono" :class="statusMeta?.className">
    <span>{{ valueText }}</span>
    <span v-if="statusMeta" class="cdr-media__status">
      <q-icon :name="statusMeta.icon" size="1em" aria-hidden="true" />
      <span>{{ statusMeta.label }}</span>
    </span>
    <q-tooltip v-if="statusMeta">{{ thresholdText }}</q-tooltip>
    <q-tooltip v-else>No thresholds configured; the raw value is shown without units.</q-tooltip>
  </span>
</template>

<script setup>
import { computed } from 'vue'

import { MEDIA_STATUSES, displayValue, isBlank, mediaStatus } from 'src/utils/cdrFormat'

const props = defineProps({
  value: { type: [Number, String], default: null },
  config: { type: Object, default: null },
})

const blank = computed(() => isBlank(props.value))
const status = computed(() => mediaStatus(props.value, props.config))
const statusMeta = computed(() => MEDIA_STATUSES[status.value] || null)
const valueText = computed(() => {
  const text = displayValue(props.value)
  return props.config?.configured && props.config.unit ? `${text} ${props.config.unit}` : text
})
const thresholdText = computed(() => {
  const { warning, critical, unit } = props.config || {}
  const parts = []
  if (warning !== null && warning !== undefined) {
    parts.push(`warning at ${warning} ${unit}`)
  }
  if (critical !== null && critical !== undefined) {
    parts.push(`critical at ${critical} ${unit}`)
  }
  return `Thresholds: ${parts.join(', ')}.`
})
</script>
