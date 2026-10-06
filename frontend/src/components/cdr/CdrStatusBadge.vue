<!--
SPDX-FileCopyrightText: Copyright 2026, Slinky Software
SPDX-License-Identifier: GPL-3.0-only
-->

<template>
  <span class="cdr-status" :class="meta.className">
    <q-icon :name="meta.icon" size="1.05em" aria-hidden="true" />
    <span>{{ label || meta.label }}</span>
  </span>
</template>

<script setup>
import { computed } from 'vue'

import { OUTCOMES, outcomeFromBoolean } from 'src/utils/cdrFormat'

const props = defineProps({
  // Either an outcome key (successful | unsuccessful | unknown) or the raw boolean/null value.
  outcome: { type: String, default: null },
  value: { type: Boolean, default: null },
  label: { type: String, default: '' },
})

const meta = computed(() => {
  const key = props.outcome || outcomeFromBoolean(props.value)
  return OUTCOMES[key] || OUTCOMES.unknown
})
</script>
