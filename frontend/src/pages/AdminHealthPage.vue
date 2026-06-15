<template>
  <q-page class="page-frame soft-grid">
    <section class="page-hero">
      <div class="section-kicker">App Admin</div>
      <h1 class="page-title">System Health</h1>
      <p class="page-subtitle">Inspect application, database, CUCM and authentication readiness without exposing secret values.</p>
    </section>

    <div class="metric-grid" v-if="health">
      <div class="card-panel metric-card">
        <div class="muted-copy">Application</div>
        <div class="metric-value">{{ health.application.status }}</div>
        <div class="muted-copy">Version {{ health.application.version }}</div>
      </div>
      <div class="card-panel metric-card">
        <div class="muted-copy">Database</div>
        <div class="metric-value">{{ health.database.status }}</div>
      </div>
      <div class="card-panel metric-card">
        <div class="muted-copy">CUCM</div>
        <div class="metric-value">{{ health.cucm.status }}</div>
        <div class="muted-copy">Version {{ health.cucm.version }}</div>
      </div>
      <div class="card-panel metric-card">
        <div class="muted-copy">Auth</div>
        <div class="metric-value">{{ health.auth.status }}</div>
        <div class="muted-copy">Mode {{ health.auth.mode }}</div>
      </div>
    </div>

    <section v-if="health" class="status-panel q-pa-lg">
      <div class="text-subtitle2 text-orange-2">Environment readiness</div>
      <div class="q-mt-sm">Required variables present: {{ health.environment.required_variables_present ? 'Yes' : 'No' }}</div>
      <div v-if="health.environment.missing?.length" class="muted-copy q-mt-sm">
        Missing: {{ health.environment.missing.join(', ') }}
      </div>
    </section>
  </q-page>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { useQuasar } from 'quasar'

import { getAdminHealth } from 'src/services/toolboxApi'
import { extractApiMessage } from 'src/utils/format'

const $q = useQuasar()
const health = ref(null)

onMounted(async () => {
  try {
    health.value = await getAdminHealth()
  } catch (error) {
    $q.notify({ type: 'negative', message: extractApiMessage(error, 'Unable to load system health.') })
  }
})
</script>