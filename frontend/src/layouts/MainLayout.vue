<template>
  <q-layout view="hHh Lpr lFf" class="app-shell">
    <q-header class="app-header">
      <q-toolbar class="toolbar-pad">
        <q-btn flat round dense icon="menu" class="lt-md text-sand" @click="toggleLeftDrawer" />

        <div class="brand-lockup">
          <div class="brand-kicker">Telephony Operations</div>
          <div class="brand-title">Telephony Toolbox</div>
        </div>

        <q-space />

        <div class="toolbar-meta gt-sm">
          <div class="toolbar-role">{{ roleLabel }}</div>
          <div class="toolbar-user">{{ session.user?.display_name }}</div>
        </div>

        <q-btn flat no-caps class="logout-btn" label="Logout" @click="handleLogout" />
      </q-toolbar>
    </q-header>

    <q-drawer v-model="leftDrawerOpen" show-if-above bordered class="app-drawer">
      <div class="drawer-top">
        <div class="drawer-kicker">Control Surface</div>
        <div class="drawer-title">Navigation</div>
      </div>

      <q-list class="drawer-list">
        <q-item v-for="item in primaryLinks" :key="item.to" clickable :to="item.to" exact class="nav-item">
          <q-item-section avatar>
            <q-icon :name="item.icon" />
          </q-item-section>
          <q-item-section>
            <q-item-label>{{ item.label }}</q-item-label>
            <q-item-label caption>{{ item.caption }}</q-item-label>
          </q-item-section>
        </q-item>
      </q-list>

      <q-separator dark class="q-my-md" />

      <q-list v-if="adminLinks.length" class="drawer-list">
        <q-item-label header class="drawer-section">Admin</q-item-label>
        <q-item v-for="item in adminLinks" :key="item.to" clickable :to="item.to" exact class="nav-item">
          <q-item-section avatar>
            <q-icon :name="item.icon" />
          </q-item-section>
          <q-item-section>
            <q-item-label>{{ item.label }}</q-item-label>
            <q-item-label caption>{{ item.caption }}</q-item-label>
          </q-item-section>
        </q-item>
      </q-list>
    </q-drawer>

    <q-page-container class="page-stage">
      <router-view />
    </q-page-container>
  </q-layout>
</template>

<script setup>
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useSessionStore } from 'src/stores/session'

const router = useRouter()
const session = useSessionStore()
const leftDrawerOpen = ref(false)

const primaryLinks = computed(() => [
  {
    to: '/diversions',
    label: 'My Diversions',
    caption: 'Refresh and update assigned call forwards',
    icon: 'call_split',
  },
])

const adminLinks = computed(() => {
  if (session.user?.role !== 'app_admin') {
    return []
  }

  return [
    { to: '/admin', label: 'Dashboard', caption: 'Operational summary', icon: 'space_dashboard' },
    { to: '/admin/users', label: 'Users', caption: 'Provision and retire operators', icon: 'badge' },
    { to: '/admin/groups', label: 'Groups', caption: 'Manage local access boundaries', icon: 'groups_2' },
    { to: '/admin/diversions', label: 'Diversions', caption: 'Create and assign source numbers', icon: 'phone_forwarded' },
    { to: '/admin/audit', label: 'Audit Log', caption: 'Export operational history', icon: 'history_edu' },
    { to: '/admin/health', label: 'System Health', caption: 'Inspect database, auth and CUCM status', icon: 'monitor_heart' },
  ]
})

const roleLabel = computed(() => (session.user?.role === 'app_admin' ? 'App Admin' : 'Standard User'))

function toggleLeftDrawer() {
  leftDrawerOpen.value = !leftDrawerOpen.value
}

async function handleLogout() {
  await session.logout()
  await router.replace('/login')
}
</script>
