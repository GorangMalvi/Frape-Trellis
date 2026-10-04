<template>
  <div>
    <p v-if="!rows.length" class="py-4 text-sm sp-ink-4">No data yet.</p>
    <div v-else class="space-y-2">
      <div
        v-for="row in rows"
        :key="row.key || row.label"
        class="grid grid-cols-[130px_minmax(0,1fr)_44px] items-center gap-2.5"
        :class="clickable ? 'cursor-pointer rounded transition hover:bg-[var(--sp-fill)]' : ''"
        :title="`${row.label}: ${row.value}${unit ? ' ' + unit : ''}`"
        @click="clickable && $emit('select', row)"
      >
        <span class="flex min-w-0 items-center gap-1.5">
          <UserAvatar v-if="row.user" :user="row.user" size="xs" class="shrink-0" />
          <span
            v-else-if="row.color"
            class="h-2 w-2 shrink-0 rounded-full"
            :style="{ background: row.color }"
          />
          <span class="truncate text-xs text-ink-gray-7">{{ row.label }}</span>
        </span>
        <span class="h-4 overflow-hidden rounded-[4px] bg-[var(--sp-fill)]">
          <span
            class="block h-full rounded-[4px] transition-[width] duration-300"
            :style="{
              width: (max ? (row.value / max) * 100 : 0) + '%',
              background: row.color || 'var(--sp-accent)',
            }"
          />
        </span>
        <span class="text-right text-xs font-medium sp-ink-2 sp-tnum">{{ row.value }}</span>
      </div>
    </div>
  </div>
</template>

<script setup>
// Hand-rolled horizontal bars: token-native (dark mode for free), value
// labels in ink at the row end — never on the fill.
import { computed } from 'vue'
import UserAvatar from '@/components/UserAvatar.vue'

const props = defineProps({
  title: String,
  // rows: [{ key?, label, value, color?, user? }]
  rows: { type: Array, default: () => [] },
  unit: { type: String, default: '' },
  clickable: { type: Boolean, default: false },
})
defineEmits(['select'])
const max = computed(() => Math.max(...props.rows.map((r) => Number(r.value) || 0), 0))
</script>
