<!--
SPDX-FileCopyrightText: Copyright 2026, Slinky Software
SPDX-License-Identifier: GPL-3.0-only
-->

<template>
  <q-page class="page-frame soft-grid">
    <section class="page-hero">
      <div class="section-kicker">App Admin</div>
      <h1 class="page-title">Operations Dashboard</h1>
      <p class="page-subtitle">A compact pulse on access, inventory and backend health before you start making changes.</p>
    </section>

    <div class="metric-grid">
      <div class="card-panel metric-card">
        <div class="muted-copy">Users</div>
        <div class="metric-value">{{ metrics.users }}</div>
      </div>
      <div class="card-panel metric-card">
        <div class="muted-copy">Groups</div>
        <div class="metric-value">{{ metrics.groups }}</div>
      </div>
      <div class="card-panel metric-card">
        <div class="muted-copy">Diversions</div>
        <div class="metric-value">{{ metrics.diversions }}</div>
      </div>
      <div class="card-panel metric-card">
        <div class="muted-copy">CUCM</div>
        <div class="metric-value">{{ metrics.cucm }}</div>
      </div>
    </div>
  </q-page>
</template>

<script setup>
import { onMounted, reactive } from 'vue'
import { useQuasar } from 'quasar'

import { getAdminHealth, listAdminDiversions, listGroups, listUsers } from 'src/services/toolboxApi'
import { extractApiMessage } from 'src/utils/format'

const $q = useQuasar()
const metrics = reactive({ users: '…', groups: '…', diversions: '…', cucm: '…' })

onMounted(async () => {
  try {
    const [users, groups, diversions, health] = await Promise.all([
      listUsers(),
      listGroups(),
      listAdminDiversions(),
      getAdminHealth(),
    ])
    metrics.users = users.length
    metrics.groups = groups.length
    metrics.diversions = diversions.length
    metrics.cucm = health.cucm.status
  } catch (error) {
    $q.notify({ type: 'negative', message: extractApiMessage(error, 'Unable to load dashboard metrics.') })
  }
})
</script>