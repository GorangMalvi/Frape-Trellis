<template>
  <div>
    <button
      ref="triggerEl"
      class="sp-control flex shrink-0 items-center gap-1.5 px-2.5 py-1.5 text-sm"
      :class="filters.length ? 'sp-control-active' : ''"
      @click="toggle"
    >
      <LucideListFilter class="h-4 w-4" />
      Filter
      <span v-if="filters.length" class="rounded-full bg-[var(--sp-fill-strong)] px-1.5 text-xs sp-tnum">{{ filters.length }}</span>
    </button>

    <!-- Teleported so the toolbar's scroll container / backdrop-filter can't
         clip it; anchored to the trigger, clamped to the viewport on phones. -->
    <Teleport to="body">
      <div v-if="open" class="fixed inset-0 z-[60]" @click="open = false" />
      <div
        v-if="open"
        ref="panelEl"
        role="dialog"
        aria-label="Filters"
        class="sp-pop fixed z-[60] w-[min(420px,calc(100vw-1.5rem))] p-3"
        :style="panelStyle"
      >
        <FilterRows
          v-model="local"
          :fields="fields"
          :buckets="buckets"
          add-label="Add filter"
          empty-text="No filters. Add one to narrow this view."
        />
        <div class="mt-3 flex items-center justify-end gap-2 border-t sp-hair pt-2.5">
          <Button variant="ghost" @click="clearAll">Clear</Button>
          <AccentButton @click="apply">Apply</AccentButton>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<script setup>
import { ref, watch } from 'vue'
import { Button } from 'frappe-ui'
import AccentButton from '@/components/AccentButton.vue'
import FilterRows from '@/components/FilterRows.vue'
import { useOverlay } from '@/composables/useOverlay'

const props = defineProps({
  filters: { type: Array, default: () => [] },
  fields: { type: Array, default: () => [] },
  buckets: { type: Array, default: () => [] },
})
const emit = defineEmits(['update'])

const open = ref(false)
const local = ref([])
const triggerEl = ref(null)
const panelEl = ref(null)
const panelStyle = ref({})
useOverlay({ close: () => (open.value = false), panel: panelEl, active: () => open.value })

function toggle() {
  if (!open.value) {
    const rect = triggerEl.value?.getBoundingClientRect()
    const width = Math.min(420, window.innerWidth - 24)
    const left = Math.max(12, Math.min(rect?.left ?? 12, window.innerWidth - width - 12))
    panelStyle.value = { top: `${(rect?.bottom ?? 0) + 6}px`, left: `${left}px` }
  }
  open.value = !open.value
}

watch(
  () => open.value,
  (o) => {
    if (o) local.value = JSON.parse(JSON.stringify(props.filters || []))
  },
)

function clearAll() {
  local.value = []
  emit('update', [])
  open.value = false
}
function apply() {
  emit('update', local.value.filter((f) => f.field && f.operator))
  open.value = false
}
</script>
