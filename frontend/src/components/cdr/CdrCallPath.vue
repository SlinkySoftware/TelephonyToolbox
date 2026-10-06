<!--
SPDX-FileCopyrightText: Copyright 2026, Slinky Software
SPDX-License-Identifier: GPL-3.0-only
-->

<template>
  <ol class="cdr-call-path" aria-label="Call path">
    <li class="cdr-path-node">
      <div class="cdr-path-node__kicker">Source</div>
      <div class="cdr-path-node__row">
        <span class="cdr-path-node__label">Source IP</span>
        <CdrCopyValue :value="raw.sourceip" label="Source IP" />
      </div>
    </li>

    <li class="cdr-path-arrow" aria-hidden="true"><q-icon name="arrow_forward" /></li>

    <li class="cdr-path-node">
      <div class="cdr-path-node__kicker">Ingress</div>
      <div class="cdr-path-node__row">
        <span class="cdr-path-node__label">IP group</span>
        <span>{{ raw.ingressipgroup ?? '' }}</span>
      </div>
      <div class="cdr-path-node__row">
        <span class="cdr-path-node__label">ANI</span>
        <CdrCopyValue :value="raw.ingressani" label="Ingress ANI" />
      </div>
      <div class="cdr-path-node__row">
        <span class="cdr-path-node__label">DNIS</span>
        <CdrCopyValue :value="raw.ingressdnis" label="Ingress DNIS" />
      </div>
    </li>

    <li class="cdr-path-arrow" aria-hidden="true"><q-icon name="arrow_forward" /></li>

    <li class="cdr-path-node cdr-path-node--sbc">
      <div class="cdr-path-node__kicker">AudioCodes SBC session</div>
      <div
        v-for="item in manipulation"
        :key="item.key"
        class="cdr-path-change"
        :class="item.className"
      >
        <q-icon :name="item.icon" size="1em" aria-hidden="true" />
        <span>{{ item.text }}</span>
      </div>
    </li>

    <li class="cdr-path-arrow" aria-hidden="true"><q-icon name="arrow_forward" /></li>

    <li class="cdr-path-node">
      <div class="cdr-path-node__kicker">Egress</div>
      <div class="cdr-path-node__row">
        <span class="cdr-path-node__label">IP group</span>
        <span>{{ raw.egressipgroup ?? '' }}</span>
      </div>
      <div class="cdr-path-node__row" :class="{ 'cdr-path-node__row--changed': changed('ani') }">
        <span class="cdr-path-node__label">ANI</span>
        <CdrCopyValue :value="raw.egressani" label="Egress ANI" />
      </div>
      <div class="cdr-path-node__row" :class="{ 'cdr-path-node__row--changed': changed('dnis') }">
        <span class="cdr-path-node__label">DNIS</span>
        <CdrCopyValue :value="raw.egressdnis" label="Egress DNIS" />
      </div>
    </li>

    <li class="cdr-path-arrow" aria-hidden="true"><q-icon name="arrow_forward" /></li>

    <li class="cdr-path-node">
      <div class="cdr-path-node__kicker">Destination</div>
      <div class="cdr-path-node__row">
        <span class="cdr-path-node__label">Destination IP</span>
        <CdrCopyValue :value="raw.destinationip" label="Destination IP" />
      </div>
    </li>
  </ol>
</template>

<script setup>
import { computed } from 'vue'

import CdrCopyValue from 'src/components/cdr/CdrCopyValue.vue'

const props = defineProps({
  raw: { type: Object, required: true },
  // { ani, dnis }: 'changed' | 'unchanged' | 'unknown' (unknown when either side is blank)
  changes: { type: Object, default: () => ({}) },
})

const NAMES = { ani: 'ANI', dnis: 'DNIS' }

function changed(key) {
  return props.changes?.[key] === 'changed'
}

const manipulation = computed(() =>
  ['ani', 'dnis']
    .filter((key) => ['changed', 'unchanged'].includes(props.changes?.[key]))
    .map((key) =>
      changed(key)
        ? {
            key,
            icon: 'swap_horiz',
            text: `${NAMES[key]} differs between ingress and egress`,
            className: 'cdr-path-change--changed',
          }
        : {
            key,
            icon: 'drag_handle',
            text: `${NAMES[key]} identical on ingress and egress`,
            className: '',
          },
    ),
)
</script>
