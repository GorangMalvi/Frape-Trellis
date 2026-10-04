<template>
  <div class="flex h-full flex-col">
    <header class="sp-glass-strong z-20 flex items-center justify-between px-4 pt-4 md:px-6">
      <div class="flex items-center gap-2.5">
        <span class="flex h-7 w-7 items-center justify-center rounded-[9px] bg-[var(--sp-fill)] text-sm">
          <LucideHouse class="h-4 w-4 sp-ink-2" />
        </span>
        <h1 class="sp-display text-[17px] font-semibold sp-ink-1">Home</h1>
      </div>
      <div class="sp-chip flex gap-0.5 p-0.5">
        <button
          v-for="t in TABS"
          :key="t.key"
          class="flex items-center gap-1.5 rounded-[7px] px-3 py-1 text-sm font-medium transition"
          :class="tab === t.key ? 'sp-seg-active text-ink-gray-9' : 'sp-ink-3 hover:text-ink-gray-8'"
          @click="tab = t.key"
        >
          {{ t.label }}
          <span
            v-if="t.key === 'inbox' && inbox.unread"
            class="rounded-full bg-[color:var(--sp-accent)] px-1.5 text-[11px] font-semibold text-white sp-tnum"
          >
            {{ inbox.unread }}
          </span>
        </button>
      </div>
    </header>

    <main class="sp-scroll min-h-0 flex-1 overflow-y-auto px-4 py-5 md:px-6">
      <!-- ================= MY TASKS ================= -->
      <template v-if="tab === 'tasks'">
        <div v-if="myCards.loading && !myCards.data" class="space-y-2">
          <div class="sp-skeleton mb-3 h-3.5 w-32 rounded" />
          <div v-for="i in 6" :key="i" class="sp-skeleton h-11 rounded-xl" />
        </div>

        <EmptyState
          v-else-if="!(myCards.data || []).length"
          title="Nothing on your plate"
          message="Cards assigned to you across all spaces show up here."
        >
          <template #icon><LucideCoffee class="h-6 w-6" /></template>
        </EmptyState>

        <template v-else>
          <section v-for="g in taskGroups" :key="g.key" class="mb-6">
            <p class="mb-2 flex items-center gap-2 px-1">
              <span
                class="text-sm font-semibold"
                :class="g.key === 'overdue' ? 'text-ink-red-3' : 'sp-ink-1'"
              >{{ g.label }}</span>
              <span class="rounded-full bg-[var(--sp-fill)] px-2 py-0.5 text-xs font-medium sp-ink-3 sp-tnum">
                {{ g.rows.length }}
              </span>
            </p>
            <div class="overflow-hidden rounded-2xl sp-surface shadow-[var(--sp-e1)] ring-1 ring-[color:var(--sp-line)]">
              <button
                v-for="(row, ri) in g.rows"
                :key="row.space + row.name"
                class="grid w-full grid-cols-[minmax(0,1fr)_auto] items-center gap-x-3 gap-y-1 px-4 py-2.5 text-left text-sm transition hover:bg-[var(--sp-fill)] md:grid-cols-[minmax(0,2fr)_150px_90px_60px] md:gap-3"
                :class="ri ? 'border-t sp-hair' : ''"
                @click="openRow(row)"
              >
                <span class="order-1 flex min-w-0 items-center gap-2.5 md:order-none">
                  <span
                    class="sp-space-icon flex h-6 w-6 shrink-0 items-center justify-center rounded-lg text-sm"
                    :style="iconBubbleStyle(row)"
                    :title="row.space_label"
                  >
                    {{ row.space_icon || '📋' }}
                  </span>
                  <span class="truncate font-medium text-ink-gray-8">{{ row.title }}</span>
                </span>
                <span class="order-3 flex min-w-0 items-center gap-1.5 pl-[34px] md:order-none md:pl-0">
                  <span class="h-2 w-2 shrink-0 rounded-full" :style="{ background: row.bucket_color || '#9ca3af' }" />
                  <span class="truncate text-xs text-ink-gray-7">{{ row.bucket_name || '—' }}</span>
                </span>
                <span
                  class="order-2 text-right text-xs md:order-none md:text-left"
                  :class="g.key === 'overdue' ? 'font-medium text-ink-red-3' : 'text-ink-gray-6'"
                >
                  {{ row.due_date ? formatDate(row.due_date) : '' }}
                </span>
                <span class="order-4 flex items-center justify-end gap-1.5 text-xs text-ink-gray-6 md:order-none md:justify-start">
                  <template v-if="row.badge">
                    <span class="h-2 w-2 rounded-full" :style="{ background: colorFor(row.badge) }" />
                    {{ row.badge }}
                  </template>
                </span>
              </button>
            </div>
          </section>
        </template>
      </template>

      <!-- ================= INBOX ================= -->
      <template v-else>
        <div class="mb-3 flex items-center justify-between">
          <p class="text-sm sp-ink-3">Mentions, assignments and ticket updates.</p>
          <Button v-if="inbox.unread" variant="subtle" @click="markAllRead">Mark all read</Button>
        </div>

        <div v-if="notifs.loading && !notifs.data" class="space-y-2">
          <div v-for="i in 5" :key="i" class="sp-skeleton h-12 rounded-xl" />
        </div>

        <EmptyState
          v-else-if="!(notifs.data || []).length"
          title="Inbox zero"
          message="When someone mentions you, assigns you a card, or updates your ticket, it lands here."
        >
          <template #icon><LucideBellOff class="h-6 w-6" /></template>
        </EmptyState>

        <div v-else class="overflow-hidden rounded-2xl sp-surface shadow-[var(--sp-e1)] ring-1 ring-[color:var(--sp-line)]">
          <button
            v-for="(n, ni) in notifs.data"
            :key="n.name"
            class="flex w-full items-center gap-3 px-4 py-3 text-left transition hover:bg-[var(--sp-fill)]"
            :class="ni ? 'border-t sp-hair' : ''"
            @click="openNotification(n)"
          >
            <span
              class="h-2 w-2 shrink-0 rounded-full"
              :class="n.read ? 'bg-transparent' : 'bg-[color:var(--sp-accent)]'"
            />
            <UserAvatar :user="n.from_user" size="md" class="shrink-0" />
            <span class="min-w-0 flex-1">
              <span
                class="block truncate text-sm"
                :class="n.read ? 'text-ink-gray-6' : 'font-medium text-ink-gray-9'"
              >{{ n.subject }}</span>
              <span class="block truncate text-xs sp-ink-4">
                {{ n.space_label || n.document_type }} · {{ when(n.creation) }}
              </span>
            </span>
            <LucideArrowUpRight class="h-4 w-4 shrink-0 sp-ink-4" />
          </button>
        </div>
      </template>
    </main>
  </div>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { Button, call, createResource } from 'frappe-ui'
import UserAvatar from '@/components/UserAvatar.vue'
import EmptyState from '@/components/EmptyState.vue'
import { colorFor } from '@/lib/board'
import { formatDate, when } from '@/lib/format'
import { ensureUsers } from '@/lib/users'
import { inbox, setUnread, pushToast, errorMessage } from '@/store'

const router = useRouter()

const TABS = [
  { key: 'tasks', label: 'My Tasks' },
  { key: 'inbox', label: 'Inbox' },
]
const tab = ref('tasks')

ensureUsers()
const myCards = createResource({ url: 'sprint.api.get_my_cards', auto: true })
const notifs = createResource({ url: 'sprint.api.get_notifications', auto: true })

// live: an incoming sprint_notification bumps inbox.unread (store) — refresh the list
watch(() => inbox.unread, (n, o) => {
  if (n > (o || 0)) notifs.reload()
})

// ---- due-date grouping ----------------------------------------------------
function dayStart(d) {
  const x = new Date(d)
  x.setHours(0, 0, 0, 0)
  return x
}
const taskGroups = computed(() => {
  const today = dayStart(new Date())
  const weekEnd = new Date(today)
  weekEnd.setDate(weekEnd.getDate() + 7)
  const groups = {
    overdue: { key: 'overdue', label: 'Overdue', rows: [] },
    today: { key: 'today', label: 'Today', rows: [] },
    week: { key: 'week', label: 'This week', rows: [] },
    later: { key: 'later', label: 'Later', rows: [] },
    none: { key: 'none', label: 'No due date', rows: [] },
  }
  for (const row of myCards.data || []) {
    if (!row.due_date) {
      groups.none.rows.push(row)
      continue
    }
    const due = dayStart(row.due_date)
    if (due < today) groups.overdue.rows.push(row)
    else if (due.getTime() === today.getTime()) groups.today.rows.push(row)
    else if (due <= weekEnd) groups.week.rows.push(row)
    else groups.later.rows.push(row)
  }
  for (const g of Object.values(groups)) {
    g.rows.sort((a, b) => String(a.due_date || '9999').localeCompare(String(b.due_date || '9999')))
  }
  return Object.values(groups).filter((g) => g.rows.length)
})

function iconBubbleStyle(row) {
  const color = row.space_color || '#8e8e93'
  return { background: `linear-gradient(135deg, ${color}ee 0%, ${color}99 100%)` }
}

// ---- click-through --------------------------------------------------------
function openRow(row) {
  router.push(
    row.space_type === 'Ticket'
      ? { name: 'TicketBoard', params: { space: row.space }, query: { ticket: row.name } }
      : { name: 'Board', params: { space: row.space }, query: { card: row.name } },
  )
}

async function openNotification(n) {
  if (!n.read) {
    n.read = 1
    setUnread(inbox.unread - 1)
    call('sprint.api.mark_notification_read', { name: n.name }).catch(() => {})
  }
  if (!n.space || !n.document_name) return
  router.push(
    n.space_type === 'Ticket'
      ? { name: 'TicketBoard', params: { space: n.space }, query: { ticket: n.document_name } }
      : { name: 'Board', params: { space: n.space }, query: { card: n.document_name } },
  )
}

async function markAllRead() {
  try {
    await call('sprint.api.mark_all_notifications_read')
    setUnread(0)
    notifs.reload()
  } catch (e) {
    pushToast(errorMessage(e))
  }
}
</script>
