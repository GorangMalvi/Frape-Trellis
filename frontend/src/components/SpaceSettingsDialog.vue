<template>
  <Teleport to="body">
    <transition name="sp-fade" appear>
      <div class="fixed inset-0 z-[70] flex items-center justify-center sp-scrim p-4 backdrop-blur-md" @click.self="$emit('close')">
        <transition name="sp-pop" appear>
          <div ref="panelEl" v-glass="{ scale: -90, chroma: 6, blur: 4, saturate: 1.7, radius: 22 }"role="dialog" aria-modal="true" aria-label="Space settings" class="sp-modal max-h-[85vh] w-full max-w-[460px] overflow-y-auto p-5">
            <h2 class="sp-display text-lg font-semibold text-ink-gray-9">Edit space</h2>

            <label class="mt-4 block text-sm font-medium sp-ink-2">Name</label>
            <input
              v-model="label"
              ref="nameEl"
              class="mt-1 h-9 w-full rounded-md border sp-hair px-2.5 text-sm focus:border-outline-gray-3 focus:outline-none"
              @keyup.enter="save"
            />

            <div class="mt-4">
              <p class="mb-2 text-sm font-medium sp-ink-2">Icon</p>
              <div class="grid grid-cols-[repeat(auto-fill,minmax(2.25rem,1fr))] gap-1.5">
                <button
                  v-for="item in SPACE_ICONS"
                  :key="item"
                  class="sp-space-icon-choice flex h-8 w-8 items-center justify-center rounded-md text-base transition hover:bg-[var(--sp-fill-hover)]"
                  :class="icon === item ? 'sp-space-icon-choice-active' : 'bg-[var(--sp-fill)]'"
                  @click="icon = item"
                >
                  {{ item }}
                </button>
              </div>
              <input
                v-model="icon"
                class="mt-2 h-9 w-20 rounded-md border sp-hair px-2.5 text-center text-base focus:border-outline-gray-3 focus:outline-none"
                maxlength="4"
              />
            </div>

            <div class="mt-4">
              <p class="mb-2 text-sm font-medium sp-ink-2">Color</p>
              <div class="flex flex-wrap gap-2">
                <button
                  v-for="item in SPACE_COLORS"
                  :key="item"
                  class="h-6 w-6 rounded-full transition"
                  :class="color === item ? 'ring-2 ring-offset-1 ring-ink-gray-5' : ''"
                  :style="{ background: item }"
                  @click="color = item"
                />
              </div>
            </div>

            <p v-if="error" class="mt-3 text-sm text-ink-red-3">{{ error }}</p>

            <div class="mt-5 flex justify-end gap-2">
              <Button variant="subtle" @click="$emit('close')">Cancel</Button>
              <AccentButton :loading="saving" @click="save">Save</AccentButton>
            </div>
          </div>
        </transition>
      </div>
    </transition>
  </Teleport>
</template>

<script setup>
import { nextTick, onMounted, ref, watch } from 'vue'
import { Button, call } from 'frappe-ui'
import AccentButton from '@/components/AccentButton.vue'
import { SPACE_COLORS, SPACE_ICONS } from '@/lib/spaceOptions'
import { useOverlay } from '@/composables/useOverlay'
import { breakpoint } from '@/composables/useBreakpoint'

const props = defineProps({ space: { type: Object, required: true } })
const emit = defineEmits(['close', 'changed'])

const panelEl = ref(null)
useOverlay({ close: () => emit('close'), panel: panelEl })

const label = ref('')
const icon = ref('')
const color = ref('')
const saving = ref(false)
const error = ref('')
const nameEl = ref(null)

function sync() {
  label.value = props.space?.label || props.space?.name || ''
  icon.value = props.space?.icon || '📋'
  color.value = props.space?.color || SPACE_COLORS[0]
}

watch(() => props.space, sync, { immediate: true })
onMounted(() => nextTick(() => !breakpoint.isTouch && nameEl.value?.focus()))

async function save() {
  error.value = ''
  if (!label.value.trim()) {
    error.value = 'Please enter a space name.'
    return
  }
  saving.value = true
  try {
    await call('sprint.api.update_space_settings', {
      space: props.space.name,
      label: label.value.trim(),
      icon: icon.value,
      color: color.value,
    })
    emit('changed')
  } catch (e) {
    error.value = e?.messages?.[0] || e?.message || 'Could not save space.'
  } finally {
    saving.value = false
  }
}
</script>
