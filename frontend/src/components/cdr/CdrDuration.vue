<!--
SPDX-FileCopyrightText: Copyright 2026, Slinky Software
SPDX-License-Identifier: GPL-3.0-only
-->

<template>
  <span v-if="!blank" class="cdr-duration cdr-mono">
    <span :class="{ 'cdr-duration--unformatted': formatted.unformatted }">{{
      formatted.text
    }}</span>
    <span v-if="formatted.unformatted" class="cdr-unformatted">
      <q-icon name="report" size="1em" aria-hidden="true" />
      <span>unformatted</span>
    </span>
    <span v-else-if="showRaw" class="cdr-raw">raw {{ rawText }}</span>
    <q-tooltip>
      <template v-if="formatted.unformatted">
        Value "{{ rawText }}" is not a number of hundredths of a second and is shown as recorded.
      </template>
      <template v-else> Raw value {{ rawText }} hundredths of a second ({{ alternate }}) </template>
    </q-tooltip>
  </span>
</template>

<script setup>
import { computed } from 'vue'

import { useCdrDisplayStore } from 'src/stores/cdrDisplay'
import { formatDuration, isBlank } from 'src/utils/cdrFormat'

const props = defineProps({
  value: { type: [String, Number], default: null },
  format: { type: String, default: '' },
  showRaw: { type: Boolean, default: false },
})

const display = useCdrDisplayStore()

const activeFormat = computed(() => props.format || display.durationFormat)
const blank = computed(() => isBlank(props.value))
const rawText = computed(() => String(props.value))
const formatted = computed(() => formatDuration(props.value, activeFormat.value))
const alternate = computed(
  () => formatDuration(props.value, activeFormat.value === 'hms' ? 'seconds' : 'hms').text,
)
</script>
