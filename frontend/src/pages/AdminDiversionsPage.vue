<!--
SPDX-FileCopyrightText: Copyright 2026, Slinky Software
SPDX-License-Identifier: GPL-3.0-only
-->

<template>
  <q-page class="page-frame soft-grid">
    <section class="page-hero">
      <div class="section-kicker">App Admin</div>
      <h1 class="page-title">Manage Diversions</h1>
      <p class="page-subtitle">Validate source DNs against CUCM, create local diversion records and keep group ownership explicit.</p>
    </section>

    <div class="row q-col-gutter-lg">
      <div class="col-12 col-lg-4">
        <section class="form-panel q-pa-lg soft-grid">
          <div>
            <div class="text-subtitle2 text-orange-2">Validate source number</div>
            <div class="row q-col-gutter-sm q-mt-sm">
              <div class="col">
                <q-input v-model="sourceNumber" filled dense label="Source DN" />
              </div>
              <div class="col-auto">
                <q-btn color="orange-6" text-color="black" label="Validate" @click="handleValidateSource" />
              </div>
            </div>
            <div v-if="sourceValidation" class="status-panel q-pa-md q-mt-md">
              <div><strong>Exists in CUCM:</strong> {{ sourceValidation.exists_in_cucm ? 'Yes' : 'No' }}</div>
              <div><strong>Already in app:</strong> {{ sourceValidation.already_exists_in_app ? 'Yes' : 'No' }}</div>
              <div><strong>Line name:</strong> {{ sourceValidation.line_name || 'Not available' }}</div>
              <div><strong>Current destination:</strong> {{ sourceValidation.current_destination || 'None' }}</div>
            </div>
          </div>

          <div>
            <div class="text-subtitle2 text-orange-2">{{ editingId ? 'Edit diversion metadata' : 'Create diversion' }}</div>
            <q-form class="q-gutter-md q-mt-sm" @submit.prevent="handleSaveDiversion">
              <q-input v-model="form.name" filled label="Name" />
              <q-input v-model="form.description" filled type="textarea" autogrow label="Description" />
              <q-input v-model="form.source_number" filled label="Source number" :disable="Boolean(editingId)" />
              <q-select v-model="form.group_id" filled label="Group" :options="groupOptions" emit-value map-options />
              <div class="row q-gutter-sm">
                <q-btn color="orange-6" text-color="black" :label="editingId ? 'Update diversion' : 'Create diversion'" type="submit" />
                <q-btn flat color="grey-4" label="Reset" @click="resetForm" />
              </div>
            </q-form>
          </div>
        </section>
      </div>

      <div class="col-12 col-lg-8">
        <section class="table-panel q-pa-lg">
          <q-table :rows="diversions" :columns="columns" row-key="id" flat :rows-per-page-options="[10, 20, 50, 0]" :pagination="{ rowsPerPage: 10 }">
            <template #body-cell-group="props">
              <q-td :props="props">{{ props.row.group?.name }}</q-td>
            </template>

            <template #body-cell-actions="props">
              <q-td :props="props" class="q-gutter-sm">
                <q-btn flat round dense icon="sync" color="orange-4" @click="handleRefresh(props.row.id)" />
                <q-btn flat round dense icon="edit" color="orange-3" @click="beginEdit(props.row)" />
                <q-btn flat round dense icon="delete" color="red-3" @click="handleDeleteDiversion(props.row)" />
              </q-td>
            </template>
          </q-table>
        </section>
      </div>
    </div>
  </q-page>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useQuasar } from 'quasar'

import {
  createDiversion,
  deleteAdminDiversion,
  listAdminDiversions,
  listGroups,
  refreshDiversion,
  updateAdminDiversion,
  validateSourceNumber,
} from 'src/services/toolboxApi'
import { extractApiMessage } from 'src/utils/format'

const $q = useQuasar()

const groups = ref([])
const diversions = ref([])
const sourceNumber = ref('')
const sourceValidation = ref(null)
const editingId = ref('')
const form = ref({ name: '', description: '', source_number: '', group_id: null })

const groupOptions = computed(() => groups.value.map((group) => ({ label: group.name, value: group.id })))

const columns = [
  { name: 'name', label: 'Name', field: 'name', align: 'left' },
  { name: 'source_number', label: 'Source DN', field: 'source_number', align: 'left' },
  { name: 'cached_current_destination', label: 'Cached destination', field: 'cached_current_destination', align: 'left' },
  { name: 'group', label: 'Group', field: 'group', align: 'left' },
  { name: 'actions', label: 'Actions', field: 'actions', align: 'right' },
]

function resetForm() {
  editingId.value = ''
  form.value = { name: '', description: '', source_number: '', group_id: null }
}

function beginEdit(diversion) {
  editingId.value = diversion.id
  form.value = {
    name: diversion.name,
    description: diversion.description,
    source_number: diversion.source_number,
    group_id: diversion.group?.id || null,
  }
}

async function loadData() {
  ;[groups.value, diversions.value] = await Promise.all([listGroups(), listAdminDiversions()])
}

async function handleValidateSource() {
  try {
    const result = await validateSourceNumber(sourceNumber.value)
    sourceValidation.value = result
    sourceNumber.value = result.source_number
    if (!editingId.value && result.is_valid) {
      form.value.source_number = result.source_number
      form.value.name = result.line_name || ''
    }
  } catch (error) {
    $q.notify({ type: 'negative', message: extractApiMessage(error, 'Source number validation failed.') })
  }
}

async function handleSaveDiversion() {
  try {
    if (editingId.value) {
      await updateAdminDiversion(editingId.value, {
        name: form.value.name,
        description: form.value.description,
        group_id: form.value.group_id,
      })
      $q.notify({ type: 'positive', message: 'Diversion updated.' })
    } else {
      await createDiversion(form.value)
      $q.notify({ type: 'positive', message: 'Diversion created.' })
    }
    resetForm()
    await loadData()
  } catch (error) {
    $q.notify({ type: 'negative', message: extractApiMessage(error, 'Unable to save diversion.') })
  }
}

async function handleRefresh(id) {
  try {
    await refreshDiversion(id)
    await loadData()
    $q.notify({ type: 'positive', message: 'Diversion refreshed.' })
  } catch (error) {
    $q.notify({ type: 'negative', message: extractApiMessage(error, 'Unable to refresh diversion.') })
  }
}

async function handleDeleteDiversion(diversion) {
  try {
    await $q.dialog({
      title: 'Delete diversion',
      message: 'This removes the diversion from Telephony Toolbox only. CUCM will not be changed.',
      cancel: true,
      persistent: true,
    }).onOk(async () => {
      await deleteAdminDiversion(diversion.id)
      await loadData()
      $q.notify({ type: 'positive', message: 'Diversion deleted.' })
    })
  } catch {
    // Dialog cancelled.
  }
}

onMounted(async () => {
  try {
    await loadData()
  } catch (error) {
    $q.notify({ type: 'negative', message: extractApiMessage(error, 'Unable to load diversions.') })
  }
})
</script>