<!--
SPDX-FileCopyrightText: Copyright 2026, Slinky Software
SPDX-License-Identifier: GPL-3.0-only
-->

<template>
  <nav class="cdr-module-bar" aria-label="AudioCodes CDR sections">
    <q-tabs dense inline-label no-caps align="left" active-color="primary" class="cdr-module-tabs">
      <q-route-tab to="/admin/cdr" icon="manage_search" label="Search" :exact="!onSession" />
      <q-route-tab to="/admin/cdr/statistics" icon="insights" label="Statistics" exact />
      <q-route-tab to="/admin/cdr/settings" icon="tune" label="Settings" exact />
    </q-tabs>

    <div v-if="showDurationToggle" class="cdr-duration-pref">
      <span id="cdr-duration-pref-label" class="text-caption muted-copy">Durations</span>
      <q-btn-toggle
        :model-value="display.durationFormat"
        :options="DURATION_FORMATS"
        dense
        no-caps
        unelevated
        toggle-color="primary"
        color="white"
        text-color="primary"
        class="cdr-duration-pref__toggle"
        aria-labelledby="cdr-duration-pref-label"
        :disable="display.savingPreference"
        @update:model-value="changeFormat"
      />
    </div>
  </nav>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { useQuasar } from 'quasar'

import { describeCdrError } from 'src/services/cdrApi'
import { useCdrDisplayStore } from 'src/stores/cdrDisplay'
import { DURATION_FORMATS } from 'src/utils/cdrFormat'

defineProps({
  showDurationToggle: { type: Boolean, default: true },
})

const $q = useQuasar()
const route = useRoute()
const display = useCdrDisplayStore()

const onSession = computed(() => route.path.startsWith('/admin/cdr/sessions/'))

async function changeFormat(format) {
  try {
    await display.setDurationFormat(format)
  } catch (error) {
    $q.notify({
      type: 'negative',
      message: describeCdrError(error, 'Unable to save the duration format preference.').message,
    })
  }
}
</script>
