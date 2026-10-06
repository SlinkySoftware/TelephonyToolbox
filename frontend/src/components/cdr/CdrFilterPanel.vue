<!--
SPDX-FileCopyrightText: Copyright 2026, Slinky Software
SPDX-License-Identifier: GPL-3.0-only
-->

<template>
  <q-form ref="form" class="cdr-filter-panel" greedy @submit="emit('submit')">
    <div v-if="showRange" class="row q-col-gutter-md">
      <div class="col-12 col-sm-6 col-lg-3">
        <q-input
          :model-value="startText"
          filled
          dense
          label="Setup time from"
          mask="####-##-## ##:##:##"
          placeholder="YYYY-MM-DD HH:mm:ss"
          :hint="zoneHint(modelValue.start, startText)"
          :rules="startRules"
          :error="Boolean(serverError('start'))"
          :error-message="serverError('start')"
          lazy-rules
          @update:model-value="(value) => onRangeText('start', value)"
        >
          <template #append>
            <q-icon name="event" class="cursor-pointer" aria-label="Choose start date and time">
              <q-popup-proxy cover transition-show="scale" transition-hide="scale">
                <div class="row no-wrap">
                  <q-date
                    :model-value="startText"
                    mask="YYYY-MM-DD HH:mm:ss"
                    minimal
                    @update:model-value="(value) => onRangeText('start', value)"
                  />
                  <q-time
                    :model-value="startText"
                    mask="YYYY-MM-DD HH:mm:ss"
                    format24h
                    with-seconds
                    @update:model-value="(value) => onRangeText('start', value)"
                  />
                </div>
                <div class="row justify-end q-pa-sm">
                  <q-btn v-close-popup flat no-caps color="primary" label="Done" />
                </div>
              </q-popup-proxy>
            </q-icon>
          </template>
        </q-input>
      </div>
      <div class="col-12 col-sm-6 col-lg-3">
        <q-input
          ref="endInput"
          :model-value="endText"
          filled
          dense
          label="Setup time to (exclusive)"
          mask="####-##-## ##:##:##"
          placeholder="YYYY-MM-DD HH:mm:ss"
          :hint="zoneHint(modelValue.end, endText)"
          :rules="endRules"
          :error="Boolean(serverError('end'))"
          :error-message="serverError('end')"
          lazy-rules
          @update:model-value="(value) => onRangeText('end', value)"
        >
          <template #append>
            <q-icon name="event" class="cursor-pointer" aria-label="Choose end date and time">
              <q-popup-proxy cover transition-show="scale" transition-hide="scale">
                <div class="row no-wrap">
                  <q-date
                    :model-value="endText"
                    mask="YYYY-MM-DD HH:mm:ss"
                    minimal
                    @update:model-value="(value) => onRangeText('end', value)"
                  />
                  <q-time
                    :model-value="endText"
                    mask="YYYY-MM-DD HH:mm:ss"
                    format24h
                    with-seconds
                    @update:model-value="(value) => onRangeText('end', value)"
                  />
                </div>
                <div class="row justify-end q-pa-sm">
                  <q-btn v-close-popup flat no-caps color="primary" label="Done" />
                </div>
              </q-popup-proxy>
            </q-icon>
          </template>
        </q-input>
      </div>
      <div class="col-12 col-lg-6 cdr-range-note muted-copy">
        Times are Australia/Sydney. The range is searched on SDR setup time and cannot exceed 12
        months.
      </div>
    </div>

    <div class="row q-col-gutter-md">
      <div v-for="lookup in lookupFields" :key="lookup.key" class="col-12 col-md-4">
        <q-select
          :model-value="modelValue[lookup.key]"
          filled
          dense
          multiple
          use-chips
          use-input
          input-debounce="0"
          :label="lookup.label"
          :options="filteredOptions[lookup.store] || []"
          :loading="lookups[lookup.store].loading"
          :max-values="maxValues"
          :new-value-mode="allowManual(lookup.store) ? 'add-unique' : undefined"
          :hint="lookupHint(lookup.store)"
          :rules="[multiRule]"
          :error="Boolean(serverError(lookup.key))"
          :error-message="serverError(lookup.key)"
          @filter="(value, done) => filterOptions(lookup.store, value, done)"
          @update:model-value="(value) => update(lookup.key, value || [])"
        >
          <template #no-option>
            <q-item>
              <q-item-section class="text-grey-7">
                {{ noOptionText(lookup.store) }}
              </q-item-section>
            </q-item>
          </template>
        </q-select>
      </div>
    </div>

    <div class="row q-col-gutter-md">
      <div v-for="field in textFields" :key="field.key" class="col-12 col-sm-6 col-lg-3">
        <div class="cdr-text-filter">
          <q-input
            :model-value="modelValue[field.key]"
            filled
            dense
            clearable
            class="cdr-text-filter__value"
            :label="field.label"
            :maxlength="MAX_TEXT_LENGTH"
            :hint="textHint(field)"
            :rules="[maxLengthRule]"
            :error="Boolean(serverError(field.key))"
            :error-message="serverError(field.key)"
            @update:model-value="(value) => update(field.key, value ?? '')"
          />
          <q-select
            :model-value="modelValue[field.matchKey]"
            filled
            dense
            emit-value
            map-options
            options-dense
            class="cdr-text-filter__mode"
            :options="MATCH_MODE_OPTIONS"
            :aria-label="`${field.label} match mode`"
            :error="Boolean(serverError(field.matchKey))"
            :error-message="serverError(field.matchKey)"
            @update:model-value="(value) => update(field.matchKey, value)"
          />
        </div>
      </div>
    </div>

    <div class="row q-col-gutter-md items-start">
      <div class="col-12 col-sm-6 col-lg-3">
        <q-select
          :model-value="modelValue.status"
          filled
          dense
          emit-value
          map-options
          label="Status"
          :options="STATUS_OPTIONS"
          :error="Boolean(serverError('status'))"
          :error-message="serverError('status')"
          @update:model-value="(value) => update('status', value)"
        />
      </div>
      <div class="col-12 col-sm-6 col-lg-9 cdr-filter-actions">
        <q-btn
          type="submit"
          color="primary"
          text-color="white"
          no-caps
          :icon="submitIcon"
          :label="submitLabel"
        />
        <q-btn
          outline
          color="primary"
          no-caps
          icon="filter_alt_off"
          label="Clear filters"
          @click="emit('clear')"
        />
        <q-btn
          v-if="showReset"
          flat
          color="primary"
          no-caps
          icon="today"
          label="Reset to today"
          @click="emit('reset')"
        />
        <slot name="actions" />
      </div>
    </div>
  </q-form>
</template>

<script setup>
import { computed, nextTick, reactive, ref, watch } from 'vue'

import { useCdrDisplayStore } from 'src/stores/cdrDisplay'
import { useCdrLookupsStore } from 'src/stores/cdrLookups'
import {
  MATCH_MODE_OPTIONS,
  MAX_TEXT_LENGTH,
  SLOW_MATCH_MODES,
  STATUS_OPTIONS,
} from 'src/utils/cdrQuery'
import {
  formatLocalInput,
  parseInstant,
  parseLocalInput,
  rangeExceedsLimit,
  sydneyZoneName,
  toSydneyIso,
} from 'src/utils/cdrTime'

const props = defineProps({
  modelValue: { type: Object, required: true },
  showRange: { type: Boolean, default: true },
  showReset: { type: Boolean, default: false },
  serverErrors: { type: Object, default: null },
  submitLabel: { type: String, default: 'Search' },
  submitIcon: { type: String, default: 'search' },
})

const emit = defineEmits(['update:modelValue', 'submit', 'clear', 'reset'])

const display = useCdrDisplayStore()
const lookups = useCdrLookupsStore()

const form = ref(null)
const endInput = ref(null)
const startText = ref(formatLocalInput(props.modelValue.start))
const endText = ref(formatLocalInput(props.modelValue.end))
const filteredOptions = reactive({})

const lookupFields = [
  { key: 'ingress_ip_group', store: 'ingress', label: 'Ingress IP group' },
  { key: 'egress_ip_group', store: 'egress', label: 'Egress IP group' },
  { key: 'termination_reason', store: 'terminationReasons', label: 'Termination reason (exact)' },
]
const textFields = [
  { key: 'ani', matchKey: 'ani_match', label: 'ANI (ingress or egress)' },
  { key: 'dnis', matchKey: 'dnis_match', label: 'DNIS (ingress or egress)' },
  { key: 'call_id', matchKey: 'call_id_match', label: 'Call-ID (ingress or egress)' },
  { key: 'termination_text', matchKey: 'termination_match', label: 'Termination reason text' },
]

const maxValues = computed(() => display.maxMultiselect)

watch(
  () => props.modelValue.start,
  (value) => syncText(startText, value),
)
watch(
  () => props.modelValue.end,
  (value) => syncText(endText, value),
)

function syncText(textRef, value) {
  const text = formatLocalInput(value)
  if (text && text !== textRef.value) {
    textRef.value = text
  }
}

function update(key, value) {
  emit('update:modelValue', { ...props.modelValue, [key]: value })
}

function onRangeText(which, value) {
  const text = value || ''
  if (which === 'start') {
    startText.value = text
  } else {
    endText.value = text
  }
  const { date, error } = parseLocalInput(text)
  // Keep the exact instant (and its offset) when the wall-clock text is unchanged.
  if (!error && formatLocalInput(props.modelValue[which]) !== text.trim()) {
    update(which, toSydneyIso(date))
  }
  if (which === 'start' && endText.value) {
    nextTick(() => endInput.value?.validate())
  }
}

function serverError(key) {
  const messages = props.serverErrors?.[key]
  if (Array.isArray(messages)) {
    return messages.join(' ')
  }
  return typeof messages === 'string' ? messages : undefined
}

function zoneHint(iso, text) {
  if (parseLocalInput(text).error) {
    return 'Australia/Sydney'
  }
  const zone = sydneyZoneName(iso)
  return zone ? `Australia/Sydney (${zone})` : 'Australia/Sydney'
}

const required = (value) => Boolean(value && value.trim()) || 'Required.'
const validFormat = (value) =>
  parseLocalInput(value).error !== 'format' || 'Enter a valid date and time (YYYY-MM-DD HH:mm:ss).'
const existingTime = (value) =>
  parseLocalInput(value).error !== 'nonexistent' ||
  'This time does not exist in Australia/Sydney (daylight-saving change).'

function rangeDates(endText) {
  return { start: instantFor('start', startText.value), end: instantFor('end', endText) }
}

// Rules receive the field text before the parent model updates, so resolve instants from text.
function instantFor(which, text) {
  const model = props.modelValue[which]
  if (formatLocalInput(model) === (text || '').trim()) {
    return parseInstant(model)
  }
  return parseLocalInput(text).date
}

const endAfterStart = (value) => {
  const { start, end } = rangeDates(value)
  return !start || !end || end > start || 'The end time must be after the start time.'
}
const withinLimit = (value) => {
  const { start, end } = rangeDates(value)
  return !start || !end || !rangeExceedsLimit(start, end) || 'The range cannot exceed 12 months.'
}

const startRules = [required, validFormat, existingTime]
const endRules = [required, validFormat, existingTime, endAfterStart, withinLimit]

const multiRule = (value) =>
  !value || value.length <= maxValues.value || `Select no more than ${maxValues.value} values.`
const maxLengthRule = (value) =>
  !value || value.length <= MAX_TEXT_LENGTH || `Use no more than ${MAX_TEXT_LENGTH} characters.`

function filterOptions(name, needle, done) {
  done(() => {
    const term = (needle || '').toLowerCase()
    const values = lookups[name].values
    filteredOptions[name] = term
      ? values.filter((value) => value.toLowerCase().includes(term))
      : values
  })
}

function allowManual(name) {
  return Boolean(lookups[name].error) && !lookups[name].values.length
}

function lookupHint(name) {
  const lookup = lookups[name]
  if (lookup.error && !lookup.values.length) {
    return `Values unavailable (${lookup.error.message}) Type exact values and press Enter.`
  }
  if (lookup.stale) {
    return 'Showing previously cached values; the latest refresh failed.'
  }
  if (name === 'terminationReasons' && lookups.windowDays) {
    return `Values seen in the last ${lookups.windowDays} days; matches any termination field.`
  }
  return undefined
}

function noOptionText(name) {
  const lookup = lookups[name]
  if (lookup.loading) {
    return 'Loading values…'
  }
  if (lookup.error && !lookup.values.length) {
    return 'Values are unavailable.'
  }
  return 'No matching values.'
}

function textHint(field) {
  if (props.modelValue[field.key] && SLOW_MATCH_MODES.has(props.modelValue[field.matchKey])) {
    return 'Contains and ends-with matching can be slow on long ranges.'
  }
  return undefined
}

defineExpose({
  validate: () => form.value?.validate(),
  resetValidation: () => form.value?.resetValidation(),
})
</script>
