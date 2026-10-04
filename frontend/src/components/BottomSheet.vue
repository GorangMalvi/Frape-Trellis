<template>
  <Teleport to="body">
    <transition name="sp-fade" appear>
      <div class="sp-scrim fixed inset-0 z-[70]" @click.self="$emit('close')">
        <transition name="sp-slide-up" appear>
          <div
            ref="panelEl"
            role="dialog"
            aria-modal="true"
            :aria-label="title || 'Menu'"
            class="sp-modal sp-safe-bottom fixed inset-x-0 bottom-0 flex max-h-[75vh] flex-col rounded-b-none"
          >
            <!-- grabber -->
            <div class="flex shrink-0 justify-center pb-1 pt-2.5">
              <div class="h-1 w-9 rounded-full bg-[var(--sp-fill-strong)]" />
            </div>
            <div v-if="title" class="shrink-0 px-4 pb-1 pt-0.5 text-sm font-semibold sp-ink-1">
              {{ title }}
            </div>
            <div class="sp-scroll min-h-0 flex-1 overflow-y-auto px-2 pb-2">
              <slot />
            </div>
            <div v-if="$slots.footer" class="shrink-0 border-t sp-hair px-4 py-3">
              <slot name="footer" />
            </div>
          </div>
        </transition>
      </div>
    </transition>
  </Teleport>
</template>

<script setup>
import { ref } from 'vue'
import { useOverlay } from '@/composables/useOverlay'

defineProps({ title: { type: String, default: '' } })
const emit = defineEmits(['close'])

const panelEl = ref(null)
useOverlay({ close: () => emit('close'), panel: panelEl })
</script>
