<template>
  <article
    class="sp-card group relative cursor-pointer p-3"
    :class="selected ? 'ring-2 ring-[color:var(--sp-accent)] ring-offset-1' : ''"
  >
    <!-- select checkbox (appears on hover / when selected) -->
    <button
      aria-label="Select task"
      :aria-pressed="selected"
      class="sp-reveal absolute right-2 top-2 flex h-4 w-4 items-center justify-center rounded border transition max-md:h-5 max-md:w-5"
      :class="
        selected
          ? 'border-transparent bg-[color:var(--sp-accent)] text-white opacity-100'
          : 'border-[rgb(var(--sp-ink)/0.25)] bg-[var(--sp-surface)] text-transparent opacity-0 hover:border-[rgb(var(--sp-ink)/0.45)] group-hover:opacity-100'
      "
      @click.stop="$emit('toggle')"
    >
      <LucideCheck class="h-3 w-3" />
    </button>

    <!-- parent context (when this card is a subtask) -->
    <button
      v-if="parentName"
      class="mb-1 flex max-w-full items-center gap-1 rounded bg-surface-gray-2 px-1.5 py-0.5 text-[11px] text-ink-gray-5 transition hover:bg-surface-gray-3 hover:text-ink-gray-7"
      :title="`Go to parent: ${parentTitle || parentName}`"
      @click.stop="$emit('open-parent')"
    >
      <LucideCornerLeftUp class="h-3 w-3 shrink-0" />
      <span class="truncate">{{ parentTitle || parentName }}</span>
    </button>

    <p class="pr-5 text-sm font-medium leading-snug text-ink-gray-8" style="letter-spacing: -0.012em">
      {{ card[titleField] || 'Untitled' }}
    </p>

    <!-- tag chips -->
    <div v-if="chips.length" class="mt-2 flex flex-wrap gap-1">
      <span v-for="(c, i) in chips" :key="i" class="rounded-md bg-[var(--sp-fill)] px-1.5 py-0.5 text-[11px] font-medium text-ink-gray-6">
        {{ c }}
      </span>
    </div>

    <div v-if="hasMeta" class="mt-2.5 flex flex-wrap items-center gap-x-2 gap-y-1.5">
      <span v-if="badgeValue" class="flex items-center gap-1 text-xs text-ink-gray-6">
        <span class="h-2 w-2 rounded-full" :style="{ background: badgeColor }" />
        {{ badgeValue }}
      </span>
      <span
        v-if="card.due_date"
        class="flex items-center gap-1 rounded-md px-1.5 py-0.5 text-xs font-medium"
        :class="overdue ? 'bg-surface-red-1 text-ink-red-3' : 'bg-[var(--sp-fill)] text-ink-gray-6'"
      >
        <LucideCalendar class="h-3 w-3" />
        {{ formattedDue }}
      </span>
      <span v-if="subtaskCount" class="flex items-center gap-0.5 text-xs text-ink-gray-5">
        <LucideListChecks class="h-3.5 w-3.5" />
        {{ subtaskCount }}
      </span>
      <div v-if="assignee" class="ml-auto">
        <UserAvatar :user="assignee" size="sm" />
      </div>
    </div>
  </article>
</template>

<script setup>
import { computed, onMounted } from 'vue'
import UserAvatar from '@/components/UserAvatar.vue'
import { ensureUsers } from '@/lib/users'
import { colorFor } from '@/lib/board'
import { formatDate } from '@/lib/format'

onMounted(ensureUsers)

const props = defineProps({
  card: { type: Object, required: true },
  titleField: { type: String, default: 'title' },
  assigneeField: String,
  badgeField: String,
  chipFields: { type: Array, default: () => [] },
  parentName: String,
  parentTitle: String,
  subtaskCount: { type: Number, default: 0 },
  selected: Boolean,
})
defineEmits(['toggle', 'open-parent'])

const chips = computed(() =>
  props.chipFields.flatMap((f) =>
    String(props.card[f] || '').split(',').map((c) => c.trim()).filter(Boolean),
  ),
)

const badgeValue = computed(() => props.badgeField && props.card[props.badgeField])
const badgeColor = computed(() => colorFor(badgeValue.value))
const assignee = computed(() => props.assigneeField && props.card[props.assigneeField])
const hasMeta = computed(
  () => badgeValue.value || props.card.due_date || props.subtaskCount || assignee.value,
)
const overdue = computed(() => {
  if (!props.card.due_date) return false
  return new Date(props.card.due_date) < new Date(new Date().toDateString())
})
const formattedDue = computed(() => formatDate(props.card.due_date))
</script>
