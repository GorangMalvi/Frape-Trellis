<template>
  <div class="sp-scroll h-full overflow-auto px-3 py-3 md:px-5 md:py-4">
    <div :style="{ minWidth: tableMinWidth + 'px' }">
      <!-- column header (scrolls with the list) -->
      <div
        class="grid items-center gap-3 px-4 pb-2.5 pt-1 text-[11px] font-semibold uppercase tracking-wider sp-ink-3"
        :style="gridStyle"
      >
        <div class="min-w-0 truncate">Name</div>
        <div class="min-w-0 truncate">Bucket</div>
        <div v-for="col in columns" :key="col.fieldname" class="min-w-0 truncate">{{ col.label }}</div>
      </div>

      <!-- groups -->
      <section v-for="group in groups" :key="group.key" class="mb-5">
        <!-- group header -->
        <button class="mb-2 flex w-full items-center gap-2 px-1 text-left" @click="toggle(group.key)">
          <LucideChevronRight
            class="h-3.5 w-3.5 sp-ink-3 transition-transform"
            :class="{ 'rotate-90': !collapsed[group.key] }"
          />
          <UserAvatar v-if="isUserGroup && group.key !== '__none__'" :user="group.key" size="sm" />
          <span v-else class="h-2.5 w-2.5 rounded-full" :style="{ background: group.color || '#9ca3af' }" />
          <span class="text-sm font-semibold sp-ink-1">{{ groupLabel(group) }}</span>
          <span class="rounded-full bg-[var(--sp-fill)] px-2 py-0.5 text-xs font-medium sp-ink-3 sp-tnum">
            {{ group.cards.length }}
          </span>
        </button>

        <!-- rows: one rounded, inset card per group -->
        <div
          v-if="!collapsed[group.key]"
          class="overflow-hidden rounded-2xl sp-surface shadow-[var(--sp-e1)] ring-1 ring-[color:var(--sp-line)]"
        >
          <div
            v-for="(card, ri) in visibleCards(group)"
            :key="card.name"
            class="group/row grid items-center gap-3 px-4 py-2.5 text-sm transition"
            :class="[
              ri ? 'border-t sp-hair' : '',
              selected.includes(card.name) ? 'bg-[var(--sp-accent-tint)]' : 'hover:bg-[var(--sp-fill)]',
            ]"
            :style="gridStyle"
          >
            <!-- name (opens drawer) -->
            <div class="flex min-w-0 cursor-pointer items-center gap-2.5" @click="$emit('openCard', card.name)">
              <button
                aria-label="Select task"
                :aria-pressed="selected.includes(card.name)"
                class="sp-reveal flex h-4 w-4 shrink-0 items-center justify-center rounded-md border transition max-md:h-5 max-md:w-5"
                :class="
                  selected.includes(card.name)
                    ? 'border-transparent bg-[color:var(--sp-accent)] text-white opacity-100'
                    : 'border-[rgb(var(--sp-ink)/0.25)] text-transparent opacity-0 hover:border-[rgb(var(--sp-ink)/0.45)] group-hover/row:opacity-100'
                "
                @click.stop="$emit('toggleSelect', card.name)"
              >
                <LucideCheck class="h-3 w-3" />
              </button>
              <span
                v-if="badgeField && card[badgeField]"
                class="h-2 w-2 shrink-0 rounded-full"
                :style="{ background: colorFor(card[badgeField]) }"
              />
              <span class="truncate font-medium text-ink-gray-8">{{ card[titleField] || 'Untitled' }}</span>
              <span v-if="subtaskCount(card)" class="flex shrink-0 items-center gap-0.5 text-xs sp-ink-3">
                <LucideListChecks class="h-3.5 w-3.5" />{{ subtaskCount(card) }}
              </span>
            </div>

            <!-- bucket: click the chip to move the card to another bucket -->
            <div class="min-w-0" @click.stop>
              <select
                v-if="bucketEditing === card.name"
                v-focus
                class="sp-field w-full"
                :value="card[bucketField] || ''"
                @change="commitBucket(card, $event.target.value)"
                @blur="bucketEditing = null"
              >
                <option value="">— None —</option>
                <option v-for="b in buckets" :key="b.name" :value="b.name">{{ b.bucket_name }}</option>
              </select>
              <button
                v-else
                class="flex max-w-full items-center gap-1.5 rounded-md px-1.5 py-1 transition hover:bg-[var(--sp-fill-strong)]"
                @click="bucketEditing = card.name"
              >
                <span class="h-2 w-2 shrink-0 rounded-full" :style="{ background: bucketColor(card[bucketField]) }" />
                <span class="truncate text-xs text-ink-gray-7">{{ bucketName(card[bucketField]) || '—' }}</span>
                <LucideChevronDown class="h-3 w-3 shrink-0 sp-ink-4" />
              </button>
            </div>

            <!-- editable columns -->
            <div v-for="col in columns" :key="col.fieldname" class="min-w-0" @click.stop>
              <!-- editing -->
              <template v-if="isEditing(card, col)">
                <select
                  v-if="col.fieldtype === 'Select'"
                  v-focus
                  class="sp-field w-full"
                  @change="commit(card, col, $event.target.value)"
                  @blur="cancel"
                >
                  <option value="">—</option>
                  <option
                    v-for="o in (col.options || '').split('\n').filter(Boolean)"
                    :key="o"
                    :value="o"
                    :selected="card[col.fieldname] === o"
                  >
                    {{ o }}
                  </option>
                </select>
                <input
                  v-else-if="col.fieldtype === 'Date'"
                  v-focus
                  type="date"
                  :value="card[col.fieldname]"
                  class="sp-field w-full"
                  @change="commit(card, col, $event.target.value)"
                  @blur="cancel"
                />
                <LinkField
                  v-else-if="col.fieldtype === 'Link'"
                  :doctype="col.options"
                  :model-value="card[col.fieldname]"
                  @update:model-value="(v) => commit(card, col, v)"
                />
                <div
                  v-else-if="col.fieldtype === 'Duration'"
                  @focusout="onFieldBlur($event, card, col)"
                >
                  <DurationField
                    :model-value="card[col.fieldname] || 0"
                    @update:model-value="(v) => (card[col.fieldname] = v)"
                  />
                </div>
                <input
                  v-else-if="isNumber(col)"
                  v-focus
                  type="number"
                  :value="card[col.fieldname]"
                  class="sp-field w-full"
                  @keyup.enter="commit(card, col, $event.target.value)"
                  @keyup.esc="cancel"
                  @blur="commit(card, col, $event.target.value)"
                />
                <input
                  v-else
                  v-focus
                  type="text"
                  :value="card[col.fieldname]"
                  :placeholder="chipFields.includes(col.fieldname) ? 'tag, tag, …' : ''"
                  class="sp-field w-full"
                  @keyup.enter="commit(card, col, $event.target.value)"
                  @keyup.esc="cancel"
                  @blur="commit(card, col, $event.target.value)"
                />
              </template>

              <!-- display -->
              <div
                v-else
                class="truncate"
                :class="editable(col) ? 'cursor-pointer rounded-md px-1.5 py-1 hover:bg-[var(--sp-fill-strong)]' : ''"
                @click="editable(col) && startEdit(card, col)"
              >
                <input
                  v-if="col.fieldtype === 'Check'"
                  type="checkbox"
                  class="h-4 w-4 cursor-pointer rounded accent-[color:var(--sp-accent)]"
                  :checked="!!Number(card[col.fieldname])"
                  @change="commitDirect(card, col, $event.target.checked ? 1 : 0)"
                />
                <span v-else-if="isUser(col) && card[col.fieldname]" class="flex items-center gap-1.5">
                  <UserAvatar :user="card[col.fieldname]" size="sm" />
                  <span class="truncate text-xs text-ink-gray-7">{{ userLabel(card[col.fieldname]) }}</span>
                </span>
                <span
                  v-else-if="col.fieldname === badgeField && card[col.fieldname]"
                  class="flex items-center gap-1.5 text-xs text-ink-gray-7"
                >
                  <span class="h-2 w-2 rounded-full" :style="{ background: colorFor(card[col.fieldname]) }" />
                  {{ card[col.fieldname] }}
                </span>
                <span v-else-if="col.fieldtype === 'Date' && card[col.fieldname]" class="text-xs text-ink-gray-6">
                  {{ formatDate(card[col.fieldname]) }}
                </span>
                <span v-else-if="col.fieldtype === 'Duration' && card[col.fieldname]" class="text-xs text-ink-gray-7">
                  {{ formatDuration(card[col.fieldname]) }}
                </span>
                <span v-else-if="chipFields.includes(col.fieldname) && card[col.fieldname]" class="flex flex-wrap gap-1">
                  <span v-for="(c, ci) in cardChips(card[col.fieldname])" :key="ci" class="rounded-md bg-[var(--sp-fill)] px-1.5 py-0.5 text-[11px] font-medium text-ink-gray-6">{{ c }}</span>
                </span>
                <span v-else-if="col.fieldtype === 'Percent' && card[col.fieldname] != null && card[col.fieldname] !== ''" class="text-xs text-ink-gray-7 sp-tnum">{{ card[col.fieldname] }}%</span>
                <span v-else-if="card[col.fieldname] != null && card[col.fieldname] !== ''" class="text-xs text-ink-gray-7" :class="{ 'sp-tnum': isNumber(col) }">{{ card[col.fieldname] }}</span>
                <span v-else class="sp-ink-4">—</span>
              </div>
            </div>
          </div>

          <!-- reveal more rows in big groups (keeps the DOM bounded) -->
          <button
            v-if="moreCount(group)"
            class="flex w-full items-center justify-center gap-1.5 border-t sp-hair px-4 py-2 text-xs font-medium sp-ink-3 transition hover:bg-[var(--sp-fill)] hover:text-ink-gray-8"
            @click="showMore(group)"
          >
            <LucideChevronDown class="h-3.5 w-3.5" />
            Show {{ Math.min(PAGE, moreCount(group)) }} more
            <span class="sp-ink-4">· {{ moreCount(group) }} hidden</span>
          </button>

          <!-- group totals: generic aggregate per column, by field type -->
          <div
            v-if="hasTotals(group)"
            class="grid items-center gap-3 border-t border-[color:var(--sp-line)] bg-[var(--sp-fill)] px-4 py-2 text-xs"
            :style="gridStyle"
          >
            <div class="font-semibold sp-ink-3">Total</div>
            <div />
            <div v-for="col in columns" :key="col.fieldname" class="truncate font-semibold text-ink-gray-8 sp-tnum">
              {{ aggregate(col, group.cards) || '' }}
            </div>
          </div>

          <button
            v-if="allowNewCard && group.key !== '__none__'"
            class="flex w-full items-center gap-1.5 border-t sp-hair px-4 py-2.5 text-sm sp-ink-3 transition hover:bg-[var(--sp-fill)] hover:text-ink-gray-7"
            @click="$emit('newCard', group.key)"
          >
            <LucidePlus class="h-3.5 w-3.5" /> Add task
          </button>
        </div>
      </section>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import LinkField from '@/components/LinkField.vue'
import UserAvatar from '@/components/UserAvatar.vue'
import DurationField from '@/components/DurationField.vue'
import { colorFor } from '@/lib/board'
import { ensureUsers, userLabel } from '@/lib/users'
import { formatDate, formatDuration, formatNumber, splitChips } from '@/lib/format'
import { breakpoint } from '@/composables/useBreakpoint'
import { vFocus } from '@/lib/directives'

const props = defineProps({
  groups: Array,
  columns: { type: Array, default: () => [] },
  titleField: String,
  badgeField: String,
  chipFields: { type: Array, default: () => [] },
  subtaskCount: { type: Function, default: () => 0 },
  selected: { type: Array, default: () => [] },
  groupField: { type: Object, default: null },
  buckets: { type: Array, default: () => [] },
  bucketField: { type: String, default: 'bucket' },
  allowNewCard: { type: Boolean, default: true },
})
const emit = defineEmits(['openCard', 'newCard', 'edit', 'toggleSelect'])

onMounted(ensureUsers)

const collapsed = reactive({})
const editing = reactive({ name: null, field: null })
const bucketEditing = ref(null)

// render rows in pages so huge groups don't flood the DOM
const PAGE = 50
const shown = reactive({})
function shownFor(group) {
  return shown[group.key] || PAGE
}
function visibleCards(group) {
  return group.cards.length > shownFor(group) ? group.cards.slice(0, shownFor(group)) : group.cards
}
function moreCount(group) {
  return Math.max(0, group.cards.length - shownFor(group))
}
function showMore(group) {
  shown[group.key] = shownFor(group) + PAGE
}

const bucketMap = computed(() => {
  const m = {}
  for (const b of props.buckets) m[b.name] = b
  return m
})
function bucketName(id) {
  return bucketMap.value[id]?.bucket_name || ''
}
function bucketColor(id) {
  return bucketMap.value[id]?.color || '#9ca3af'
}
function commitBucket(card, value) {
  card[props.bucketField] = value === '' ? null : value
  emit('edit', { name: card.name, field: props.bucketField, value: card[props.bucketField] })
  bucketEditing.value = null
}

const isUserGroup = computed(
  () => props.groupField?.fieldtype === 'Link' && props.groupField?.options === 'User',
)
function groupLabel(group) {
  if (group.key === '__none__') return isUserGroup.value ? 'Unassigned' : group.label
  return isUserGroup.value ? userLabel(group.key) : group.label
}

// Name flexes (the only fr track); Bucket + property columns are fixed width so
// every independent grid (header, each row, totals) shares identical tracks and
// total width — they stay aligned and span fully even when the table scrolls.
// Phones get narrower tracks so less horizontal scrolling is needed.
const nameMin = computed(() => (breakpoint.isMobile ? 190 : 240))
const colWidth = computed(() => (breakpoint.isMobile ? 130 : 150))
const gridStyle = computed(() => ({
  gridTemplateColumns: `minmax(${nameMin.value}px, 2fr) ${colWidth.value}px repeat(${props.columns.length}, ${colWidth.value}px)`,
}))

// The wrapper must be at least as wide as the grid actually needs: row padding +
// inter-track gaps + name's min floor + bucket + every property column.
// Without this, the wrapper only fills the viewport, so when the columns overflow
// the un-clipped header spans the full grid while the rounded, overflow-hidden
// group cards clip the trailing columns — making the rows look narrower than the
// header. Growing the wrapper lets the whole table scroll as one aligned unit.
const GAP = 12 // gap-3
const PAD = 32 // px-4 both sides
const tableMinWidth = computed(() => {
  const cols = props.columns.length
  const tracks = 2 + cols // name + bucket + property columns
  const width = PAD + (tracks - 1) * GAP + nameMin.value + colWidth.value + cols * colWidth.value
  return Math.max(breakpoint.isMobile ? 560 : 760, width)
})

function toggle(key) {
  collapsed[key] = !collapsed[key]
}

// ---- inline editing -------------------------------------------------------
const NUMBER_TYPES = ['Int', 'Float', 'Currency', 'Percent']
function isNumber(col) {
  return NUMBER_TYPES.includes(col.fieldtype)
}
function editable(col) {
  if (col.fieldtype === 'Check') return false // toggled directly, no edit mode
  if (props.chipFields.includes(col.fieldname)) return true
  return [
    'Select', 'Link', 'Date', 'Duration', 'Int', 'Float', 'Currency',
    'Percent', 'Data', 'Small Text', 'Long Text', 'Text',
  ].includes(col.fieldtype)
}
function isEditing(card, col) {
  return editing.name === card.name && editing.field === col.fieldname
}
function startEdit(card, col) {
  editing.name = card.name
  editing.field = col.fieldname
}
function cancel() {
  editing.name = null
  editing.field = null
}
function commit(card, col, value) {
  // guard against the second of enter+blur firing twice
  if (editing.name !== card.name || editing.field !== col.fieldname) return
  card[col.fieldname] = value === '' ? null : value
  emit('edit', { name: card.name, field: col.fieldname, value: card[col.fieldname] })
  cancel()
}
// for controls that commit without an edit-mode (checkboxes)
function commitDirect(card, col, value) {
  card[col.fieldname] = value
  emit('edit', { name: card.name, field: col.fieldname, value })
}
// commit a multi-input field (e.g. Duration) only once focus leaves it entirely
function onFieldBlur(e, card, col) {
  if (e.currentTarget.contains(e.relatedTarget)) return
  commit(card, col, card[col.fieldname])
}

// ---- generic per-group aggregates -----------------------------------------
// Picks an aggregation by field type: sum for durations/numbers (and
// numeric-valued selects like Sprint Points), average for percent, and a
// checked-count for checkboxes. Other types have no meaningful total.
function isNumericValued(col, cards) {
  let any = false
  for (const c of cards) {
    const v = c[col.fieldname]
    if (v == null || v === '') continue
    any = true
    if (Number.isNaN(Number(v))) return false
  }
  return any
}
function aggregate(col, cards) {
  const ft = col.fieldtype
  if (ft === 'Duration') {
    const sum = cards.reduce((s, c) => s + (Number(c[col.fieldname]) || 0), 0)
    return sum ? formatDuration(sum) : null
  }
  if (NUMBER_TYPES.includes(ft)) {
    const vals = cards.map((c) => c[col.fieldname]).filter((v) => v != null && v !== '')
    if (!vals.length) return null
    const sum = vals.reduce((s, v) => s + (Number(v) || 0), 0)
    if (ft === 'Percent') return Math.round(sum / vals.length) + '%'
    return formatNumber(sum)
  }
  if (ft === 'Check') {
    const checked = cards.reduce((s, c) => s + (Number(c[col.fieldname]) ? 1 : 0), 0)
    return `${checked}/${cards.length}`
  }
  // numeric-valued Select / Data (e.g. Sprint Points)
  if ((ft === 'Select' || ft === 'Data') && isNumericValued(col, cards)) {
    const sum = cards.reduce((s, c) => s + (Number(c[col.fieldname]) || 0), 0)
    return formatNumber(sum)
  }
  return null
}
function hasTotals(group) {
  return props.columns.some((col) => aggregate(col, group.cards))
}

function isUser(col) {
  return col.fieldtype === 'Link' && col.options === 'User'
}
const cardChips = splitChips
</script>
