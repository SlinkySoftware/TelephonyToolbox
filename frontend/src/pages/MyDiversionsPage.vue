<!--
SPDX-FileCopyrightText: Copyright 2026, Slinky Software
SPDX-License-Identifier: GPL-3.0-only
-->

<template>
  <q-page class="page-frame soft-grid">
    <section class="page-hero">
      <div class="section-kicker">Assigned Work</div>
      <h1 class="page-title">My Diversions</h1>
      <p class="page-subtitle">Refresh live state from CUCM, inspect the cached forwarding destination, and update only the lines you’re authorised to control.</p>
    </section>

    <q-banner v-if="cucmUnavailable" class="warning-banner text-white q-pa-md">
      CUCM is currently unavailable. Cached diversion information is displayed. Diversion updates are temporarily disabled.
    </q-banner>

    <section class="table-panel q-pa-lg">
      <div class="row items-center q-col-gutter-md q-mb-md">
        <div class="col-12 col-md">
          <q-input v-model="search" filled dense label="Search diversions" />
        </div>
        <div class="col-12 col-md-auto">
          <q-btn color="orange-6" text-color="black" label="Reload list" @click="loadDiversions" :loading="loading" />
        </div>
      </div>

      <q-table
        flat
        :rows="filteredDiversions"
        :columns="columns"
        row-key="id"
        :loading="loading"
        :rows-per-page-options="[10, 20, 50, 0]"
        :pagination="{ rowsPerPage: 10 }"
      >
        <template #body-cell-last_refreshed_at="props">
          <q-td :props="props">{{ formatDateTime(props.row.last_refreshed_at) }}</q-td>
        </template>

        <template #body-cell-last_updated_at="props">
          <q-td :props="props">{{ formatLastUpdated(props.row) }}</q-td>
        </template>

        <template #body-cell-actions="props">
          <q-td :props="props" class="q-gutter-sm">
            <q-btn flat round dense icon="sync" color="orange-4" @click="handleRefresh(props.row)" />
            <q-btn flat round dense icon="edit" color="orange-2" :disable="props.row.cucm_status !== 'available'" @click="goToEdit(props.row.id)" />
          </q-td>
        </template>
      </q-table>
    </section>
  </q-page>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useQuasar } from 'quasar'
import { useRouter } from 'vue-router'

import { listDiversions, refreshDiversion } from 'src/services/toolboxApi'
import { extractApiMessage, formatDateTime } from 'src/utils/format'

const $q = useQuasar()
const router = useRouter()

const loading = ref(false)
const search = ref('')
const diversions = ref([])

const columns = [
  { name: 'name', label: 'Name', field: 'name', align: 'left', sortable: true },
  { name: 'source_number', label: 'Source DN', field: 'source_number', align: 'left' },
  { name: 'cached_current_destination', label: 'Cached destination', field: 'cached_current_destination', align: 'left' },
  { name: 'group', label: 'Group', field: (row) => row.group?.name || 'Unassigned', align: 'left' },
  { name: 'last_refreshed_at', label: 'Last refreshed', field: 'last_refreshed_at', align: 'left' },
  { name: 'last_updated_at', label: 'Last updated', field: 'last_updated_at', align: 'left' },
  { name: 'actions', label: 'Actions', field: 'actions', align: 'right' },
]

const filteredDiversions = computed(() => {
  const term = search.value.trim().toLowerCase()
  if (!term) {
    return diversions.value
  }
  return diversions.value.filter((item) =>
    [item.name, item.description, item.source_number, item.cached_current_destination, item.group?.name]
      .filter(Boolean)
      .some((value) => value.toLowerCase().includes(term)),
  )
})

const cucmUnavailable = computed(() => diversions.value.some((item) => item.cucm_status !== 'available'))

function formatLastUpdated(diversion) {
  const formatted = formatDateTime(diversion.last_updated_at)
  if (!diversion.last_updated_at) {
    return formatted
  }
  return diversion.last_updated_by ? `${diversion.last_updated_by} on ${formatted}` : formatted
}

async function loadDiversions() {
  loading.value = true
  try {
    diversions.value = await listDiversions()
  } catch (error) {
    $q.notify({ type: 'negative', message: extractApiMessage(error, 'Unable to load diversions.') })
  } finally {
    loading.value = false
  }
}

async function handleRefresh(diversion) {
  try {
    const response = await refreshDiversion(diversion.id)
    const index = diversions.value.findIndex((item) => item.id === diversion.id)
    if (index >= 0 && response.diversion) {
      diversions.value[index] = response.diversion
    }
    $q.notify({ type: 'positive', message: 'Diversion refreshed.' })
  } catch (error) {
    $q.notify({ type: 'negative', message: extractApiMessage(error, 'Unable to refresh diversion.') })
  }
}

function goToEdit(id) {
  router.push(`/diversions/${id}/edit`)
}

onMounted(loadDiversions)
</script>