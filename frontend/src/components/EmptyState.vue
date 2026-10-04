<template>
  <div class="flex h-full flex-col items-center justify-center gap-1.5 px-6 py-16 text-center">
    <div
      v-if="$slots.icon"
      class="mb-2 flex h-12 w-12 items-center justify-center rounded-2xl bg-[var(--sp-fill)] sp-ink-3"
    >
      <slot name="icon" />
    </div>
    <p class="sp-display text-[15px] font-semibold sp-ink-2">{{ title }}</p>
    <p v-if="message" class="max-w-sm text-sm leading-relaxed sp-ink-3">{{ message }}</p>
    <div v-if="$slots.action" class="mt-4">
      <slot name="action" />
    </div>
  </div>
</template>

<script setup>
defineProps({ title: String, message: String })
</script>
