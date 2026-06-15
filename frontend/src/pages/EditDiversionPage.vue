<template>
  <q-page class="page-frame soft-grid">
    <section class="page-hero">
      <div class="section-kicker">Update Forwarding</div>
      <h1 class="page-title">{{ diversion?.name || 'Edit Diversion' }}</h1>
      <p class="page-subtitle">Validate and normalise the destination before CUCM is updated. The application only reports clean success after read-back confirmation.</p>
    </section>

    <q-banner v-if="diversion?.cucm_status !== 'available'" class="warning-banner text-white q-pa-md">
      CUCM is currently unavailable. Cached diversion information is displayed and updates are temporarily disabled.
    </q-banner>

    <div class="row q-col-gutter-lg">
      <div class="col-12 col-lg-5">
        <section class="card-panel q-pa-lg">
          <div class="text-subtitle2 text-orange-2">Current state</div>
          <div class="q-mt-md muted-copy">Source DN</div>
          <div class="text-h6">{{ diversion?.source_number }}</div>
          <div class="q-mt-md muted-copy">Cached destination</div>
          <div class="text-h6">{{ diversion?.cached_current_destination || 'None recorded' }}</div>
          <div class="q-mt-md muted-copy">Last refreshed</div>
          <div>{{ formatDateTime(diversion?.last_refreshed_at) }}</div>
        </section>
      </div>

      <div class="col-12 col-lg-7">
        <section class="form-panel q-pa-lg">
          <q-form class="q-gutter-md" @submit.prevent="prepareUpdate">
            <q-input v-model="destination" filled label="New destination" hint="Australian FNN, mobile or +E.164 only" />

            <div v-if="validationResult" class="status-panel q-pa-md">
              <div class="text-subtitle2 text-orange-2">Validation result</div>
              <div class="q-mt-sm">
                <strong v-if="validationResult.is_valid">Normalised destination:</strong>
                <strong v-else>Error:</strong>
                <span class="q-ml-sm">{{ validationSummary }}</span>
              </div>
            </div>

            <div class="row q-gutter-sm">
              <q-btn outline color="orange-3" label="Validate" @click="runValidation" :loading="validating" />
              <q-btn color="orange-6" text-color="black" label="Save diversion" type="submit" :disable="diversion?.cucm_status !== 'available'" :loading="saving" />
              <q-btn flat color="grey-4" label="Back" @click="router.push('/diversions')" />
            </div>
          </q-form>
        </section>
      </div>
    </div>

    <q-dialog v-model="confirmOpen">
      <q-card style="min-width: 360px; max-width: 520px">
        <q-card-section>
          <div class="text-h6">Confirm diversion update</div>
        </q-card-section>
        <q-card-section class="q-gutter-y-sm">
          <div><strong>Diversion:</strong> {{ diversion?.name }}</div>
          <div><strong>Source DN:</strong> {{ diversion?.source_number }}</div>
          <div><strong>Entered destination:</strong> {{ destination }}</div>
          <div><strong>Normalised destination:</strong> {{ validationResult?.normalised_destination }}</div>
        </q-card-section>
        <q-card-actions align="right">
          <q-btn flat label="Cancel" v-close-popup />
          <q-btn color="orange-6" text-color="black" label="Confirm update" @click="saveUpdate" />
        </q-card-actions>
      </q-card>
    </q-dialog>
  </q-page>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useQuasar } from 'quasar'
import { useRouter } from 'vue-router'

import { getDiversion, updateDiversionDestination, validateDiversionDestination } from 'src/services/toolboxApi'
import { extractApiMessage, formatDateTime } from 'src/utils/format'

const props = defineProps({
  id: {
    type: String,
    required: true,
  },
})

const $q = useQuasar()
const router = useRouter()

const diversion = ref(null)
const destination = ref('')
const validationResult = ref(null)
const validating = ref(false)
const saving = ref(false)
const confirmOpen = ref(false)

const validationSummary = computed(() => {
  if (!validationResult.value) {
    return ''
  }
  return validationResult.value.is_valid ? validationResult.value.normalised_destination : validationResult.value.message
})

async function loadDiversion() {
  diversion.value = await getDiversion(props.id)
}

async function runValidation() {
  validating.value = true
  try {
    validationResult.value = await validateDiversionDestination(props.id, destination.value)
  } catch (error) {
    validationResult.value = error.response?.data || null
    $q.notify({ type: 'negative', message: extractApiMessage(error, 'Destination validation failed.') })
  } finally {
    validating.value = false
  }
}

async function prepareUpdate() {
  await runValidation()
  if (validationResult.value?.is_valid) {
    confirmOpen.value = true
  }
}

async function saveUpdate() {
  saving.value = true
  try {
    const response = await updateDiversionDestination(props.id, destination.value)
    diversion.value = response.diversion
    confirmOpen.value = false
    $q.notify({ type: 'positive', message: response.message || 'Diversion updated successfully.' })
    await router.replace('/diversions')
  } catch (error) {
    $q.notify({ type: 'negative', message: extractApiMessage(error, 'Unable to update diversion.') })
  } finally {
    saving.value = false
  }
}

onMounted(async () => {
  try {
    await loadDiversion()
  } catch (error) {
    $q.notify({ type: 'negative', message: extractApiMessage(error, 'Unable to load diversion details.') })
    await router.replace('/diversions')
  }
})
</script>