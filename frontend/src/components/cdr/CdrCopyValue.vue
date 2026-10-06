<!--
SPDX-FileCopyrightText: Copyright 2026, Slinky Software
SPDX-License-Identifier: GPL-3.0-only
-->

<template>
  <span class="cdr-copy" :class="{ 'cdr-mono': mono }">
    <span class="cdr-copy__value">{{ text }}</span>
    <q-btn
      v-if="text"
      flat
      round
      dense
      size="xs"
      icon="content_copy"
      class="cdr-copy__btn"
      :aria-label="`Copy ${label}`"
      @click.stop="copy"
    >
      <q-tooltip>Copy {{ label }}</q-tooltip>
    </q-btn>
  </span>
</template>

<script setup>
import { computed } from 'vue'
import { copyToClipboard, useQuasar } from 'quasar'

import { displayValue } from 'src/utils/cdrFormat'

const props = defineProps({
  value: { type: [String, Number, Boolean], default: null },
  label: { type: String, default: 'value' },
  mono: { type: Boolean, default: true },
})

const $q = useQuasar()
const text = computed(() => displayValue(props.value))

async function copy() {
  try {
    await copyToClipboard(text.value)
    $q.notify({ type: 'positive', message: `${props.label} copied.`, timeout: 1200 })
  } catch {
    $q.notify({ type: 'negative', message: 'Unable to copy to the clipboard.' })
  }
}
</script>
