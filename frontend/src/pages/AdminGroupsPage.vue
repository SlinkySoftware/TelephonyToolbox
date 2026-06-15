<!--
SPDX-FileCopyrightText: Copyright 2026, Slinky Software
SPDX-License-Identifier: GPL-3.0-only
-->

<template>
  <q-page class="page-frame soft-grid">
    <section class="page-hero">
      <div class="section-kicker">App Admin</div>
      <h1 class="page-title">Manage Groups</h1>
      <p class="page-subtitle">Shape the local access model without exposing unrelated diversions to standard users.</p>
    </section>

    <div class="row q-col-gutter-lg">
      <div class="col-12 col-lg-4">
        <section class="form-panel q-pa-lg">
          <div class="text-subtitle2 text-orange-2">{{ editingId ? 'Edit group' : 'Create group' }}</div>
          <q-form class="q-gutter-md q-mt-sm" @submit.prevent="handleSaveGroup">
            <q-input v-model="form.name" filled label="Group name" />
            <q-input v-model="form.description" filled type="textarea" autogrow label="Description" />
            <div class="row q-gutter-sm">
              <q-btn color="orange-6" text-color="black" :label="editingId ? 'Update group' : 'Create group'" type="submit" />
              <q-btn flat color="grey-4" label="Reset" @click="resetForm" />
            </div>
          </q-form>
        </section>
      </div>

      <div class="col-12 col-lg-8">
        <section class="table-panel q-pa-lg">
          <q-table :rows="groups" :columns="columns" row-key="id" flat :pagination="{ rowsPerPage: 8 }">
            <template #body-cell-actions="props">
              <q-td :props="props" class="q-gutter-sm">
                <q-btn flat round dense icon="edit" color="orange-3" @click="beginEdit(props.row)" />
                <q-btn flat round dense icon="delete" color="red-3" @click="handleDeleteGroup(props.row)" />
              </q-td>
            </template>
          </q-table>
        </section>
      </div>
    </div>
  </q-page>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { useQuasar } from 'quasar'

import { createGroup, deleteGroup, listGroups, updateGroup } from 'src/services/toolboxApi'
import { extractApiMessage } from 'src/utils/format'

const $q = useQuasar()

const groups = ref([])
const editingId = ref('')
const form = ref({ name: '', description: '' })

const columns = [
  { name: 'name', label: 'Name', field: 'name', align: 'left' },
  { name: 'description', label: 'Description', field: 'description', align: 'left' },
  { name: 'user_count', label: 'Users', field: 'user_count', align: 'center' },
  { name: 'diversion_count', label: 'Diversions', field: 'diversion_count', align: 'center' },
  { name: 'actions', label: 'Actions', field: 'actions', align: 'right' },
]

function resetForm() {
  editingId.value = ''
  form.value = { name: '', description: '' }
}

function beginEdit(group) {
  editingId.value = group.id
  form.value = { name: group.name, description: group.description }
}

async function loadGroups() {
  groups.value = await listGroups()
}

async function handleSaveGroup() {
  try {
    if (editingId.value) {
      await updateGroup(editingId.value, form.value)
      $q.notify({ type: 'positive', message: 'Group updated.' })
    } else {
      await createGroup(form.value)
      $q.notify({ type: 'positive', message: 'Group created.' })
    }
    resetForm()
    await loadGroups()
  } catch (error) {
    $q.notify({ type: 'negative', message: extractApiMessage(error, 'Unable to save group.') })
  }
}

async function handleDeleteGroup(group) {
  try {
    await $q.dialog({ title: 'Delete group', message: 'Deletion is blocked if diversions are assigned to this group.', cancel: true, persistent: true }).onOk(async () => {
      await deleteGroup(group.id)
      await loadGroups()
      $q.notify({ type: 'positive', message: 'Group deleted.' })
    })
  } catch (error) {
    if (error) {
      $q.notify({ type: 'negative', message: extractApiMessage(error, 'Unable to delete group.') })
    }
  }
}

onMounted(async () => {
  try {
    await loadGroups()
  } catch (error) {
    $q.notify({ type: 'negative', message: extractApiMessage(error, 'Unable to load groups.') })
  }
})
</script>