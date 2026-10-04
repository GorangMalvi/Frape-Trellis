<template>
  <Teleport to="body">
    <transition name="sp-fade" appear>
      <div class="fixed inset-0 z-[70] flex items-center justify-center sp-scrim p-4 backdrop-blur-md" @click.self="$emit('close')">
        <transition name="sp-pop" appear>
          <div ref="panelEl" v-glass="{ scale: -90, chroma: 6, blur: 4, saturate: 1.7, radius: 22 }"role="dialog" aria-modal="true" :aria-label="title" class="sp-modal w-full max-w-[400px] p-5">
            <h2 class="sp-display text-lg font-semibold text-ink-gray-9">{{ title }}</h2>
            <p v-if="message" class="mt-1 text-sm sp-ink-2">{{ message }}</p>
            <input
              v-model="name"
              autofocus
              :placeholder="placeholder"
              class="sp-field mt-4 w-full"
              @keyup.enter="submit"
            />
            <div class="mt-6 flex justify-end gap-2">
              <Button variant="subtle" @click="$emit('close')">Cancel</Button>
              <AccentButton :loading="loading" :disabled="!name.trim()" @click="submit">
                {{ confirmLabel }}
              </AccentButton>
            </div>
          </div>
        </transition>
      </div>
    </transition>
  </Teleport>
</template>

<script setup>
import { ref } from 'vue'
import { Button } from 'frappe-ui'
import AccentButton from '@/components/AccentButton.vue'
import { useOverlay } from '@/composables/useOverlay'

defineProps({
  title: { type: String, default: 'Name' },
  message: String,
  placeholder: { type: String, default: 'Name…' },
  confirmLabel: { type: String, default: 'Save' },
  loading: Boolean,
})
const emit = defineEmits(['close', 'submit'])

const name = ref('')
const panelEl = ref(null)
useOverlay({ close: () => emit('close'), panel: panelEl })

function submit() {
  if (name.value.trim()) emit('submit', name.value.trim())
}
</script>
