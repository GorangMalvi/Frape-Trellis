<template>
  <Teleport to="body">
    <div class="fixed bottom-6 right-6 z-[200] flex flex-col gap-2">
      <transition-group name="sp-pop">
        <div
          v-for="t in toasts"
          :key="t.id"
          class="sp-pop flex max-w-sm cursor-pointer items-start gap-2.5 px-3.5 py-2.5 text-sm"
          @click="dismissToast(t.id)"
        >
          <LucideCircleCheck v-if="t.type === 'success'" class="mt-0.5 h-4 w-4 shrink-0 text-ink-green-3" />
          <LucideCircleAlert v-else class="mt-0.5 h-4 w-4 shrink-0 text-ink-red-3" />
          <span class="text-ink-gray-8">{{ t.message }}</span>
        </div>
      </transition-group>
    </div>
  </Teleport>
</template>

<script setup>
import { toasts, dismissToast } from '@/store'
</script>
