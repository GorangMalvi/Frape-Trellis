<template>
  <Teleport to="body">
    <transition name="sp-fade" appear>
      <div class="fixed inset-0 z-[70] flex items-center justify-center sp-scrim p-4 backdrop-blur-md" @click.self="$emit('close')">
        <transition name="sp-pop" appear>
          <div ref="panelEl" v-glass="{ scale: -90, chroma: 6, blur: 4, saturate: 1.7, radius: 22 }"role="dialog" aria-modal="true" aria-label="Save view" class="sp-modal max-h-[85vh] w-full max-w-[400px] overflow-y-auto p-5">
            <h2 class="sp-display text-lg font-semibold text-ink-gray-9">Save view</h2>
            <p class="mt-0.5 text-sm sp-ink-3">Saves the current group, sort, filters and layout.</p>

            <input
              ref="nameEl"
              v-model="name"
              placeholder="View name (e.g. Current Sprint)"
              class="sp-field mt-4 h-9 w-full"
              @keyup.enter="submit"
            />

            <label class="mt-3 flex cursor-pointer items-start gap-2.5">
              <input type="checkbox" v-model="shared" class="mt-0.5 rounded accent-[color:var(--sp-accent)]" />
              <span class="text-sm">
                <span class="sp-ink-1">Share with the team</span>
                <span class="block text-xs sp-ink-3">Everyone sees it. Uncheck to keep it private to you.</span>
              </span>
            </label>

            <div class="mt-6 flex justify-end gap-2">
              <Button variant="subtle" @click="$emit('close')">Cancel</Button>
              <AccentButton :loading="loading" @click="submit">Save view</AccentButton>
            </div>
          </div>
        </transition>
      </div>
    </transition>
  </Teleport>
</template>

<script setup>
import { ref, onMounted, nextTick } from 'vue'
import { Button } from 'frappe-ui'
import AccentButton from '@/components/AccentButton.vue'
import { useOverlay } from '@/composables/useOverlay'
import { breakpoint } from '@/composables/useBreakpoint'

defineProps({ loading: { type: Boolean, default: false } })
const emit = defineEmits(['close', 'create'])

const panelEl = ref(null)
useOverlay({ close: () => emit('close'), panel: panelEl })

const name = ref('')
const shared = ref(true)
const nameEl = ref(null)

function submit() {
  const n = name.value.trim()
  if (!n) {
    nameEl.value?.focus()
    return
  }
  emit('create', { name: n, is_shared: shared.value ? 1 : 0 })
}
onMounted(() => nextTick(() => !breakpoint.isTouch && nameEl.value?.focus()))
</script>
