<template>
  <div>
    <div class="mb-3 flex items-center gap-2">
      <select v-model="ruleFilter" class="sp-field min-w-0 max-w-full">
        <option value="">All automations</option>
        <option v-for="r in rules" :key="r.name" :value="r.name">{{ r.automation_name }}</option>
      </select>
      <button class="sp-control p-1.5" aria-label="Refresh" @click="runs.reload()"><LucideRefreshCw class="h-4 w-4" /></button>
    </div>

    <div v-if="runs.loading && !runs.data" class="space-y-2">
      <div v-for="i in 5" :key="i" class="sp-skeleton h-12 rounded-xl" />
    </div>

    <EmptyState
      v-else-if="!(runs.data || []).length"
      title="No runs yet"
      message="Runs appear here as your automations fire."
    >
      <template #icon><LucideHistory class="h-6 w-6" /></template>
    </EmptyState>

    <div v-else class="overflow-hidden rounded-2xl sp-surface shadow-[var(--sp-e1)] ring-1 ring-[color:var(--sp-line)]">
      <div v-for="(r, ri) in runs.data" :key="r.name" :class="ri ? 'border-t sp-hair' : ''">
        <button class="grid w-full grid-cols-[64px_minmax(0,1fr)_20px] items-center gap-2 px-3 py-2.5 text-left text-sm transition hover:bg-[var(--sp-fill)] sm:grid-cols-[80px_minmax(0,1fr)_70px_90px_20px] sm:gap-3 sm:px-4" @click="toggle(r.name)">
          <span class="rounded-full px-2 py-0.5 text-center text-xs font-medium" :class="pillClass(r.status)">{{ r.status }}</span>
          <span class="min-w-0">
            <span class="block truncate font-medium text-ink-gray-8">{{ r.automation_label || '—' }}</span>
            <button v-if="r.ref_name" class="truncate text-xs text-[color:var(--sp-accent)] hover:underline" @click.stop="openCard(r)">
              {{ r.doc_title || r.ref_name }}
            </button>
            <span class="block text-xs sp-ink-4 sm:hidden">{{ timeAgo(r.creation) }} · {{ r.duration_ms }} ms</span>
          </span>
          <span class="text-right text-xs sp-ink-3 sp-tnum max-sm:hidden">{{ r.duration_ms }} ms</span>
          <span class="text-right text-xs sp-ink-4 max-sm:hidden">{{ timeAgo(r.creation) }}</span>
          <LucideChevronRight class="h-3.5 w-3.5 sp-ink-4 transition-transform" :class="{ 'rotate-90': expanded === r.name }" />
        </button>
        <div v-if="expanded === r.name" class="border-t sp-hair bg-[var(--sp-fill)] px-4 py-2.5 text-sm">
          <div v-for="(a, ai) in r.actions_log" :key="ai" class="flex items-start gap-1.5">
            <LucideCheck v-if="a.status === 'ok'" class="mt-0.5 h-3.5 w-3.5 shrink-0 text-ink-green-3" />
            <LucideClock v-else-if="a.status === 'queued'" class="mt-0.5 h-3.5 w-3.5 shrink-0 text-ink-amber-3" />
            <LucideMinus v-else-if="a.status === 'skipped'" class="mt-0.5 h-3.5 w-3.5 shrink-0 sp-ink-4" />
            <LucideX v-else class="mt-0.5 h-3.5 w-3.5 shrink-0 text-ink-red-3" />
            <span class="sp-ink-2">{{ a.detail || a.type }}</span>
          </div>
          <p v-if="r.error" class="mt-1.5 rounded bg-surface-red-1 px-2 py-1 font-mono text-xs text-ink-red-3">{{ r.error }}</p>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { createResource } from 'frappe-ui'
import EmptyState from '@/components/EmptyState.vue'
import { timeAgo } from '@/lib/format'

const props = defineProps({
  space: String,
  rules: { type: Array, default: () => [] },
  isTicket: { type: Boolean, default: false },
})
const router = useRouter()

const ruleFilter = ref('')
const expanded = ref(null)
const runs = createResource({
  url: 'sprint.automation.get_automation_runs',
  makeParams: () => ({ space: props.space, automation: ruleFilter.value || null, limit: 100 }),
  auto: true,
})
watch(ruleFilter, () => runs.reload())

function toggle(name) {
  expanded.value = expanded.value === name ? null : name
}
function pillClass(status) {
  return {
    Success: 'text-ink-green-3 bg-surface-green-1',
    Partial: 'text-ink-amber-3 bg-surface-amber-1',
    Failed: 'text-ink-red-3 bg-surface-red-1',
    Skipped: 'sp-ink-3 bg-[var(--sp-fill)]',
  }[status] || 'sp-ink-3 bg-[var(--sp-fill)]'
}
function openCard(r) {
  // all runs here belong to this space; open its board with the card drawer
  router.push(props.isTicket
    ? { name: 'TicketBoard', params: { space: props.space }, query: { ticket: r.ref_name } }
    : { name: 'Board', params: { space: props.space }, query: { card: r.ref_name } })
}
</script>
