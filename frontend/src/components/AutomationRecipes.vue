<template>
  <div class="grid gap-2.5 sm:grid-cols-2 lg:grid-cols-3">
    <button
      v-for="r in recipes"
      :key="r.id"
      class="sp-card flex flex-col gap-1.5 p-3.5 text-left"
      @click="$emit('pick', r)"
    >
      <span class="flex h-8 w-8 items-center justify-center rounded-lg bg-[var(--sp-fill)] sp-ink-2">
        <AutomationIcon :kind="r.icon" class="h-4 w-4" />
      </span>
      <span class="text-sm font-semibold sp-ink-1">{{ r.name }}</span>
      <span class="text-xs leading-relaxed sp-ink-3">{{ r.description }}</span>
    </button>
  </div>
</template>

<script setup>
import AutomationIcon from '@/components/AutomationIcon.vue'

defineProps({ recipes: { type: Array, default: () => [] } })
defineEmits(['pick'])
</script>
