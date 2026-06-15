<template>
  <q-page class="row items-center justify-center">
    <div class="status-panel q-pa-xl text-center">
      <q-spinner-rings size="52px" color="orange-4" />
      <div class="text-h6 q-mt-md">Routing you to the right workspace</div>
    </div>
  </q-page>
</template>

<script setup>
import { onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useSessionStore } from 'src/stores/session'

const router = useRouter()
const session = useSessionStore()

onMounted(async () => {
  const destination = session.user?.role === 'app_admin' ? '/admin' : '/diversions'
  await router.replace(destination)
})
</script>