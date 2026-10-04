<template>
  <div class="h-full overflow-y-auto sp-ground">
    <div class="flex min-h-full items-center justify-center px-4 py-12">
      <div class="w-full max-w-[380px]">
        <div class="mb-8 flex flex-col items-center gap-3">
          <div class="flex h-12 w-12 items-center justify-center rounded-[14px] bg-gradient-to-b from-[#0a84ff] to-[#0071e3] text-lg font-bold text-white shadow-sm">
            S
          </div>
          <h1 class="sp-display text-xl font-semibold sp-ink-1">Set your password</h1>
          <p class="-mt-1 text-center text-sm sp-ink-3">Choose a password to activate your account.</p>
        </div>

        <div class="sp-modal p-6">
          <div v-if="!key" class="flex flex-col items-center gap-2 py-2 text-center">
            <div class="flex h-10 w-10 items-center justify-center rounded-full bg-[var(--sp-fill)] text-ink-red-3">
              <LucideTriangleAlert class="h-5 w-5" />
            </div>
            <p class="text-sm sp-ink-2">This link is missing its reset token. Request a new one from the sign-in page.</p>
            <button class="mt-2 text-sm text-ink-blue-3 hover:underline" @click="router.replace({ name: 'Login' })">
              Back to sign in
            </button>
          </div>

          <form v-else @submit.prevent="submit">
            <label class="mb-1 block text-sm font-medium sp-ink-2">New password</label>
            <input
              ref="pwEl"
              v-model="password"
              type="password"
              autocomplete="new-password"
              placeholder="••••••••"
              class="mb-3 h-10 w-full rounded-md border sp-hair bg-surface-white px-3 text-sm focus:border-outline-gray-3 focus:outline-none"
            />
            <label class="mb-1 block text-sm font-medium sp-ink-2">Confirm password</label>
            <input
              v-model="confirm"
              type="password"
              autocomplete="new-password"
              placeholder="••••••••"
              class="h-10 w-full rounded-md border sp-hair bg-surface-white px-3 text-sm focus:border-outline-gray-3 focus:outline-none"
              @keyup.enter="submit"
            />

            <p v-if="error" class="mt-3 text-sm text-ink-red-3">{{ error }}</p>

            <button
              type="submit"
              class="sp-btn-primary mt-5 flex h-10 w-full items-center justify-center gap-1.5 text-sm font-medium"
              :disabled="loading"
            >
              <LucideLoader2 v-if="loading" class="h-4 w-4 animate-spin" />
              <span>Set password &amp; continue</span>
            </button>
          </form>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, nextTick } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { setPasswordWithKey } from '@/lib/auth'
import { errorMessage } from '@/store'

const route = useRoute()
const router = useRouter()

const key = ref(String(route.query.key || ''))
const password = ref('')
const confirm = ref('')
const loading = ref(false)
const error = ref('')
const pwEl = ref(null)

onMounted(() => nextTick(() => pwEl.value?.focus()))

async function submit() {
  error.value = ''
  if (!password.value || password.value.length < 6) {
    error.value = 'Choose a password of at least 6 characters.'
    return
  }
  if (password.value !== confirm.value) {
    error.value = 'Passwords do not match.'
    return
  }
  loading.value = true
  try {
    await setPasswordWithKey(key.value, password.value)
    // set_password_with_key logs the user in server-side; a hard reload picks up
    // the fresh session boot and the router guard lands them in the app.
    window.location.href = '/sprint'
  } catch (e) {
    error.value = errorMessage(e, 'Could not set your password. The link may have expired.')
    loading.value = false
  }
}
</script>
