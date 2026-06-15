<!--
SPDX-FileCopyrightText: Copyright 2026, Slinky Software
SPDX-License-Identifier: GPL-3.0-only
-->

<template>
  <q-page class="page-frame soft-grid">
    <section class="page-hero">
      <div class="section-kicker">App Admin</div>
      <h1 class="page-title">Audit Log</h1>
      <p class="page-subtitle">Filter operational history and export the currently selected window to CSV.</p>
    </section>

    <section class="form-panel q-pa-lg soft-grid">
      <div class="row q-col-gutter-md">
        <div class="col-12 col-md-3"><q-input v-model="filters.actor_email" filled dense label="Actor email" /></div>
        <div class="col-12 col-md-2"><q-input v-model="filters.event_type" filled dense label="Event type" /></div>
        <div class="col-12 col-md-2"><q-input v-model="filters.result" filled dense label="Result" /></div>
        <div class="col-12 col-md-2"><q-input v-model="filters.source_number" filled dense label="Source number" /></div>
        <div class="col-12 col-md-3 row q-gutter-sm items-start">
          <q-btn color="orange-6" text-color="black" label="Apply filters" @click="loadAudit" />
          <q-btn outline color="orange-3" label="Export CSV" :href="exportUrl" target="_blank" />
        </div>
      </div>
    </section>

    <section class="table-panel q-pa-lg">
      <q-table :rows="rows" :columns="columns" row-key="id" flat :loading="loading" :pagination="{ rowsPerPage: 10 }">
        <template #body-cell-timestamp="props">
          <q-td :props="props">{{ formatDateTime(props.row.timestamp) }}</q-td>
        </template>
      </q-table>
    </section>
  </q-page>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useQuasar } from 'quasar'

import { listAudit } from 'src/services/toolboxApi'
import { buildCsvExportUrl, extractApiMessage, formatDateTime } from 'src/utils/format'

const $q = useQuasar()

const loading = ref(false)
const rows = ref([])
const filters = ref({ actor_email: '', event_type: '', result: '', source_number: '' })

const columns = [
  { name: 'timestamp', label: 'Timestamp', field: 'timestamp', align: 'left' },
  { name: 'actor_email', label: 'Actor', field: 'actor_email', align: 'left' },
  { name: 'event_type', label: 'Event type', field: 'event_type', align: 'left' },
  { name: 'result', label: 'Result', field: 'result', align: 'left' },
  { name: 'object_name', label: 'Object', field: 'object_name', align: 'left' },
  { name: 'message', label: 'Message', field: 'message', align: 'left' },
]

const exportUrl = computed(() => buildCsvExportUrl(filters.value))

async function loadAudit() {
  loading.value = true
  try {
    const data = await listAudit(filters.value)
    rows.value = data.results || []
  } catch (error) {
    $q.notify({ type: 'negative', message: extractApiMessage(error, 'Unable to load audit events.') })
  } finally {
    loading.value = false
  }
}

onMounted(loadAudit)
</script>