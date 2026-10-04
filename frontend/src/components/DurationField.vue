<template>
  <div class="flex items-center gap-1.5">
    <input
      type="number"
      min="0"
      :value="hours"
      placeholder="0"
      :disabled="disabled"
      class="h-7 w-14 rounded-lg border-0 bg-[var(--sp-fill)] px-2 text-sm transition focus:bg-[var(--sp-fill-hover)] focus:outline-none focus:ring-0"
      @input="onInput('h', $event.target.value)"
      @blur="$emit('commit')"
    />
    <span class="text-xs sp-ink-3">h</span>
    <input
      type="number"
      min="0"
      max="59"
      :value="mins"
      placeholder="0"
      :disabled="disabled"
      class="h-7 w-14 rounded-lg border-0 bg-[var(--sp-fill)] px-2 text-sm transition focus:bg-[var(--sp-fill-hover)] focus:outline-none focus:ring-0"
      @input="onInput('m', $event.target.value)"
      @blur="$emit('commit')"
    />
    <span class="text-xs sp-ink-3">m</span>
  </div>
</template>

<script setup>
import { computed } from 'vue'

// modelValue is stored in seconds (Frappe Duration convention)
const props = defineProps({
  modelValue: { type: [Number, String], default: 0 },
  disabled: { type: Boolean, default: false },
})
const emit = defineEmits(['update:modelValue', 'commit'])

const seconds = computed(() => Number(props.modelValue) || 0)
const hours = computed(() => Math.floor(seconds.value / 3600))
const mins = computed(() => Math.floor((seconds.value % 3600) / 60))

function onInput(part, raw) {
  if (props.disabled) return
  const v = Math.max(0, parseInt(raw, 10) || 0)
  const h = part === 'h' ? v : hours.value
  const m = part === 'm' ? v : mins.value
  emit('update:modelValue', h * 3600 + m * 60)
}
</script>
