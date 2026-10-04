<template>
  <div class="sp-card flex flex-col p-4" :class="widget.type === 'stat' ? '' : 'min-h-[13rem]'">
    <!-- header: title + (edit-mode) drag / edit / remove -->
    <div class="mb-2 flex items-center gap-1.5">
      <LucideGripVertical v-if="editing" class="widget-drag-handle h-4 w-4 shrink-0 cursor-grab sp-ink-4" />
      <p class="min-w-0 flex-1 truncate" :class="widget.type === 'stat' ? 'sp-uppercase' : 'text-sm font-semibold sp-ink-1'">
        {{ title }}
      </p>
      <template v-if="editing">
        <button class="rounded p-1 sp-ink-4 transition hover:bg-[var(--sp-fill)] hover:text-ink-gray-8" title="Edit widget" @click="$emit('edit')">
          <LucidePencil class="h-3.5 w-3.5" />
        </button>
        <button class="rounded p-1 sp-ink-4 transition hover:bg-[var(--sp-fill)] hover:text-ink-red-3" title="Remove widget" @click="$emit('remove')">
          <LucideX class="h-3.5 w-3.5" />
        </button>
      </template>
    </div>

    <!-- body -->
    <template v-if="widget.type === 'stat'">
      <p class="sp-display text-[28px] font-semibold leading-none sp-tnum" :class="widget.tone === 'warning' && Number(result.value) > 0 ? 'text-ink-red-3' : 'sp-ink-1'">
        {{ result.value }}
      </p>
    </template>
    <div v-else class="min-h-0 flex-1">
      <BarChart v-if="widget.chart !== 'donut'" :rows="result.rows" :clickable="drillable" @select="onSelect" />
      <DonutChart v-else :rows="result.rows" :clickable="drillable" @select="onSelect" />
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import BarChart from '@/components/BarChart.vue'
import DonutChart from '@/components/DonutChart.vue'
import { aggregate, autoTitle, isChipField } from '@/lib/dashboard'

const props = defineProps({
  widget: { type: Object, required: true },
  cards: { type: Array, default: () => [] },
  ctx: { type: Object, required: true },
  editing: { type: Boolean, default: false },
})
const emit = defineEmits(['edit', 'remove', 'drill'])

const title = computed(() => autoTitle(props.widget, props.ctx))
const result = computed(() => aggregate(props.cards, props.widget, props.ctx))

// drill only makes sense for charts, off in edit mode, and not on "Other"/none
const drillable = computed(() => props.widget.type === 'chart' && !props.editing)

function onSelect(row) {
  if (!drillable.value || !row || row.key === '__none__' || row.key === '__other__') return
  emit('drill', {
    field: props.widget.group_by || props.ctx.bucketField,
    value: row.key,
    isChip: isChipField(props.ctx, props.widget.group_by),
  })
}
</script>
