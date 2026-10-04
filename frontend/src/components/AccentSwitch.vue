<template>
  <button
    type="button"
    role="switch"
    :aria-checked="modelValue"
    :disabled="disabled"
    class="relative inline-flex h-5 w-9 shrink-0 items-center rounded-full transition disabled:opacity-50"
    :style="{ background: modelValue ? 'var(--sp-accent)' : 'var(--sp-fill-strong)' }"
    @click.stop="disabled || $emit('update:modelValue', !modelValue)"
  >
    <span
      class="inline-block h-4 w-4 rounded-full bg-white shadow-sm transition-transform"
      :class="modelValue ? 'translate-x-[18px]' : 'translate-x-0.5'"
    />
  </button>
</template>

<script setup>
defineProps({ modelValue: Boolean, disabled: Boolean })
defineEmits(['update:modelValue'])
</script>
