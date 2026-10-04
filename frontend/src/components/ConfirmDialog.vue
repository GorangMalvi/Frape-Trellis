<template>
  <Teleport to="body">
    <transition name="sp-fade" appear>
      <div v-if="open" class="fixed inset-0 z-[80] flex items-center justify-center sp-scrim p-4 backdrop-blur-md" @click.self="cancel">
        <transition name="sp-pop" appear>
          <div ref="panelEl" v-glass="{ scale: -90, chroma: 6, blur: 4, saturate: 1.7, radius: 22 }"role="alertdialog" aria-modal="true" :aria-label="title" class="sp-modal w-full max-w-[400px] p-5">
            <h2 class="sp-display text-lg font-semibold text-ink-gray-9">{{ title }}</h2>
            <p v-if="message" class="mt-1 text-sm sp-ink-2">{{ message }}</p>

            <!-- second step: re-auth with the account password -->
            <div v-if="requirePassword" class="mt-4">
              <label class="sp-uppercase mb-1.5 block">Confirm with your password</label>
              <input
                ref="pwEl"
                v-model="password"
                type="password"
                autocomplete="current-password"
                placeholder="Account password"
                class="sp-field w-full"
                @keyup.enter="confirm"
              />
              <p v-if="error" class="mt-1.5 text-xs text-ink-red-3">{{ error }}</p>
            </div>

            <div class="mt-6 flex justify-end gap-2">
              <Button variant="subtle" @click="cancel">Cancel</Button>
              <Button variant="solid" theme="red" :loading="busy" @click="confirm">{{ confirmLabel }}</Button>
            </div>
          </div>
        </transition>
      </div>
    </transition>
  </Teleport>
</template>

<script setup>
import { ref, watch, nextTick } from 'vue'
import { Button, call } from 'frappe-ui'
import { useOverlay } from '@/composables/useOverlay'

const props = defineProps({
  open: Boolean,
  title: { type: String, default: 'Are you sure?' },
  message: { type: String, default: '' },
  confirmLabel: { type: String, default: 'Delete' },
  requirePassword: { type: Boolean, default: false },
})
const emit = defineEmits(['confirm', 'cancel'])

const password = ref('')
const error = ref('')
const busy = ref(false)

watch(
  () => props.open,
  (o) => {
    if (o) {
      password.value = ''
      error.value = ''
      busy.value = false
      if (props.requirePassword) nextTick(() => pwEl.value?.focus())
    }
  },
)
const pwEl = ref(null)
const panelEl = ref(null)
useOverlay({ close: cancel, panel: panelEl, active: () => props.open })

async function confirm() {
  if (props.requirePassword) {
    if (!password.value) {
      error.value = 'Enter your password to continue.'
      return
    }
    busy.value = true
    error.value = ''
    try {
      const ok = await call('sprint.api.verify_password', { password: password.value })
      if (!ok) {
        error.value = 'Incorrect password.'
        busy.value = false
        return
      }
    } catch (e) {
      error.value = 'Could not verify password. Try again.'
      busy.value = false
      return
    }
  }
  emit('confirm')
}
function cancel() {
  emit('cancel')
}
</script>
