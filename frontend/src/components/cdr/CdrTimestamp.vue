<!--
SPDX-FileCopyrightText: Copyright 2026, Slinky Software
SPDX-License-Identifier: GPL-3.0-only
-->

<template>
  <span class="cdr-timestamp cdr-mono">
    <span>{{ text }}</span>
    <span v-if="isFallback" class="cdr-fallback">
      <q-icon name="schedule" size="1em" aria-hidden="true" />
      <span>connect time</span>
      <q-tooltip>Connect time shown because setup time is unavailable.</q-tooltip>
    </span>
  </span>
</template>

<script setup>
import { computed } from 'vue'

import { formatSydneyTimestamp } from 'src/utils/cdrFormat'

const props = defineProps({
  value: { type: String, default: null },
  // Field that supplied the value; 'connecttime' marks a setup-time fallback.
  source: { type: String, default: null },
})

const text = computed(() => formatSydneyTimestamp(props.value))
const isFallback = computed(() => Boolean(props.value) && props.source === 'connecttime')
</script>
