<template>
  <div class="flex h-full flex-col">
    <header class="sp-glass-strong z-20 flex items-center gap-2.5 px-4 pt-4 md:px-6">
      <span class="flex h-7 w-7 items-center justify-center rounded-lg bg-[var(--sp-fill)]">
        <LucideUser class="h-4 w-4 sp-ink-2" />
      </span>
      <h1 class="sp-display text-[17px] font-semibold sp-ink-1">My account</h1>
    </header>

    <main class="sp-scroll min-h-0 flex-1 overflow-y-auto px-4 py-5 md:px-6">
      <div v-if="loading" class="flex max-w-[560px] flex-col gap-3">
        <div class="sp-skeleton h-40 rounded-2xl" />
        <div class="sp-skeleton h-40 rounded-2xl" />
      </div>

      <template v-else>
        <!-- profile -->
        <section class="sp-card mb-4 max-w-[560px] p-5">
          <div class="mb-4 flex items-center gap-3">
            <UserAvatar :user="me" size="xl" />
            <div class="min-w-0">
              <p class="truncate text-sm font-medium sp-ink-1">{{ fullName || me }}</p>
              <p class="truncate text-xs sp-ink-3">{{ email }}</p>
            </div>
          </div>

          <label class="mb-1 block text-sm font-medium sp-ink-2">Full name</label>
          <input
            v-model="fullName"
            class="mb-3 h-9 w-full rounded-md border sp-hair bg-surface-white px-2.5 text-sm focus:border-outline-gray-3 focus:outline-none"
          />

          <label class="mb-1 block text-sm font-medium sp-ink-2">Time zone</label>
          <select
            v-model="timeZone"
            class="h-9 w-full rounded-md border sp-hair bg-surface-white px-2 text-sm focus:outline-none"
          >
            <option v-for="tz in tzOptions" :key="tz" :value="tz">{{ tz }}</option>
          </select>

          <p v-if="profileError" class="mt-3 text-sm text-ink-red-3">{{ profileError }}</p>

          <div class="mt-4 flex justify-end">
            <AccentButton :loading="savingProfile" @click="saveProfile">Save changes</AccentButton>
          </div>
        </section>

        <!-- password -->
        <section class="sp-card max-w-[560px] p-5">
          <h2 class="mb-1 text-base font-semibold text-ink-gray-9">Change password</h2>
          <p class="mb-4 text-sm sp-ink-3">Re-enter your current password to set a new one.</p>

          <label class="mb-1 block text-sm font-medium sp-ink-2">Current password</label>
          <input
            v-model="oldPassword"
            type="password"
            autocomplete="current-password"
            class="mb-3 h-9 w-full rounded-md border sp-hair bg-surface-white px-2.5 text-sm focus:border-outline-gray-3 focus:outline-none"
          />
          <label class="mb-1 block text-sm font-medium sp-ink-2">New password</label>
          <input
            v-model="newPassword"
            type="password"
            autocomplete="new-password"
            class="mb-3 h-9 w-full rounded-md border sp-hair bg-surface-white px-2.5 text-sm focus:border-outline-gray-3 focus:outline-none"
          />
          <label class="mb-1 block text-sm font-medium sp-ink-2">Confirm new password</label>
          <input
            v-model="confirmPassword"
            type="password"
            autocomplete="new-password"
            class="h-9 w-full rounded-md border sp-hair bg-surface-white px-2.5 text-sm focus:border-outline-gray-3 focus:outline-none"
          />

          <p v-if="pwError" class="mt-3 text-sm text-ink-red-3">{{ pwError }}</p>

          <div class="mt-4 flex justify-end">
            <AccentButton :loading="savingPassword" @click="savePassword">Update password</AccentButton>
          </div>
        </section>
      </template>
    </main>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { call } from 'frappe-ui'
import AccentButton from '@/components/AccentButton.vue'
import UserAvatar from '@/components/UserAvatar.vue'
import { currentUser, users as userCache } from '@/lib/users'
import { pushToast, errorMessage } from '@/store'

const me = ref(currentUser())
const email = ref('')
const fullName = ref('')
const timeZone = ref('')

const loading = ref(true)
const savingProfile = ref(false)
const savingPassword = ref(false)
const profileError = ref('')
const pwError = ref('')

const oldPassword = ref('')
const newPassword = ref('')
const confirmPassword = ref('')

// A curated set of common IANA zones; the user's own zone is always included.
const COMMON_TZ = [
  'UTC', 'America/Los_Angeles', 'America/Denver', 'America/Chicago', 'America/New_York',
  'America/Sao_Paulo', 'Europe/London', 'Europe/Paris', 'Europe/Berlin', 'Europe/Moscow',
  'Africa/Johannesburg', 'Asia/Dubai', 'Asia/Kolkata', 'Asia/Singapore', 'Asia/Shanghai',
  'Asia/Tokyo', 'Australia/Sydney',
]
const tzOptions = ref(COMMON_TZ)

onMounted(async () => {
  try {
    const p = await call('sprint.api.get_my_profile')
    me.value = p.user
    email.value = p.email
    fullName.value = p.full_name
    timeZone.value = p.time_zone || 'UTC'
    if (p.time_zone && !COMMON_TZ.includes(p.time_zone)) {
      tzOptions.value = [p.time_zone, ...COMMON_TZ]
    }
  } catch (e) {
    pushToast(errorMessage(e))
  } finally {
    loading.value = false
  }
})

async function saveProfile() {
  profileError.value = ''
  if (!fullName.value.trim()) {
    profileError.value = 'Please enter your name.'
    return
  }
  savingProfile.value = true
  try {
    const p = await call('sprint.api.update_my_profile', {
      full_name: fullName.value.trim(),
      time_zone: timeZone.value,
    })
    fullName.value = p.full_name
    userCache.loaded = false // refresh cached name/avatar everywhere
    pushToast('Profile updated.', 'success')
  } catch (e) {
    profileError.value = errorMessage(e, 'Could not save your profile.')
  } finally {
    savingProfile.value = false
  }
}

async function savePassword() {
  pwError.value = ''
  if (!oldPassword.value) {
    pwError.value = 'Enter your current password.'
    return
  }
  if (!newPassword.value || newPassword.value.length < 6) {
    pwError.value = 'Choose a new password of at least 6 characters.'
    return
  }
  if (newPassword.value !== confirmPassword.value) {
    pwError.value = 'New passwords do not match.'
    return
  }
  savingPassword.value = true
  try {
    await call('sprint.api.change_my_password', {
      old_password: oldPassword.value,
      new_password: newPassword.value,
    })
    oldPassword.value = ''
    newPassword.value = ''
    confirmPassword.value = ''
    pushToast('Password updated.', 'success')
  } catch (e) {
    pwError.value = errorMessage(e, 'Could not update your password.')
  } finally {
    savingPassword.value = false
  }
}
</script>
