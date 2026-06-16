<!--
SPDX-FileCopyrightText: Copyright 2026, Slinky Software
SPDX-License-Identifier: GPL-3.0-only
-->

<template>
  <q-page class="page-frame soft-grid">
    <section class="page-hero">
      <div class="section-kicker">App Admin</div>
      <h1 class="page-title">Manage Users</h1>
      <p class="page-subtitle">
        Validate external identities, provision local fallback users, assign roles and bind access
        groups.
      </p>
    </section>

    <div class="row q-col-gutter-lg">
      <div class="col-12 col-lg-4">
        <section class="form-panel q-pa-lg soft-grid">
          <div>
            <div class="text-subtitle2 text-orange-2">Validate external user</div>
            <div class="row q-col-gutter-sm q-mt-sm">
              <div class="col">
                <q-input
                  v-model="validationEmail"
                  filled
                  dense
                  label="Email"
                  @update:model-value="handleValidationEmailInput"
                />
              </div>
              <div class="col-auto">
                <q-btn
                  color="orange-6"
                  text-color="black"
                  label="Validate"
                  :disable="!trimmedValidationEmail"
                  @click="handleValidateExternalUser"
                />
              </div>
            </div>
            <div v-if="externalValidation" class="status-panel q-pa-md q-mt-md">
              <div><strong>Exists:</strong> {{ externalValidation.exists ? 'Yes' : 'No' }}</div>
              <div><strong>Provider:</strong> {{ externalValidation.provider }}</div>
              <div>
                <strong>Display name:</strong>
                {{ externalValidation.display_name || 'Not returned' }}
              </div>
            </div>
          </div>

          <div>
            <div class="text-subtitle2 text-orange-2">
              {{ editingId ? 'Edit user' : 'Create user' }}
            </div>
            <q-form ref="userFormRef" class="q-gutter-md q-mt-sm" @submit.prevent="handleSaveUser">
              <q-input
                v-model="form.email"
                filled
                label="Email"
                :disable="isEmailLocked"
                :rules="[emailRule]"
                lazy-rules="ondemand"
              />
              <q-input
                v-model="form.display_name"
                filled
                label="Display name"
                :rules="[displayNameRule]"
                lazy-rules="ondemand"
              />
              <q-select
                v-model="form.auth_source"
                filled
                label="Auth source"
                :options="authSourceOptions"
                emit-value
                map-options
                :rules="[authSourceRule]"
                lazy-rules="ondemand"
                @update:model-value="handleAuthSourceChange"
              />
              <q-select
                v-model="form.role"
                filled
                label="Role"
                :options="roleOptions"
                emit-value
                map-options
              />
              <q-select
                v-model="form.group_ids"
                filled
                multiple
                use-chips
                label="Groups"
                :options="groupOptions"
                emit-value
                map-options
                :rules="[groupRule]"
                lazy-rules="ondemand"
              />
              <q-input
                v-model="form.password"
                filled
                type="password"
                label="Password"
                :disable="!isLocalAuthSource"
                :rules="[passwordRule]"
                lazy-rules="ondemand"
                hint="Required when creating a local user."
              />
              <q-toggle v-model="form.is_active" label="User is active" color="orange-5" />
              <div class="row q-gutter-sm">
                <q-btn
                  color="orange-6"
                  text-color="black"
                  :label="editingId ? 'Update user' : 'Create user'"
                  type="submit"
                />
                <q-btn flat color="grey-4" label="Reset" @click="resetForm" />
              </div>
            </q-form>
          </div>
        </section>
      </div>

      <div class="col-12 col-lg-8">
        <section class="table-panel q-pa-lg">
          <div class="row items-center q-col-gutter-md q-mb-md">
            <div class="col">
              <q-input v-model="search" filled dense label="Search users" />
            </div>
            <div class="col-auto">
              <q-btn outline color="orange-3" label="Reload" @click="loadData" />
            </div>
          </div>

          <q-table
            :rows="filteredUsers"
            :columns="columns"
            row-key="id"
            flat
            :rows-per-page-options="[10, 20, 50, 0]"
            :pagination="{ rowsPerPage: 10 }"
          >
            <template #body-cell-email="props">
              <q-td :props="props">
                <div class="row items-center no-wrap q-gutter-sm">
                  <q-icon
                    :name="props.row.is_active ? 'check_circle' : 'cancel'"
                    :color="props.row.is_active ? 'positive' : 'negative'"
                    :title="props.row.is_active ? 'Enabled user' : 'Disabled user'"
                    size="18px"
                  />
                  <span>{{ props.value }}</span>
                </div>
              </q-td>
            </template>

            <template #body-cell-groups="props">
              <q-td :props="props">{{
                props.row.groups.map((group) => group.name).join(', ') || 'None'
              }}</q-td>
            </template>

            <template #body-cell-actions="props">
              <q-td :props="props" class="q-gutter-sm">
                <q-btn
                  flat
                  round
                  dense
                  icon="edit"
                  color="orange-3"
                  @click="beginEdit(props.row)"
                />
                <q-btn
                  flat
                  round
                  dense
                  icon="delete"
                  color="red-3"
                  @click="handleDeleteUser(props.row)"
                />
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
  createUser,
  deleteUser,
  listGroups,
  listUsers,
  updateUser,
  validateExternalUser,
} from 'src/services/toolboxApi'
import { extractApiMessage } from 'src/utils/format'
import { useSessionStore } from 'src/stores/session'

const $q = useQuasar()
const session = useSessionStore()

const users = ref([])
const groups = ref([])
const search = ref('')
const validationEmail = ref('')
const externalValidation = ref(null)
const editingId = ref('')
const userFormRef = ref(null)

const form = ref(defaultFormState())

const authSourceOptions = computed(() => {
  const mode = session.authOptions?.auth_mode || 'entra'
  return [
    { label: 'Local', value: 'local' },
    { label: mode === 'ldap' ? 'LDAP' : 'Entra', value: mode },
  ]
})

const groupOptions = computed(() =>
  groups.value.map((group) => ({ label: group.name, value: group.id })),
)
const trimmedValidationEmail = computed(() => validationEmail.value.trim())
const isEditing = computed(() => Boolean(editingId.value))
const isLocalAuthSource = computed(() => form.value.auth_source === 'local')
const hasValidatedExternalIdentity = computed(() => Boolean(externalValidation.value))
const isEmailLocked = computed(() => isEditing.value || hasValidatedExternalIdentity.value)
const roleOptions = [
  { label: 'Standard User', value: 'standard_user' },
  { label: 'App Admin', value: 'app_admin' },
]

const emailRule = (value) => Boolean(String(value || '').trim()) || 'Email is required.'
const displayNameRule = (value) =>
  Boolean(String(value || '').trim()) || 'Display name is required.'
const authSourceRule = (value) => Boolean(value) || 'Auth source is required.'
const groupRule = (value) =>
  (Array.isArray(value) && value.length > 0) || 'Select at least one group.'
const passwordRule = (value) => {
  if (!isLocalAuthSource.value || isEditing.value) {
    return true
  }
  return Boolean(String(value || '').trim()) || 'Password is required for local users.'
}

const columns = [
  { name: 'email', label: 'Email', field: 'email', align: 'left' },
  { name: 'display_name', label: 'Display name', field: 'display_name', align: 'left' },
  { name: 'auth_source', label: 'Auth source', field: 'auth_source', align: 'left' },
  { name: 'role', label: 'Role', field: 'role', align: 'left' },
  { name: 'groups', label: 'Groups', field: 'groups', align: 'left' },
  { name: 'actions', label: 'Actions', field: 'actions', align: 'right' },
]

const filteredUsers = computed(() => {
  const term = search.value.trim().toLowerCase()
  if (!term) {
    return users.value
  }
  return users.value.filter((user) =>
    [user.email, user.display_name, user.auth_source, user.role].some((value) =>
      value.toLowerCase().includes(term),
    ),
  )
})

function resetForm() {
  validationEmail.value = ''
  externalValidation.value = null
  editingId.value = ''
  form.value = defaultFormState()
  userFormRef.value?.resetValidation()
}

function beginEdit(user) {
  validationEmail.value = ''
  externalValidation.value = null
  editingId.value = user.id
  form.value = {
    email: user.email,
    display_name: user.display_name,
    auth_source: user.auth_source,
    role: user.role,
    group_ids: user.groups.map((group) => group.id),
    password: '',
    is_active: user.is_active,
  }
  userFormRef.value?.resetValidation()
}

function defaultFormState() {
  return {
    email: '',
    display_name: '',
    auth_source: 'local',
    role: 'standard_user',
    group_ids: [],
    password: '',
    is_active: true,
  }
}

function normalizeEmail(value) {
  return String(value || '')
    .trim()
    .toLowerCase()
}

function handleValidationEmailInput(value) {
  if (isEditing.value) {
    return
  }

  const nextEmail = normalizeEmail(value)
  const validatedEmail = normalizeEmail(externalValidation.value?.email)
  if (!validatedEmail || nextEmail === validatedEmail) {
    return
  }

  externalValidation.value = null
  form.value.email = ''
  form.value.display_name = ''
  if (form.value.auth_source !== 'local') {
    form.value.auth_source = 'local'
  }
}

function handleAuthSourceChange(authSource) {
  if (authSource !== 'local') {
    form.value.password = ''
  }
}

async function loadData() {
  ;[users.value, groups.value] = await Promise.all([listUsers(), listGroups()])
}

async function handleValidateExternalUser() {
  try {
    const result = await validateExternalUser(trimmedValidationEmail.value)
    externalValidation.value = result
    validationEmail.value = result.email || trimmedValidationEmail.value

    if (!isEditing.value) {
      form.value.email = result.email || trimmedValidationEmail.value
      form.value.display_name = result.display_name || ''
      form.value.auth_source = result.provider || form.value.auth_source
      if (form.value.auth_source !== 'local') {
        form.value.password = ''
      }
      userFormRef.value?.resetValidation()
    }
  } catch (error) {
    $q.notify({
      type: 'negative',
      message: extractApiMessage(error, 'External validation failed.'),
    })
  }
}

async function handleSaveUser() {
  const isValid = await userFormRef.value?.validate()
  if (!isValid) {
    return
  }

  const payload = { ...form.value }
  if (!payload.password) {
    delete payload.password
  }
  try {
    if (editingId.value) {
      await updateUser(editingId.value, payload)
      $q.notify({ type: 'positive', message: 'User updated.' })
    } else {
      await createUser(payload)
      $q.notify({ type: 'positive', message: 'User created.' })
    }
    resetForm()
    await loadData()
  } catch (error) {
    $q.notify({ type: 'negative', message: extractApiMessage(error, 'Unable to save user.') })
  }
}

async function handleDeleteUser(user) {
  try {
    await $q
      .dialog({
        title: 'Delete user',
        message: 'This hard deletes the user record. Historical audit entries will remain.',
        cancel: true,
        persistent: true,
      })
      .onOk(async () => {
        await deleteUser(user.id)
        await loadData()
        $q.notify({ type: 'positive', message: 'User deleted.' })
      })
  } catch {
    // Dialog cancelled.
  }
}

onMounted(async () => {
  try {
    await loadData()
  } catch (error) {
    $q.notify({ type: 'negative', message: extractApiMessage(error, 'Unable to load users.') })
  }
})
</script>
