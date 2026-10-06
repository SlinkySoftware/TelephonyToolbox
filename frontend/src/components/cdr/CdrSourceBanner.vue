<!--
SPDX-FileCopyrightText: Copyright 2026, Slinky Software
SPDX-License-Identifier: GPL-3.0-only
-->

<template>
  <div class="cdr-source-banner">
    <div class="cdr-source-banner__meta">
      <q-chip
        v-if="display.activeSourceLabel"
        dense
        square
        icon="storage"
        class="cdr-source-chip"
        :aria-label="`Active AudioCodes source: ${display.activeSourceLabel}`"
      >
        Source: {{ display.activeSourceLabel }} (read-only)
      </q-chip>
      <q-chip dense square icon="schedule" class="cdr-source-chip">Australia/Sydney</q-chip>
    </div>

    <q-banner v-if="!display.credentialUsable" dense rounded class="cdr-banner cdr-banner--warning">
      <template #avatar><q-icon name="key_off" /></template>
      The source credential cannot be used because the encryption key is missing or invalid. Contact
      an administrator.
    </q-banner>

    <q-banner
      v-if="error && (error.sourceIssue || error.timeout)"
      dense
      rounded
      class="cdr-banner"
      :class="error.timeout ? 'cdr-banner--warning' : 'cdr-banner--danger'"
      role="alert"
    >
      <template #avatar>
        <q-icon :name="error.timeout ? 'hourglass_disabled' : 'cloud_off'" />
      </template>
      <div class="text-weight-medium">
        {{ error.timeout ? 'Query timed out' : 'AudioCodes source unavailable' }}
      </div>
      <div>{{ error.message }}</div>
      <template v-if="retry" #action>
        <q-btn flat no-caps label="Retry" icon="refresh" @click="emit('retry')" />
      </template>
    </q-banner>
  </div>
</template>

<script setup>
import { useCdrDisplayStore } from 'src/stores/cdrDisplay'

defineProps({
  error: { type: Object, default: null },
  retry: { type: Boolean, default: false },
})

const emit = defineEmits(['retry'])

const display = useCdrDisplayStore()
</script>
