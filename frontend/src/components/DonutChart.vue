<template>
  <div>
    <p v-if="!segments.length" class="py-4 text-sm sp-ink-4">No data yet.</p>
    <div v-else class="flex items-center gap-4">
      <svg :width="size" :height="size" :viewBox="`0 0 ${size} ${size}`" class="shrink-0 -rotate-90">
        <circle :cx="c" :cy="c" :r="r" fill="none" :stroke-width="stroke" class="stroke-[var(--sp-fill)]" />
        <circle
          v-for="s in segments"
          :key="s.key"
          :cx="c" :cy="c" :r="r"
          fill="none"
          :stroke="s.color"
          :stroke-width="stroke"
          :stroke-dasharray="`${s.len} ${circumference - s.len}`"
          :stroke-dashoffset="-s.offset"
          :class="clickable ? 'cursor-pointer transition-opacity hover:opacity-80' : ''"
          @click="clickable && $emit('select', s)"
        >
          <title>{{ s.label }}: {{ s.value }}</title>
        </circle>
        <text :x="c" :y="c" text-anchor="middle" dominant-baseline="central" class="rotate-90 fill-[rgb(var(--sp-ink)/0.9)] sp-tnum" :style="{ fontSize: '18px', fontWeight: 600, transformOrigin: 'center' }">
          {{ total }}
        </text>
      </svg>
      <div class="sp-scroll min-w-0 flex-1 space-y-1 overflow-y-auto" :style="{ maxHeight: size + 'px' }">
        <button
          v-for="s in segments"
          :key="s.key"
          class="flex w-full items-center gap-1.5 rounded px-1 py-0.5 text-left"
          :class="clickable ? 'transition hover:bg-[var(--sp-fill)]' : 'cursor-default'"
          @click="clickable && $emit('select', s)"
        >
          <span class="h-2 w-2 shrink-0 rounded-full" :style="{ background: s.color }" />
          <span class="min-w-0 flex-1 truncate text-xs text-ink-gray-7">{{ s.label }}</span>
          <span class="text-xs font-medium sp-ink-2 sp-tnum">{{ s.value }}</span>
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
// Token-native SVG donut. Caps at maxSlices, folding the tail into "Other".
import { computed } from 'vue'

const props = defineProps({
  rows: { type: Array, default: () => [] },   // [{key,label,value,color}]
  clickable: { type: Boolean, default: false },
  maxSlices: { type: Number, default: 6 },
})
defineEmits(['select'])

const size = 132
const stroke = 16
const c = size / 2
const r = c - stroke / 2
const circumference = computed(() => 2 * Math.PI * r)

const capped = computed(() => {
  const rows = (props.rows || []).filter((x) => Number(x.value) > 0)
  if (rows.length <= props.maxSlices) return rows
  const head = rows.slice(0, props.maxSlices - 1)
  const tail = rows.slice(props.maxSlices - 1)
  const other = tail.reduce((s, x) => s + Number(x.value), 0)
  return [...head, { key: '__other__', label: `Other (${tail.length})`, value: other, color: 'var(--sp-fill-strong)' }]
})
const total = computed(() => capped.value.reduce((s, x) => s + Number(x.value), 0))

const segments = computed(() => {
  const t = total.value || 1
  let offset = 0
  return capped.value.map((x) => {
    const len = (Number(x.value) / t) * circumference.value
    const seg = { ...x, len, offset }
    offset += len
    return seg
  })
})
</script>
