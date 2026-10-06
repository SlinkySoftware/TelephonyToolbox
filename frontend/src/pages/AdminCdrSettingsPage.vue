<!--
SPDX-FileCopyrightText: Copyright 2026, Slinky Software
SPDX-License-Identifier: GPL-3.0-only
-->

<template>
  <q-page class="page-frame soft-grid">
    <section class="page-hero">
      <div class="section-kicker">App Admin · AudioCodes CDR</div>
      <h1 class="page-title">CDR Settings</h1>
      <p class="page-subtitle">
        Source connection, query limits, labels, media thresholds and help text for the AudioCodes
        CDR module. Changes are audited. The source database is always accessed read-only.
      </p>
    </section>

    <CdrModuleTabs :show-duration-toggle="false" />

    <div v-if="loading" class="status-panel q-pa-lg cdr-loading" role="status">
      <q-spinner color="primary" size="1.6rem" />
      <span>Loading settings…</span>
    </div>

    <q-banner v-else-if="loadError" rounded class="cdr-banner cdr-banner--danger" role="alert">
      <template #avatar><q-icon name="error_outline" /></template>
      {{ loadError.message }}
      <template #action>
        <q-btn flat no-caps icon="refresh" label="Retry" @click="loadSettings" />
      </template>
    </q-banner>

    <q-form v-else-if="form" ref="formRef" greedy class="soft-grid" @submit="save">
      <q-banner
        v-if="settings.encryption_key_status !== 'ok'"
        rounded
        class="cdr-banner cdr-banner--warning"
        role="alert"
      >
        <template #avatar><q-icon name="key_off" /></template>
        The credential encryption key (CDR_SOURCE_ENCRYPTION_KEY) is
        {{ settings.encryption_key_status === 'missing' ? 'not configured' : 'invalid' }}. Source
        passwords cannot be saved or used until it is fixed in the deployment configuration.
      </q-banner>

      <section class="card-panel q-pa-lg" aria-labelledby="cdr-settings-source">
        <h2 id="cdr-settings-source" class="cdr-section-title">Source connection</h2>
        <p class="muted-copy">
          The module never switches sources automatically. Use a dedicated PostgreSQL account that
          only has SELECT on <span class="cdr-mono">public.sdr</span> and
          <span class="cdr-mono">public.cdr</span>.
        </p>

        <div class="cdr-settings-active">
          <span id="cdr-active-source-label" class="text-subtitle2">Active source</span>
          <q-option-group
            v-model="form.active_source"
            inline
            :options="SOURCE_OPTIONS"
            aria-labelledby="cdr-active-source-label"
          />
          <div v-if="errorAt(['active_source'])" class="text-negative text-caption">
            {{ errorAt(['active_source']) }}
          </div>
        </div>
        <q-banner
          v-if="!form.profiles[form.active_source].configured"
          dense
          rounded
          class="cdr-banner cdr-banner--warning q-mt-sm"
        >
          <template #avatar><q-icon name="warning" /></template>
          The active source has no connection profile, so the module will report the source as not
          configured.
        </q-banner>

        <div class="cdr-profile-grid q-mt-md">
          <div v-for="role in ROLES" :key="role" class="cdr-profile">
            <div class="cdr-profile__head">
              <h3 class="cdr-subsection-title">{{ SOURCE_LABELS[role] }}</h3>
              <q-toggle
                v-model="form.profiles[role].configured"
                :label="form.profiles[role].configured ? 'Configured' : 'Not configured'"
              />
            </div>

            <div v-if="form.profiles[role].configured" class="cdr-settings-fields">
              <q-input
                v-model.trim="form.profiles[role].host"
                filled
                dense
                label="Host"
                :rules="[requiredRule, hostRule]"
                :error="Boolean(errorAt(['profiles', role, 'host']))"
                :error-message="errorAt(['profiles', role, 'host'])"
              />
              <q-input
                v-model.number="form.profiles[role].port"
                filled
                dense
                type="number"
                label="Port"
                :rules="[requiredRule, intRange(1, 65535)]"
                :error="Boolean(errorAt(['profiles', role, 'port']))"
                :error-message="errorAt(['profiles', role, 'port'])"
              />
              <q-input
                v-model.trim="form.profiles[role].database_name"
                filled
                dense
                label="Database name"
                maxlength="63"
                :rules="[requiredRule, identifierRule]"
                :error="Boolean(errorAt(['profiles', role, 'database_name']))"
                :error-message="errorAt(['profiles', role, 'database_name'])"
              />
              <q-input
                v-model.trim="form.profiles[role].username"
                filled
                dense
                label="Username (read-only role)"
                maxlength="63"
                autocomplete="off"
                :rules="[requiredRule, identifierRule]"
                :error="Boolean(errorAt(['profiles', role, 'username']))"
                :error-message="errorAt(['profiles', role, 'username'])"
              />
              <q-input
                v-model="form.profiles[role].password"
                filled
                dense
                type="password"
                autocomplete="new-password"
                maxlength="1024"
                :label="form.profiles[role].has_password ? 'New password (optional)' : 'Password'"
                :hint="
                  form.profiles[role].has_password
                    ? 'A password is stored. Leave blank to keep it.'
                    : 'Required for a new profile. Stored encrypted; never displayed.'
                "
                :rules="[(value) => passwordRule(role, value)]"
                :error="Boolean(errorAt(['profiles', role, 'password']))"
                :error-message="errorAt(['profiles', role, 'password'])"
              />
              <q-select
                v-model="form.profiles[role].sslmode"
                filled
                dense
                label="SSL mode"
                :options="SSL_MODES"
                :error="Boolean(errorAt(['profiles', role, 'sslmode']))"
                :error-message="errorAt(['profiles', role, 'sslmode'])"
              />
              <q-input
                v-model.trim="form.profiles[role].sslrootcert"
                filled
                dense
                label="SSL root certificate"
                hint="Absolute path, 'system', or blank"
                :rules="[sslRootCertRule]"
                :error="Boolean(errorAt(['profiles', role, 'sslrootcert']))"
                :error-message="errorAt(['profiles', role, 'sslrootcert'])"
              />
              <q-input
                v-model.number="form.profiles[role].connect_timeout"
                filled
                dense
                type="number"
                label="Connect timeout (seconds)"
                :rules="[requiredRule, intRange(1, 60)]"
                :error="Boolean(errorAt(['profiles', role, 'connect_timeout']))"
                :error-message="errorAt(['profiles', role, 'connect_timeout'])"
              />
              <q-toggle v-model="form.profiles[role].is_enabled" label="Profile enabled" />
              <div v-if="settings.profiles?.[role]?.updated_at" class="muted-copy text-caption">
                Profile updated {{ formatSydneyTimestamp(settings.profiles[role].updated_at) }}
              </div>
            </div>
            <div v-else class="muted-copy">
              {{
                settings.profiles?.[role]
                  ? 'This profile will be removed when you save.'
                  : 'No profile is configured.'
              }}
            </div>
          </div>
        </div>
      </section>

      <section class="card-panel q-pa-lg" aria-labelledby="cdr-settings-limits">
        <h2 id="cdr-settings-limits" class="cdr-section-title">Query limits and caching</h2>
        <div class="cdr-settings-fields cdr-settings-fields--grid">
          <q-input
            v-for="field in LIMIT_FIELDS"
            :key="field.key"
            v-model.number="form[field.key]"
            filled
            dense
            type="number"
            :label="field.label"
            :hint="field.hint"
            :rules="[requiredRule, intRange(field.min, field.max)]"
            :error="Boolean(errorAt([field.key]))"
            :error-message="errorAt([field.key])"
          />
        </div>
      </section>

      <section class="card-panel q-pa-lg" aria-labelledby="cdr-settings-udf">
        <h2 id="cdr-settings-udf" class="cdr-section-title">User-defined field labels</h2>
        <p class="muted-copy">
          Labels for the CDR fields <span class="cdr-mono">varcalluserdefined1</span>–<span
            class="cdr-mono"
            >5</span
          >. A blank label uses the default.
        </p>
        <div v-for="key in UDF_KEYS" :key="key" class="cdr-udf-row">
          <div class="cdr-mono cdr-udf-row__key">{{ key }}</div>
          <q-input
            v-model="form.user_defined_fields[key].label"
            filled
            dense
            label="Label"
            maxlength="100"
            :error="Boolean(errorAt(['user_defined_fields', key, 'label']))"
            :error-message="errorAt(['user_defined_fields', key, 'label'])"
          />
          <q-input
            v-model="form.user_defined_fields[key].description"
            filled
            dense
            label="Description"
            maxlength="500"
            :error="Boolean(errorAt(['user_defined_fields', key, 'description']))"
            :error-message="errorAt(['user_defined_fields', key, 'description'])"
          />
        </div>
      </section>

      <section class="card-panel q-pa-lg" aria-labelledby="cdr-settings-media">
        <h2 id="cdr-settings-media" class="cdr-section-title">Media-quality thresholds</h2>
        <p class="muted-copy">
          Values at or above a threshold are flagged. Status is shown only when a unit and at least
          one threshold are set; units are never assumed.
        </p>
        <div v-for="metric in MEDIA_METRICS" :key="metric.key" class="cdr-media-row">
          <div class="cdr-media-row__label">
            <div>{{ metric.label }}</div>
            <div class="cdr-mono text-caption muted-copy">{{ metric.field }}</div>
          </div>
          <q-input
            v-model="form.media_quality[metric.key].warning"
            filled
            dense
            type="number"
            min="0"
            step="any"
            label="Warning at"
            :rules="[optionalNonNegative]"
            :error="Boolean(errorAt(['media_quality', metric.key, 'warning']))"
            :error-message="errorAt(['media_quality', metric.key, 'warning'])"
          />
          <q-input
            v-model="form.media_quality[metric.key].critical"
            filled
            dense
            type="number"
            min="0"
            step="any"
            label="Critical at"
            :rules="[optionalNonNegative, (value) => criticalRule(metric.key, value)]"
            :error="Boolean(errorAt(['media_quality', metric.key, 'critical']))"
            :error-message="errorAt(['media_quality', metric.key, 'critical'])"
          />
          <q-input
            v-model.trim="form.media_quality[metric.key].unit"
            filled
            dense
            label="Unit"
            maxlength="32"
            :rules="[(value) => unitRule(metric.key, value)]"
            :error="Boolean(errorAt(['media_quality', metric.key, 'unit']))"
            :error-message="errorAt(['media_quality', metric.key, 'unit'])"
          />
        </div>
      </section>

      <section class="card-panel q-pa-lg" aria-labelledby="cdr-settings-help">
        <h2 id="cdr-settings-help" class="cdr-section-title">Field help overrides</h2>
        <p class="muted-copy">
          Replace the built-in {{ display.help.version || 'AudioCodes' }} help for a field or topic,
          or add an explanation for a termination value using
          <span class="cdr-mono">termination.&lt;value&gt;</span>. Termination explanations are only
          shown where configured.
        </p>
        <div v-if="errorAt(['field_help_overrides'])" class="text-negative q-mb-sm">
          {{ errorAt(['field_help_overrides']) }}
        </div>
        <div
          v-for="(override, index) in form.help_overrides"
          :key="override.id"
          class="cdr-help-row"
        >
          <q-select
            v-model="override.key"
            filled
            dense
            use-input
            hide-selected
            fill-input
            input-debounce="0"
            new-value-mode="add-unique"
            label="Help key"
            :options="helpKeyOptions"
            :hint="defaultHelpFor(override.key)"
            :rules="[requiredRule, (value) => helpKeyRule(value, index)]"
            @filter="filterHelpKeys"
          />
          <q-input
            v-model="override.text"
            filled
            dense
            autogrow
            label="Help text"
            maxlength="2000"
            :rules="[requiredRule]"
          />
          <q-btn
            flat
            round
            dense
            color="negative"
            icon="delete"
            :aria-label="`Remove help override ${override.key || index + 1}`"
            @click="form.help_overrides.splice(index, 1)"
          />
        </div>
        <q-btn
          outline
          no-caps
          color="primary"
          icon="add"
          label="Add override"
          :disable="form.help_overrides.length >= 500"
          @click="addOverride"
        />
      </section>

      <section class="status-panel q-pa-md cdr-settings-footer">
        <div class="muted-copy text-caption">
          <template v-if="settings.updated_by">
            Last updated {{ formatSydneyTimestamp(settings.updated_at) }} by
            {{ settings.updated_by }}
            ·
          </template>
          Configuration version {{ settings.config_version }}
        </div>
        <div class="row q-gutter-sm">
          <q-btn
            flat
            no-caps
            color="primary"
            label="Discard changes"
            :disable="!dirty || saving"
            @click="discard"
          />
          <q-btn
            type="submit"
            color="primary"
            text-color="white"
            no-caps
            icon="save"
            label="Save settings"
            :loading="saving"
            :disable="!dirty"
          />
        </div>
      </section>
    </q-form>
  </q-page>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { onBeforeRouteLeave } from 'vue-router'
import { useQuasar } from 'quasar'

import CdrModuleTabs from 'src/components/cdr/CdrModuleTabs.vue'
import { describeCdrError, fetchModuleSettings, updateModuleSettings } from 'src/services/cdrApi'
import { useCdrDisplayStore } from 'src/stores/cdrDisplay'
import { useCdrLookupsStore } from 'src/stores/cdrLookups'
import { useCdrStatisticsStore } from 'src/stores/cdrStatistics'
import { formatSydneyTimestamp } from 'src/utils/cdrFormat'

const ROLES = ['replica', 'primary']
const SOURCE_LABELS = { replica: 'Read replica', primary: 'Primary' }
const SOURCE_OPTIONS = ROLES.map((role) => ({ value: role, label: SOURCE_LABELS[role] }))
const SSL_MODES = ['disable', 'prefer', 'require', 'verify-ca', 'verify-full']
const UDF_KEYS = [1, 2, 3, 4, 5].map((index) => `varcalluserdefined${index}`)
const MEDIA_METRICS = [
  { key: 'local_jitter', field: 'localjitter', label: 'Local jitter' },
  { key: 'remote_jitter', field: 'remotejitter', label: 'Remote jitter' },
  { key: 'local_packet_loss', field: 'localpacketloss', label: 'Local packet loss' },
  { key: 'remote_packet_loss', field: 'remotepacketloss', label: 'Remote packet loss' },
  { key: 'local_round_trip_delay', field: 'localroundtripdelay', label: 'Local round-trip delay' },
  {
    key: 'remote_round_trip_delay',
    field: 'remoteroundtripdelay',
    label: 'Remote round-trip delay',
  },
]
const LIMIT_FIELDS = [
  {
    key: 'max_page_size',
    label: 'Maximum page size',
    min: 25,
    max: 500,
    hint: '25–500; page sizes above this are hidden',
  },
  {
    key: 'max_multiselect_values',
    label: 'Maximum values per multi-select',
    min: 1,
    max: 200,
    hint: '1–200',
  },
  {
    key: 'lookup_cache_seconds',
    label: 'Lookup cache lifetime (seconds)',
    min: 0,
    max: 86400,
    hint: 'IP groups and termination reasons; 0 disables',
  },
  {
    key: 'statistics_cache_seconds',
    label: 'Statistics cache lifetime (seconds)',
    min: 0,
    max: 86400,
    hint: '0 disables',
  },
  {
    key: 'termination_lookup_days',
    label: 'Termination lookup window (days)',
    min: 1,
    max: 365,
    hint: 'Recent days scanned for termination values',
  },
  {
    key: 'hourly_bucket_max_hours',
    label: 'Hourly bucket threshold (hours)',
    min: 24,
    max: 744,
    hint: 'Ranges up to this use hourly intervals',
  },
]
const HOST_PATTERN = /^[A-Za-z0-9.:[\]%-]+$/
const IDENTIFIER_PATTERN = /^[^\s\x00-\x1f\x7f]+$/ // eslint-disable-line no-control-regex
const HELP_KEY_PATTERN = /^(sdr|cdr|topic)\.[a-z0-9_]+$|^termination\..+$/

const $q = useQuasar()
const display = useCdrDisplayStore()
const lookups = useCdrLookupsStore()
const stats = useCdrStatisticsStore()

const settings = ref(null)
const form = ref(null)
const formRef = ref(null)
const initialSnapshot = ref('')
const loading = ref(false)
const saving = ref(false)
const loadError = ref(null)
const saveErrors = ref(null)
const helpKeyFilter = ref('')
let overrideSeq = 0

const dirty = computed(() => Boolean(form.value) && snapshot(form.value) !== initialSnapshot.value)

const allHelpKeys = computed(() => {
  const help = display.help
  const keys = [
    ...Object.keys(help.sdr || {}).map((key) => `sdr.${key}`),
    ...Object.keys(help.cdr || {}).map((key) => `cdr.${key}`),
    ...Object.keys(help.topics || {}).map((key) => `topic.${key}`),
    ...lookups.terminationReasons.values.map((value) => `termination.${value}`),
  ]
  return [...new Set(keys)]
})
const helpKeyOptions = computed(() => {
  const term = helpKeyFilter.value.toLowerCase()
  return term
    ? allHelpKeys.value.filter((key) => key.toLowerCase().includes(term))
    : allHelpKeys.value
})

function snapshot(value) {
  return JSON.stringify(buildPayload(value))
}

function profileForm(profile) {
  return {
    configured: Boolean(profile),
    host: profile?.host || '',
    port: profile?.port ?? 5432,
    database_name: profile?.database_name || '',
    username: profile?.username || '',
    password: '',
    has_password: Boolean(profile?.has_password),
    sslmode: profile?.sslmode || 'prefer',
    sslrootcert: profile?.sslrootcert || '',
    connect_timeout: profile?.connect_timeout ?? 10,
    is_enabled: profile?.is_enabled ?? true,
  }
}

function formFromSettings(data) {
  const mediaQuality = {}
  MEDIA_METRICS.forEach(({ key }) => {
    const config = data.media_quality?.[key] || {}
    mediaQuality[key] = {
      warning: config.warning ?? '',
      critical: config.critical ?? '',
      unit: config.unit || '',
    }
  })
  const userDefined = {}
  UDF_KEYS.forEach((key) => {
    const config = data.user_defined_fields?.[key] || {}
    userDefined[key] = { label: config.label || '', description: config.description || '' }
  })
  return {
    active_source: data.active_source,
    profiles: Object.fromEntries(ROLES.map((role) => [role, profileForm(data.profiles?.[role])])),
    ...Object.fromEntries(LIMIT_FIELDS.map(({ key }) => [key, data[key]])),
    user_defined_fields: userDefined,
    media_quality: mediaQuality,
    help_overrides: Object.entries(data.field_help_overrides || {}).map(([key, text]) => ({
      id: ++overrideSeq,
      key,
      text,
    })),
  }
}

function toNumberOrNull(value) {
  if (value === '' || value === null || value === undefined) {
    return null
  }
  const number = Number(value)
  return Number.isFinite(number) ? number : null
}

function buildPayload(value) {
  const profiles = {}
  ROLES.forEach((role) => {
    const profile = value.profiles[role]
    if (!profile.configured) {
      profiles[role] = null
      return
    }
    profiles[role] = {
      host: profile.host,
      port: profile.port,
      database_name: profile.database_name,
      username: profile.username,
      sslmode: profile.sslmode,
      sslrootcert: profile.sslrootcert,
      connect_timeout: profile.connect_timeout,
      is_enabled: profile.is_enabled,
    }
    if (profile.password) {
      profiles[role].password = profile.password
    }
  })
  const mediaQuality = {}
  MEDIA_METRICS.forEach(({ key }) => {
    const config = value.media_quality[key]
    mediaQuality[key] = {
      warning: toNumberOrNull(config.warning),
      critical: toNumberOrNull(config.critical),
      unit: config.unit || '',
    }
  })
  return {
    active_source: value.active_source,
    profiles,
    ...Object.fromEntries(LIMIT_FIELDS.map(({ key }) => [key, value[key]])),
    user_defined_fields: value.user_defined_fields,
    media_quality: mediaQuality,
    field_help_overrides: Object.fromEntries(
      value.help_overrides
        .filter((override) => override.key && override.text)
        .map((override) => [override.key, override.text]),
    ),
  }
}

function applySettings(data) {
  settings.value = data
  form.value = formFromSettings(data)
  initialSnapshot.value = snapshot(form.value)
  saveErrors.value = null
}

async function loadSettings() {
  loading.value = true
  loadError.value = null
  try {
    applySettings(await fetchModuleSettings())
  } catch (error) {
    loadError.value = describeCdrError(error, 'Unable to load CDR settings.')
  } finally {
    loading.value = false
  }
}

function errorAt(path) {
  let node = saveErrors.value
  for (const key of path) {
    if (!node || typeof node !== 'object' || Array.isArray(node)) {
      return undefined
    }
    node = node[key]
  }
  if (Array.isArray(node)) {
    return node.filter((item) => typeof item === 'string').join(' ') || undefined
  }
  return typeof node === 'string' ? node : undefined
}

const requiredRule = (value) =>
  (value !== null && value !== undefined && String(value).trim() !== '') || 'Required.'
const intRange = (min, max) => (value) =>
  (Number.isInteger(Number(value)) && Number(value) >= min && Number(value) <= max) ||
  `Enter a whole number from ${min} to ${max}.`
const hostRule = (value) =>
  HOST_PATTERN.test(value || '') || 'Enter a valid host name or IP address.'
const identifierRule = (value) =>
  IDENTIFIER_PATTERN.test(value || '') || 'Must not contain spaces or control characters.'
const sslRootCertRule = (value) =>
  !value ||
  value === 'system' ||
  value.startsWith('/') ||
  'Use an absolute path, "system", or leave blank.'
const optionalNonNegative = (value) =>
  value === '' || value === null || Number(value) >= 0 || 'Must be zero or greater.'

function passwordRule(role, value) {
  const profile = form.value.profiles[role]
  return Boolean(value) || profile.has_password || 'A password is required for a new profile.'
}

function criticalRule(metric, value) {
  const warning = toNumberOrNull(form.value.media_quality[metric].warning)
  const critical = toNumberOrNull(value)
  return (
    warning === null ||
    critical === null ||
    critical >= warning ||
    'Critical must be greater than or equal to warning.'
  )
}

function unitRule(metric, value) {
  const config = form.value.media_quality[metric]
  const hasThreshold =
    toNumberOrNull(config.warning) !== null || toNumberOrNull(config.critical) !== null
  return (
    !hasThreshold || Boolean((value || '').trim()) || 'A unit is required when a threshold is set.'
  )
}

function helpKeyRule(value, index) {
  if (!HELP_KEY_PATTERN.test(value || '')) {
    return 'Use sdr.<field>, cdr.<field>, topic.<topic> or termination.<value>.'
  }
  if (!value.startsWith('termination.') && !allHelpKeys.value.includes(value)) {
    return 'Unknown help key.'
  }
  const duplicate = form.value.help_overrides.some(
    (override, position) => position !== index && override.key === value,
  )
  return !duplicate || 'This key already has an override.'
}

function defaultHelpFor(key) {
  if (!key) {
    return undefined
  }
  const [prefix, ...rest] = key.split('.')
  const name = rest.join('.')
  const section = { sdr: 'sdr', cdr: 'cdr', topic: 'topics' }[prefix]
  const text = section ? display.help[section]?.[name] : null
  return text ? `Current: ${text}` : undefined
}

function filterHelpKeys(value, done) {
  done(() => {
    helpKeyFilter.value = value || ''
  })
}

function addOverride() {
  form.value.help_overrides.push({ id: ++overrideSeq, key: '', text: '' })
}

function discard() {
  form.value = formFromSettings(settings.value)
  saveErrors.value = null
  formRef.value?.resetValidation()
}

function confirm(message) {
  return new Promise((resolve) => {
    $q.dialog({ title: 'Confirm settings change', message, cancel: true, persistent: true })
      .onOk(() => resolve(true))
      .onCancel(() => resolve(false))
      .onDismiss(() => resolve(false))
  })
}

async function save() {
  const removed = ROLES.filter(
    (role) => settings.value.profiles?.[role] && !form.value.profiles[role].configured,
  )
  if (removed.length) {
    const names = removed.map((role) => SOURCE_LABELS[role]).join(' and ')
    if (!(await confirm(`Remove the ${names} connection profile and its stored credential?`))) {
      return
    }
  }

  saving.value = true
  saveErrors.value = null
  try {
    applySettings(await updateModuleSettings(buildPayload(form.value)))
    $q.notify({ type: 'positive', message: 'CDR settings saved.' })
    lookups.reset()
    stats.$reset()
    await display.load({ force: true })
  } catch (error) {
    const info = describeCdrError(error, 'Unable to save CDR settings.')
    saveErrors.value = info.fieldErrors
    $q.notify({ type: 'negative', message: info.message })
  } finally {
    saving.value = false
  }
}

onBeforeRouteLeave(() => (dirty.value ? confirm('Discard unsaved CDR settings changes?') : true))

onMounted(() => {
  display.load()
  lookups.loadOne('terminationReasons')
  loadSettings()
})
</script>
