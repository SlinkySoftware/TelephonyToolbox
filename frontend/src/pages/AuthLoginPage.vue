<!--
SPDX-FileCopyrightText: Copyright 2026, Slinky Software
SPDX-License-Identifier: GPL-3.0-only
-->

<template>
  <div class="login-page-shell row items-center justify-center q-pa-md">
    <div class="login-stage">
      <div class="login-logo-wrap">
        <img src="/images/mainlogo.png" alt="Telephony Toolbox" class="login-main-logo" />
      </div>

      <section class="form-panel q-pa-xl login-card">
        <div class="section-kicker">Sign In</div>
        <div class="text-h5 q-mt-sm">Access the control surface</div>
        <p class="muted-copy q-mt-sm">
          Select the authentication method available for this deployment, then continue with the
          matching sign-in flow.
        </p>

        <q-banner v-if="errorMessage" class="warning-banner q-mb-md text-white">
          {{ errorMessage }}
        </q-banner>

        <q-inner-loading :showing="loadingAuthOptions">
          <q-spinner-rings size="36px" color="orange-4" />
        </q-inner-loading>

        <q-form v-if="authMethodOptions.length" class="q-gutter-md" @submit.prevent="handleSignIn">
          <q-input
            v-model="credentials.email"
            filled
            label="Email Address"
            type="email"
            autocomplete="username"
          />
          <q-select
            v-model="selectedAuthMethod"
            filled
            label="Authentication Method"
            :options="authMethodOptions"
            emit-value
            map-options
          />
          <q-input
            v-if="requiresPassword"
            v-model="credentials.password"
            filled
            label="Password"
            type="password"
            autocomplete="current-password"
          />
          <div v-else class="muted-copy">Password is not required when signing in with Entra.</div>
          <q-btn
            unelevated
            color="orange-6"
            text-color="black"
            class="full-width"
            :label="submitLabel"
            type="submit"
            :loading="Boolean(submittingMethod)"
          />
        </q-form>

        <q-banner v-else-if="!loadingAuthOptions" class="warning-banner q-mt-md text-white">
          No authentication methods are currently available for this deployment.
        </q-banner>
      </section>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useQuasar } from 'quasar'
import { useRoute, useRouter } from 'vue-router'

import { useSessionStore } from 'src/stores/session'
import { extractApiMessage } from 'src/utils/format'

const $q = useQuasar()
const route = useRoute()
const router = useRouter()
const session = useSessionStore()

const loadingAuthOptions = ref(true)
const submittingMethod = ref('')
const selectedAuthMethod = ref('')
const credentials = ref({ email: '', password: '' })
const transientError = ref('')

const routeError = computed(() => (typeof route.query.error === 'string' ? route.query.error : ''))
const errorMessage = computed(() => transientError.value || routeError.value)

const authMethodOptions = computed(() => {
  const options = []
  const authMode = session.authOptions?.auth_mode

  if (authMode === 'ldap') {
    options.push({ label: 'LDAP', value: 'ldap' })
  }
  if (authMode === 'entra') {
    options.push({ label: 'Entra', value: 'entra' })
  }
  if (session.authOptions?.local_auth_enabled || authMode === 'local') {
    options.push({ label: 'Local', value: 'local' })
  }

  return options
})

const requiresPassword = computed(
  () => selectedAuthMethod.value === 'ldap' || selectedAuthMethod.value === 'local',
)

const submitLabel = computed(() => {
  switch (selectedAuthMethod.value) {
    case 'ldap':
      return 'Sign in with LDAP'
    case 'local':
      return 'Sign in with Local'
    case 'entra':
      return 'Continue with Entra'
    default:
      return 'Sign in'
  }
})

watch(
  authMethodOptions,
  (options) => {
    if (options.some((option) => option.value === selectedAuthMethod.value)) {
      return
    }
    selectedAuthMethod.value =
      options.find((option) => option.value !== 'local')?.value || options[0]?.value || ''
  },
  { immediate: true },
)

watch(selectedAuthMethod, (value) => {
  if (value === 'entra') {
    credentials.value.password = ''
  }
})

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

async function handleSignIn() {
  const method = selectedAuthMethod.value
  if (!method) {
    transientError.value = 'No authentication method is available.'
    return
  }

  submittingMethod.value = method
  transientError.value = ''
  try {
    if (method === 'local') {
      await session.signInLocal(credentials.value)
      await redirectAfterLogin()
      return
    }

    if (method === 'ldap') {
      await session.signInLdap(credentials.value)
      await redirectAfterLogin()
      return
    }

    session.beginEntraLogin()
  } catch (error) {
    transientError.value = extractApiMessage(
      error,
      method === 'ldap'
        ? 'LDAP sign-in failed.'
        : method === 'local'
          ? 'Local sign-in failed.'
          : 'Entra sign-in failed.',
    )
  } finally {
    submittingMethod.value = ''
  }
}

onMounted(async () => {
  try {
    await session.initialize()
    if (session.user) {
      await redirectAfterLogin()
    }
  } catch (error) {
    $q.notify({
      type: 'negative',
      message: extractApiMessage(error, 'Unable to load authentication options.'),
    })
  } finally {
    loadingAuthOptions.value = false
  }
})
</script>

<style scoped>
.login-page-shell {
  min-height: 100vh;
  width: 100%;
}

.login-stage {
  width: 100%;
  max-width: 560px;
  display: flex;
  flex-direction: column;
  align-items: center;
}

.login-logo-wrap {
  position: relative;
  width: 100%;
  display: flex;
  justify-content: center;
  padding: 0 1rem 1.25rem;
  isolation: isolate;
}

.login-logo-wrap::after {
  content: '';
  position: absolute;
  inset: auto 8% 0;
  height: 76%;
  border-radius: 999px;
  background:
    radial-gradient(
      circle at center,
      rgba(239, 154, 72, 0.28) 0%,
      rgba(239, 154, 72, 0.14) 40%,
      rgba(255, 215, 171, 0.08) 58%,
      transparent 78%
    ),
    radial-gradient(
      circle at center,
      rgba(16, 13, 11, 0.62) 8%,
      rgba(16, 13, 11, 0.12) 48%,
      transparent 78%
    );
  filter: blur(24px);
  transform: translateY(10%) scaleX(1.04);
  z-index: -1;
  pointer-events: none;
}

.login-main-logo {
  display: block;
  width: min(100%, 460px);
  height: auto;
  filter: drop-shadow(0 14px 34px rgba(9, 7, 6, 0.36))
    drop-shadow(0 0 28px rgba(239, 154, 72, 0.16));
  -webkit-mask-image: radial-gradient(
    ellipse at center,
    #000 68%,
    rgba(0, 0, 0, 0.92) 79%,
    rgba(0, 0, 0, 0.46) 90%,
    transparent 100%
  );
  mask-image: radial-gradient(
    ellipse at center,
    #000 68%,
    rgba(0, 0, 0, 0.92) 79%,
    rgba(0, 0, 0, 0.46) 90%,
    transparent 100%
  );
}

.login-card {
  width: 100%;
  max-width: 520px;
}
</style>
