<template>
  <Teleport to="body">
    <transition name="sp-fade" appear>
      <div class="fixed inset-0 z-[70] flex items-center justify-center sp-scrim p-4 backdrop-blur-md" @click.self="close">
        <transition name="sp-pop" appear>
          <div ref="panelEl" v-glass="{ scale: -90, chroma: 6, blur: 4, saturate: 1.7, radius: 22 }"role="dialog" aria-modal="true" aria-label="Invite user" class="sp-modal max-h-[88vh] w-full max-w-[460px] overflow-auto p-5">
            <!-- invite form -->
            <template v-if="!result">
              <h2 class="sp-display text-lg font-semibold text-ink-gray-9">Invite a user</h2>
              <p class="mt-0.5 text-sm sp-ink-3">They’ll get a link to set their password and sign in.</p>

              <div class="mt-4">
                <label class="mb-1 block text-sm font-medium sp-ink-2">Email</label>
                <input
                  ref="emailEl"
                  v-model="email"
                  type="email"
                  placeholder="person@company.com"
                  class="h-9 w-full rounded-md border sp-hair bg-surface-white px-2.5 text-sm focus:border-outline-gray-3 focus:outline-none"
                />
              </div>

              <div class="mt-3">
                <label class="mb-1 block text-sm font-medium sp-ink-2">Full name</label>
                <input
                  v-model="fullName"
                  placeholder="Jane Doe"
                  class="h-9 w-full rounded-md border sp-hair bg-surface-white px-2.5 text-sm focus:border-outline-gray-3 focus:outline-none"
                />
              </div>

              <div class="mt-3">
                <label class="mb-1 block text-sm font-medium sp-ink-2">Manager</label>
                <select
                  v-model="manager"
                  class="h-9 w-full rounded-md border sp-hair bg-surface-white px-2 text-sm focus:outline-none"
                >
                  <option value="">Select manager…</option>
                  <option v-for="u in managerOptions" :key="u.value" :value="u.value">{{ u.label }}</option>
                </select>
              </div>

              <label class="mt-4 flex cursor-pointer items-center gap-2 text-sm">
                <input v-model="makeManager" type="checkbox" class="rounded" />
                <span class="text-ink-gray-8">Make this user a Sprint Manager</span>
              </label>
              <p class="mt-1 pl-6 text-xs sp-ink-4">Managers can create spaces, manage fields, import data and manage users.</p>

              <p v-if="error" class="mt-3 text-sm text-ink-red-3">{{ error }}</p>

              <div class="mt-5 flex justify-end gap-2">
                <Button variant="subtle" @click="close">Cancel</Button>
                <AccentButton :loading="creating" @click="create">Send invite</AccentButton>
              </div>
            </template>

            <!-- result: copyable invite link -->
            <template v-else>
              <div class="flex flex-col items-center gap-2 pt-1 text-center">
                <div class="flex h-11 w-11 items-center justify-center rounded-full bg-[var(--sp-fill)] text-ink-green-3">
                  <LucideCheck class="h-5 w-5" />
                </div>
                <h2 class="sp-display text-lg font-semibold text-ink-gray-9">Invite created</h2>
                <p class="text-sm sp-ink-3">
                  {{ result.email_sent
                    ? 'We emailed them a set-password link. You can also share this link:'
                    : 'Share this set-password link with them:' }}
                </p>
              </div>

              <div class="mt-4 flex items-center gap-2 rounded-lg border sp-hair bg-[var(--sp-fill)] p-2">
                <input
                  :value="inviteUrl"
                  readonly
                  class="min-w-0 flex-1 bg-transparent px-1 text-xs sp-ink-2 focus:outline-none"
                  @focus="$event.target.select()"
                />
                <Button variant="subtle" @click="copyLink">
                  <template #prefix><LucideCopy class="h-3.5 w-3.5" /></template>
                  {{ copied ? 'Copied' : 'Copy' }}
                </Button>
              </div>

              <div class="mt-5 flex justify-end">
                <AccentButton @click="done">Done</AccentButton>
              </div>
            </template>
          </div>
        </transition>
      </div>
    </transition>
  </Teleport>
</template>

<script setup>
import { computed, ref, onMounted, nextTick } from 'vue'
import { Button, call } from 'frappe-ui'
import AccentButton from '@/components/AccentButton.vue'
import { ensureUsers, userOptions, currentUser } from '@/lib/users'
import { useOverlay } from '@/composables/useOverlay'
import { breakpoint } from '@/composables/useBreakpoint'
import { pushToast } from '@/store'

const emit = defineEmits(['close', 'created'])

const panelEl = ref(null)
useOverlay({ close: () => emit('close'), panel: panelEl })

const email = ref('')
const fullName = ref('')
const manager = ref('')
const makeManager = ref(false)
const creating = ref(false)
const error = ref('')
const result = ref(null)
const copied = ref(false)
const emailEl = ref(null)

const managerOptions = computed(() => userOptions())
const inviteUrl = computed(() => (result.value ? window.location.origin + result.value.invite_url : ''))

onMounted(async () => {
  await ensureUsers()
  // sensible default: the inviter manages the new user
  if (!manager.value) manager.value = currentUser()
  nextTick(() => !breakpoint.isTouch && emailEl.value?.focus())
})

function close() {
  emit('close')
}

async function create() {
  error.value = ''
  const em = email.value.trim().toLowerCase()
  if (!em || !em.includes('@')) {
    error.value = 'Enter a valid email address.'
    return
  }
  creating.value = true
  try {
    result.value = await call('sprint.api.invite_user', {
      email: em,
      full_name: fullName.value.trim(),
      manager: manager.value || '',
      make_manager: makeManager.value ? 1 : 0,
      send_email: 1,
    })
  } catch (e) {
    error.value = e?.messages?.[0] || e?.message || 'Could not create the invite.'
  } finally {
    creating.value = false
  }
}

async function copyLink() {
  try {
    await navigator.clipboard.writeText(inviteUrl.value)
    copied.value = true
    setTimeout(() => (copied.value = false), 1500)
  } catch {
    pushToast('Could not copy — select the link and copy manually.', 'error')
  }
}

function done() {
  emit('created', result.value)
  emit('close')
}
</script>
