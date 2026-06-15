<!--
SPDX-FileCopyrightText: Copyright 2026, Slinky Software
SPDX-License-Identifier: GPL-3.0-only
-->

<template>
  <div class="login-page-shell row items-center justify-center q-pa-md">
    <div class="login-grid">
      <section class="page-hero hero-side">
        <div class="section-kicker">Operational Console</div>
        <h1 class="page-title">Forwarding changes without roulette.</h1>
        <p class="page-subtitle">
          Telephony Toolbox keeps diversion control narrow, auditable and anchored to live CUCM state.
        </p>

        <div class="soft-grid hero-notes q-mt-xl">
          <div class="status-panel q-pa-lg">
            <div class="text-overline text-orange-3">Source of truth</div>
            <div class="text-h6 q-mt-sm">Cisco UCM decides the real forwarding state.</div>
            <div class="muted-copy q-mt-sm">The app validates, writes, reads back, and only reports clean success on a verified match.</div>
          </div>
          <div class="status-panel q-pa-lg">
            <div class="text-overline text-orange-3">Fallback ready</div>
            <div class="text-h6 q-mt-sm">Local break-glass access remains available.</div>
            <div class="muted-copy q-mt-sm">External auth can fail without locking out App Admin recovery paths.</div>
          </div>
        </div>
      </section>

      <section class="form-panel q-pa-xl">
        <div class="section-kicker">Sign In</div>
        <div class="text-h5 q-mt-sm">Access the control surface</div>
        <p class="muted-copy q-mt-sm">
          The available sign-in options come from the current deployment configuration.
        </p>

        <q-banner v-if="errorMessage" class="warning-banner q-mb-md text-white">
          {{ errorMessage }}
        </q-banner>

        <q-inner-loading :showing="loadingAuthOptions">
          <q-spinner-rings size="36px" color="orange-4" />
        </q-inner-loading>

        <div v-if="session.authOptions?.auth_mode === 'entra'" class="q-mb-lg">
          <q-btn
            unelevated
            color="orange-6"
            text-color="black"
            class="full-width"
            label="Continue with Entra"
            @click="session.beginEntraLogin()"
          />
        </div>

        <q-form v-if="session.authOptions?.auth_mode === 'ldap'" class="q-gutter-md q-mb-lg" @submit.prevent="submitLdap">
          <q-input v-model="ldapForm.email" filled label="Email address" type="email" autocomplete="username" />
          <q-input v-model="ldapForm.password" filled label="Password" type="password" autocomplete="current-password" />
          <q-btn unelevated color="orange-6" text-color="black" class="full-width" label="Sign in with LDAP" type="submit" :loading="submittingLdap" />
        </q-form>

        <div v-if="session.authOptions?.local_auth_enabled" class="q-pt-sm">
          <div class="text-subtitle2 text-orange-2 q-mb-sm">Local fallback sign-in</div>
          <q-form class="q-gutter-md" @submit.prevent="submitLocal">
            <q-input v-model="localForm.email" filled label="Email address" type="email" autocomplete="username" />
            <q-input v-model="localForm.password" filled label="Password" type="password" autocomplete="current-password" />
            <q-btn outline color="orange-3" class="full-width" label="Use local account" type="submit" :loading="submittingLocal" />
          </q-form>
        </div>
      </section>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useQuasar } from 'quasar'
import { useRoute, useRouter } from 'vue-router'

import { useSessionStore } from 'src/stores/session'
import { extractApiMessage } from 'src/utils/format'

const $q = useQuasar()
const route = useRoute()
const router = useRouter()
const session = useSessionStore()

const loadingAuthOptions = ref(true)
const submittingLocal = ref(false)
const submittingLdap = ref(false)
const localForm = ref({ email: '', password: '' })
const ldapForm = ref({ email: '', password: '' })
const transientError = ref('')

const errorMessage = computed(() => transientError.value || route.query.error || '')

function targetRoute() {
  const requested = route.query.redirect
  if (typeof requested === 'string' && requested.startsWith('/')) {
    return requested
  }
  return session.user?.role === 'app_admin' ? '/admin' : '/diversions'
}

async function redirectAfterLogin() {
  await router.replace(targetRoute())
}

async function submitLocal() {
  submittingLocal.value = true
  transientError.value = ''
  try {
    await session.signInLocal(localForm.value)
    await redirectAfterLogin()
  } catch (error) {
    transientError.value = extractApiMessage(error, 'Local sign-in failed.')
  } finally {
    submittingLocal.value = false
  }
}

async function submitLdap() {
  submittingLdap.value = true
  transientError.value = ''
  try {
    await session.signInLdap(ldapForm.value)
    await redirectAfterLogin()
  } catch (error) {
    transientError.value = extractApiMessage(error, 'LDAP sign-in failed.')
  } finally {
    submittingLdap.value = false
  }
}

onMounted(async () => {
  try {
    await session.initialize()
    if (session.user) {
      await redirectAfterLogin()
    }
  } catch (error) {
    $q.notify({ type: 'negative', message: extractApiMessage(error, 'Unable to load authentication options.') })
  } finally {
    loadingAuthOptions.value = false
  }
})
</script>

<style scoped>
.login-grid {
  width: 100%;
  max-width: 1220px;
  display: grid;
  grid-template-columns: minmax(0, 1.3fr) minmax(360px, 0.8fr);
  gap: 1rem;
}

.login-page-shell {
  min-height: 100vh;
  width: 100%;
}

.hero-side {
  min-height: 620px;
}

.hero-notes {
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

@media (max-width: 960px) {
  .login-grid {
    grid-template-columns: 1fr;
  }

  .hero-notes {
    grid-template-columns: 1fr;
  }
}
</style>