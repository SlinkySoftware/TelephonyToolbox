<!--
SPDX-FileCopyrightText: Copyright 2026, Slinky Software
SPDX-License-Identifier: GPL-3.0-only
-->

<template>
  <div v-if="raw !== null && raw !== undefined" class="cdr-tags">
    <table v-if="entries.length" class="cdr-tags__table">
      <caption class="cdr-sr-only">
        {{
          `${label} parsed as key and value pairs`
        }}
      </caption>
      <thead>
        <tr>
          <th scope="col">Key</th>
          <th scope="col">Value</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="(entry, index) in entries" :key="index">
          <td class="cdr-mono">
            <span v-if="entry.malformed" class="cdr-tags__malformed">
              <q-icon name="report" size="1em" aria-hidden="true" />
              no key
            </span>
            <template v-else>{{ entry.key }}</template>
          </td>
          <td class="cdr-mono">{{ entry.value }}</td>
        </tr>
      </tbody>
    </table>
    <div class="cdr-tags__original">
      <span class="muted-copy text-caption">Original</span>
      <CdrCopyValue :value="raw" :label="label" />
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

import CdrCopyValue from 'src/components/cdr/CdrCopyValue.vue'

const props = defineProps({
  raw: { type: String, default: null },
  parsed: { type: Array, default: null },
  label: { type: String, default: 'tags' },
})

const entries = computed(() => props.parsed || [])
</script>
