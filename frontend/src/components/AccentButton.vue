<template>
  <button
    class="sp-btn-primary inline-flex h-7 items-center justify-center gap-1.5 px-3.5 text-[13px]"
    :disabled="disabled || loading"
    @click="$emit('click', $event)"
  >
    <LucideLoader2 v-if="loading" class="h-3.5 w-3.5 animate-spin" />
    <slot name="prefix" v-else />
    <slot />
  </button>
</template>

<script setup>
// Primary call-to-action button that follows the selected accent (--sp-accent).
// Used instead of frappe-ui's <Button theme="blue">, whose colour is hardcoded.
defineProps({
  loading: { type: Boolean, default: false },
  disabled: { type: Boolean, default: false },
})
defineEmits(['click'])
</script>
