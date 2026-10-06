<!--
SPDX-FileCopyrightText: Copyright 2026, Slinky Software
SPDX-License-Identifier: GPL-3.0-only
-->

<template>
  <dl class="cdr-field-grid" :class="{ 'cdr-field-grid--wide': wide }">
    <div
      v-for="item in items"
      :key="item.key"
      class="cdr-field"
      :class="{ 'cdr-field--full': item.type === 'tags' }"
    >
      <dt class="cdr-field__label">
        <span>{{ item.label }}</span>
        <CdrHelp :text="item.help" :label="item.label" :source="helpSource" />
        <span class="cdr-field__source">{{ item.sourceName }}</span>
      </dt>
      <dd class="cdr-field__value">
        <CdrTimestamp
          v-if="item.type === 'timestamp'"
          :value="item.value"
          :source="item.timestampSource"
        />
        <CdrDuration v-else-if="item.type === 'duration'" :value="item.value" show-raw />
        <template v-else-if="item.type === 'status'">
          <CdrStatusBadge v-if="item.value !== null" :value="item.value" />
          <CdrStatusBadge v-else outcome="unknown" label="Unknown (blank)" />
        </template>
        <CdrMediaMetric
          v-else-if="item.type === 'media'"
          :value="item.value"
          :config="item.mediaConfig"
        />
        <CdrTagTable
          v-else-if="item.type === 'tags'"
          :raw="item.value"
          :parsed="item.parsedTags"
          :label="item.label"
        />
        <CdrCopyValue v-else-if="item.copy" :value="item.value" :label="item.label" />
        <span v-else :class="{ 'cdr-mono': item.mono }">{{ displayValue(item.value) }}</span>
        <div v-if="item.note" class="cdr-field__note">
          <q-icon name="info" size="1em" aria-hidden="true" />
          <span>{{ item.note }}</span>
        </div>
      </dd>
    </div>
  </dl>
</template>

<script setup>
import CdrCopyValue from 'src/components/cdr/CdrCopyValue.vue'
import CdrDuration from 'src/components/cdr/CdrDuration.vue'
import CdrHelp from 'src/components/cdr/CdrHelp.vue'
import CdrMediaMetric from 'src/components/cdr/CdrMediaMetric.vue'
import CdrStatusBadge from 'src/components/cdr/CdrStatusBadge.vue'
import CdrTagTable from 'src/components/cdr/CdrTagTable.vue'
import CdrTimestamp from 'src/components/cdr/CdrTimestamp.vue'
import { displayValue } from 'src/utils/cdrFormat'

defineProps({
  items: { type: Array, required: true },
  wide: { type: Boolean, default: false },
  helpSource: { type: String, default: '' },
})
</script>
