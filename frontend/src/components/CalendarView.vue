<template>
  <div class="flex h-full flex-col px-3 py-3 md:px-5 md:py-4">
    <!-- month nav -->
    <div class="mb-3 flex items-center gap-2">
      <button class="sp-control p-1.5" aria-label="Previous month" @click="shiftMonth(-1)">
        <LucideChevronLeft class="h-4 w-4" />
      </button>
      <button class="sp-control p-1.5" aria-label="Next month" @click="shiftMonth(1)">
        <LucideChevronRight class="h-4 w-4" />
      </button>
      <button class="sp-control px-2.5 py-1.5 text-sm" @click="goToday">Today</button>
      <h2 class="sp-display ml-2 min-w-0 truncate text-[15px] font-semibold sp-ink-1">{{ monthLabel }}</h2>

      <!-- unscheduled tray toggle -->
      <button
        v-if="unscheduled.length"
        class="sp-control ml-auto flex items-center gap-1.5 px-2.5 py-1.5 text-sm"
        :class="trayOpen ? 'sp-control-active' : ''"
        @click="trayOpen = !trayOpen"
      >
        <LucideCalendarOff class="h-4 w-4" />
        No date
        <span class="rounded-full bg-[var(--sp-fill-strong)] px-1.5 text-xs sp-tnum">{{ unscheduled.length }}</span>
      </button>
    </div>

    <!-- unscheduled tray: drag a card onto a day to schedule it -->
    <div v-if="trayOpen && unscheduled.length" class="mb-3 rounded-xl border sp-hair bg-[var(--sp-fill)] p-2">
      <p class="mb-1.5 px-1 text-[11px] font-semibold uppercase tracking-wider sp-ink-3">
        Drag onto a day to schedule
      </p>
      <draggable
        v-model="tray"
        :group="{ name: 'cal-cards' }"
        item-key="name"
        ghost-class="sp-ghost"
        v-bind="touchDragOptions"
        class="flex flex-wrap gap-1.5"
        @change="(e) => onChange(e, null)"
      >
        <template #item="{ element }">
          <button
            class="flex max-w-[220px] cursor-grab items-center gap-1.5 rounded-lg bg-[var(--sp-surface)] px-2 py-1 text-xs shadow-[var(--sp-e1)] ring-1 ring-[color:var(--sp-line)] active:cursor-grabbing"
            @click="$emit('openCard', element.name)"
          >
            <span v-if="badgeField && element[badgeField]" class="h-1.5 w-1.5 shrink-0 rounded-full" :style="{ background: colorFor(element[badgeField]) }" />
            <span class="truncate text-ink-gray-8">{{ element[titleField] || 'Untitled' }}</span>
          </button>
        </template>
      </draggable>
    </div>

    <!-- weekday header -->
    <div class="grid grid-cols-7 gap-px px-px pb-1.5">
      <div v-for="d in WEEKDAYS" :key="d" class="px-2 text-[11px] font-semibold uppercase tracking-wider sp-ink-3">
        {{ d }}
      </div>
    </div>

    <!-- month grid -->
    <div
      class="grid min-h-0 flex-1 grid-cols-7 gap-px overflow-hidden rounded-2xl bg-[color:var(--sp-line)] ring-1 ring-[color:var(--sp-line)]"
      :style="{ gridTemplateRows: `repeat(${days.length / 7}, minmax(${breakpoint.isMobile ? '3.25rem' : '0'}, 1fr))` }"
    >
      <div
        v-for="day in days"
        :key="day.date"
        class="group/day flex min-h-0 flex-col sp-surface p-1"
        :class="day.inMonth ? '' : 'opacity-45'"
        @click="openDaySheet(day)"
      >
        <div class="flex items-center justify-between px-1 pb-0.5">
          <span
            class="flex h-5 w-5 items-center justify-center rounded-full text-xs sp-tnum"
            :class="day.isToday ? 'bg-[color:var(--sp-accent)] font-semibold text-white' : 'sp-ink-3'"
          >
            {{ day.dayNum }}
          </span>
          <button
            v-if="allowNewCard"
            class="sp-reveal rounded p-0.5 text-ink-gray-4 opacity-0 transition hover:bg-[var(--sp-fill-hover)] hover:text-ink-gray-8 group-hover/day:opacity-100"
            :aria-label="`New task on ${day.date}`"
            @click.stop="$emit('newCard', day.date)"
          >
            <LucidePlus class="h-3.5 w-3.5" />
          </button>
        </div>
        <!-- phones: cell shows a count pill; tap opens the day sheet -->
        <span
          v-if="day.cards.length"
          class="mx-auto mt-0.5 rounded-full bg-[var(--sp-fill-strong)] px-1.5 py-0.5 text-[11px] font-medium sp-ink-2 sp-tnum md:hidden"
        >
          {{ day.cards.length }}
        </span>
        <draggable
          v-model="day.cards"
          :group="{ name: 'cal-cards' }"
          item-key="name"
          ghost-class="sp-ghost"
          v-bind="touchDragOptions"
          class="sp-scroll flex min-h-[8px] flex-1 flex-col gap-1 overflow-y-auto max-md:hidden"
          @change="(e) => onChange(e, day)"
        >
          <template #item="{ element }">
            <button
              class="flex w-full cursor-grab items-center gap-1.5 rounded-lg bg-[var(--sp-fill)] px-1.5 py-1 text-left text-xs transition hover:bg-[var(--sp-fill-hover)] active:cursor-grabbing"
              :class="day.isPast && !day.isToday ? 'text-ink-red-3' : 'text-ink-gray-8'"
              :title="element[titleField]"
              @click="$emit('openCard', element.name)"
            >
              <span
                v-if="badgeField && element[badgeField]"
                class="h-1.5 w-1.5 shrink-0 rounded-full"
                :style="{ background: colorFor(element[badgeField]) }"
              />
              <span class="min-w-0 flex-1 truncate">{{ element[titleField] || 'Untitled' }}</span>
              <UserAvatar
                v-if="assigneeField && element[assigneeField]"
                :user="element[assigneeField]"
                size="xs"
                class="shrink-0"
              />
            </button>
          </template>
        </draggable>
      </div>
    </div>

    <!-- phones: a tapped day's cards in a bottom sheet -->
    <BottomSheet v-if="daySheet" :title="daySheetLabel" @close="daySheet = null">
      <button
        v-for="element in daySheet.cards"
        :key="element.name"
        class="flex w-full items-center gap-2 rounded-[10px] px-3 py-2.5 text-left text-sm transition hover:bg-[var(--sp-fill)]"
        @click="openFromSheet(element)"
      >
        <span
          v-if="badgeField && element[badgeField]"
          class="h-2 w-2 shrink-0 rounded-full"
          :style="{ background: colorFor(element[badgeField]) }"
        />
        <span class="min-w-0 flex-1 truncate text-ink-gray-8">{{ element[titleField] || 'Untitled' }}</span>
        <UserAvatar
          v-if="assigneeField && element[assigneeField]"
          :user="element[assigneeField]"
          size="xs"
          class="shrink-0"
        />
      </button>
      <template v-if="allowNewCard" #footer>
        <button
          class="flex w-full items-center justify-center gap-1.5 rounded-[10px] bg-[var(--sp-fill)] px-3 py-2 text-sm font-medium sp-ink-1 transition hover:bg-[var(--sp-fill-hover)]"
          @click="newFromSheet"
        >
          <LucidePlus class="h-4 w-4" /> New task
        </button>
      </template>
    </BottomSheet>
  </div>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import draggable from 'vuedraggable'
import UserAvatar from '@/components/UserAvatar.vue'
import BottomSheet from '@/components/BottomSheet.vue'
import { colorFor } from '@/lib/board'
import { touchDragOptions } from '@/lib/dnd'
import { breakpoint } from '@/composables/useBreakpoint'
import { ensureUsers } from '@/lib/users'

const props = defineProps({
  cards: { type: Array, default: () => [] },
  dueField: { type: String, required: true },
  titleField: { type: String, default: 'title' },
  badgeField: String,
  assigneeField: String,
  allowNewCard: { type: Boolean, default: true },
})
const emit = defineEmits(['openCard', 'newCard', 'reschedule'])

ensureUsers()

const WEEKDAYS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']

function ymd(d) {
  const y = d.getFullYear()
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${y}-${m}-${day}`
}

const anchor = ref(new Date()) // any date inside the shown month
function shiftMonth(delta) {
  const d = new Date(anchor.value)
  d.setDate(1)
  d.setMonth(d.getMonth() + delta)
  anchor.value = d
}
function goToday() {
  anchor.value = new Date()
}
const monthLabel = computed(() =>
  anchor.value.toLocaleDateString('en-US', { month: 'long', year: 'numeric' }),
)

// days is a ref (not a computed) because vuedraggable v-model mutates
// day.cards in place — same pattern BoardView uses for its columns.
const days = ref([])
const tray = ref([])
const trayOpen = ref(false)
const unscheduled = computed(() => props.cards.filter((c) => !c[props.dueField]))

function rebuild() {
  const todayStr = ymd(new Date())
  const first = new Date(anchor.value)
  first.setDate(1)
  const month = first.getMonth()
  // back up to Monday
  const start = new Date(first)
  start.setDate(start.getDate() - ((start.getDay() + 6) % 7))
  const byDate = {}
  for (const c of props.cards) {
    const d = c[props.dueField]
    if (d) (byDate[String(d).slice(0, 10)] = byDate[String(d).slice(0, 10)] || []).push(c)
  }
  const out = []
  const cur = new Date(start)
  // 6 weeks covers every month layout; trim trailing out-of-month weeks
  for (let i = 0; i < 42; i++) {
    const date = ymd(cur)
    out.push({
      date,
      dayNum: cur.getDate(),
      inMonth: cur.getMonth() === month,
      isToday: date === todayStr,
      isPast: date < todayStr,
      cards: byDate[date] || [],
    })
    cur.setDate(cur.getDate() + 1)
  }
  while (out.length > 7 && out.slice(-7).every((d) => !d.inMonth)) out.splice(-7)
  days.value = out
  tray.value = unscheduled.value
}
watch([() => props.cards, anchor, () => props.dueField], rebuild, { immediate: true, deep: false })

function onChange(evt, day) {
  const element = evt.added?.element
  if (!element) return // ignore removals/moves-within-day
  emit('reschedule', { name: element.name, due: day ? day.date : null })
}

// ---- mobile day sheet -----------------------------------------------------
const daySheet = ref(null)
const daySheetLabel = computed(() => {
  if (!daySheet.value) return ''
  const [y, m, d] = daySheet.value.date.split('-').map(Number)
  return new Date(y, m - 1, d).toLocaleDateString('en-US', {
    weekday: 'long', month: 'long', day: 'numeric',
  })
})
function openDaySheet(day) {
  if (!breakpoint.isMobile || (!day.cards.length && !props.allowNewCard)) return
  daySheet.value = day
}
function openFromSheet(card) {
  daySheet.value = null
  emit('openCard', card.name)
}
function newFromSheet() {
  const date = daySheet.value?.date
  daySheet.value = null
  if (date) emit('newCard', date)
}
</script>
