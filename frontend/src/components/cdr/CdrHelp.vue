<!--
SPDX-FileCopyrightText: Copyright 2026, Slinky Software
SPDX-License-Identifier: GPL-3.0-only
-->

<template>
  <q-btn
    v-if="text"
    flat
    round
    dense
    size="xs"
    icon="help_outline"
    class="cdr-help"
    :aria-label="`Help: ${label}`"
  >
    <q-tooltip max-width="320px" class="cdr-help__tooltip">{{ text }}</q-tooltip>
    <q-menu max-width="360px" anchor="bottom left" self="top left">
      <div class="q-pa-md cdr-help__panel">
        <div class="text-subtitle2">{{ label }}</div>
        <div class="q-mt-xs">{{ text }}</div>
        <div v-if="source" class="text-caption muted-copy q-mt-sm">{{ source }}</div>
      </div>
    </q-menu>
  </q-btn>
</template>

<script setup>
defineProps({
  text: { type: String, default: '' },
  label: { type: String, default: 'Field' },
  source: { type: String, default: '' },
})
</script>
