<template>
  <Teleport to="body">
    <transition name="sp-fade" appear>
      <div class="fixed inset-0 z-[70] flex items-center justify-center sp-scrim p-4 backdrop-blur-md" @click.self="$emit('close')">
        <transition name="sp-pop" appear>
          <div ref="panelEl" v-glass="{ scale: -90, chroma: 6, blur: 4, saturate: 1.7, radius: 22 }"role="dialog" aria-modal="true" aria-label="Add bucket" class="sp-modal w-full max-w-[400px] p-5">
            <h2 class="sp-display text-lg font-semibold text-ink-gray-9">Add bucket</h2>
            <p class="mt-0.5 text-sm sp-ink-3">A new column for this board.</p>

            <input
              ref="nameEl"
              v-model="name"
              placeholder="Bucket name (e.g. In Review)"
              class="mt-4 h-9 w-full rounded-xl border sp-hair bg-transparent px-3 text-sm focus:border-outline-gray-3 focus:outline-none"
              @keyup.enter="submit"
            />

            <p class="sp-uppercase mb-2 mt-4">Colour</p>
            <div class="flex flex-wrap gap-2.5">
              <button
                v-for="c in PALETTE"
                :key="c"
                class="sp-swatch h-6 w-6"
                :class="color === c ? 'sp-swatch-active' : ''"
                :style="{ background: c, color: c }"
                @click="pick(c)"
              />
            </div>

            <div class="mt-6 flex justify-end gap-2">
              <Button variant="subtle" @click="$emit('close')">Cancel</Button>
              <AccentButton :loading="loading" @click="submit">Add bucket</AccentButton>
            </div>
          </div>
        </transition>
      </div>
    </transition>
  </Teleport>
</template>

<script setup>
import { ref, watch, onMounted, nextTick } from 'vue'
import { Button } from 'frappe-ui'
import AccentButton from '@/components/AccentButton.vue'
import { bucketColorFor, BUCKET_PALETTE } from '@/lib/board'
import { useOverlay } from '@/composables/useOverlay'
import { breakpoint } from '@/composables/useBreakpoint'

const props = defineProps({
  loading: { type: Boolean, default: false },
  index: { type: Number, default: 0 },
})
const emit = defineEmits(['close', 'create'])

const panelEl = ref(null)
useOverlay({ close: () => emit('close'), panel: panelEl })

const PALETTE = BUCKET_PALETTE
const name = ref('')
const color = ref(bucketColorFor('', props.index))
const manual = ref(false)
const nameEl = ref(null)

// follow the typed name until the user picks a colour by hand
watch(name, (n) => {
  if (!manual.value) color.value = bucketColorFor(n, props.index)
})
function pick(c) {
  manual.value = true
  color.value = c
}
function submit() {
  const bucket_name = name.value.trim()
  if (!bucket_name) {
    nameEl.value?.focus()
    return
  }
  emit('create', { bucket_name, color: color.value })
}

onMounted(() => nextTick(() => !breakpoint.isTouch && nameEl.value?.focus()))
</script>
