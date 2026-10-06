<!--
SPDX-FileCopyrightText: Copyright 2026, Slinky Software
SPDX-License-Identifier: GPL-3.0-only
-->

<template>
  <q-expansion-item
    :model-value="modelValue"
    class="cdr-leg-card"
    :class="{ 'cdr-leg-card--failed': cdr.raw.callsuccess === false }"
    header-class="cdr-leg-card__header"
    @update:model-value="(value) => emit('update:modelValue', value)"
  >
    <template #header>
      <div class="cdr-leg-head">
        <div class="cdr-leg-head__primary">
          <span class="cdr-leg-head__leg">{{ legLabel }}</span>
          <span class="cdr-direction" :class="`cdr-direction--${direction}`">
            <q-icon :name="DIRECTION_ICONS[direction]" size="1.05em" aria-hidden="true" />
            <span>{{ cdr.display.direction_label }}</span>
          </span>
          <span class="cdr-raw cdr-mono">callorig: {{ cdr.raw.callorig ?? '' }}</span>
          <span v-if="anomalies.length" class="cdr-leg-head__anomaly">
            <q-icon name="warning" size="1em" aria-hidden="true" />
            <span>{{ anomalies.length }} anomal{{ anomalies.length === 1 ? 'y' : 'ies' }}</span>
            <q-tooltip>{{ anomalies.map((item) => item.message).join(' ') }}</q-tooltip>
          </span>
        </div>
        <div class="cdr-leg-head__grid">
          <div>
            <div class="cdr-leg-head__label">IP group</div>
            <div>{{ cdr.raw.ipgroupname ?? '' }}</div>
          </div>
          <div>
            <div class="cdr-leg-head__label">Source</div>
            <div class="cdr-mono">{{ cdr.raw.sourceusername ?? '' }}</div>
          </div>
          <div>
            <div class="cdr-leg-head__label">Destination</div>
            <div class="cdr-mono">{{ cdr.raw.destinationusername ?? '' }}</div>
          </div>
          <div>
            <div class="cdr-leg-head__label">Status</div>
            <CdrStatusBadge :outcome="cdr.display.outcome" />
          </div>
          <div>
            <div class="cdr-leg-head__label">Termination</div>
            <div>{{ cdr.raw.terminationreason ?? '' }}</div>
          </div>
          <div>
            <div class="cdr-leg-head__label">Duration</div>
            <CdrDuration :value="cdr.raw.callduration" />
          </div>
        </div>
      </div>
    </template>

    <div class="cdr-leg-body">
      <section v-for="group in groups" :key="group.key" class="cdr-leg-group">
        <h4 class="cdr-leg-group__title">
          <span>{{ group.label }}</span>
          <CdrHelp
            v-if="group.topicHelp"
            :text="group.topicHelp"
            :label="group.label"
            :source="display.help.version"
          />
        </h4>
        <CdrFieldGrid :items="group.items" :help-source="display.help.version" />
      </section>
    </div>
  </q-expansion-item>
</template>

<script setup>
import { computed } from 'vue'

import CdrDuration from 'src/components/cdr/CdrDuration.vue'
import CdrFieldGrid from 'src/components/cdr/CdrFieldGrid.vue'
import CdrHelp from 'src/components/cdr/CdrHelp.vue'
import CdrStatusBadge from 'src/components/cdr/CdrStatusBadge.vue'
import { useCdrDisplayStore } from 'src/stores/cdrDisplay'
import { CDR_GROUPS, buildFieldItems } from 'src/utils/cdrFields'

const props = defineProps({
  cdr: { type: Object, required: true },
  anomalies: { type: Array, default: () => [] },
  modelValue: { type: Boolean, default: false },
})

const emit = defineEmits(['update:modelValue'])

const display = useCdrDisplayStore()

const DIRECTION_ICONS = { inbound: 'call_received', outbound: 'call_made', unknown: 'help_outline' }
const GROUP_TOPICS = { routing: 'direction' }

const direction = computed(() => props.cdr.display?.direction || 'unknown')
const legLabel = computed(() =>
  props.cdr.raw.legid === null || props.cdr.raw.legid === undefined
    ? 'Leg ID blank'
    : `Leg ${props.cdr.raw.legid}`,
)

const groups = computed(() => {
  const context = {
    help: display.help,
    userDefinedFields: display.userDefinedFields,
    mediaByField: display.mediaByField,
    parsedTags: props.cdr.parsed_tags || {},
  }
  return CDR_GROUPS.map((group) => ({
    ...group,
    topicHelp: display.help.topics?.[group.topic || GROUP_TOPICS[group.key]] || '',
    items: buildFieldItems('cdr', group.fields, props.cdr.raw, context),
  }))
})
</script>
