<template>
  <div
    class="sp-scroll flex h-full items-start gap-3 overflow-x-auto p-3 md:gap-4 md:p-5"
    :class="!dragging ? 'max-md:snap-x max-md:snap-mandatory max-md:scroll-p-3' : ''"
  >
    <!-- reorderable bucket columns -->
    <draggable
      v-model="cols"
      :group="{ name: 'columns' }"
      item-key="key"
      handle=".col-grip"
      :disabled="!bucketMode"
      :animation="160"
      v-bind="touchDragOptions"
      class="flex h-full items-start gap-3 md:gap-4"
      @start="dragging = true"
      @end="dragging = false; emitReorder()"
    >
      <template #item="{ element: group }">
        <section class="sp-col group/col relative flex max-h-full w-[85vw] max-w-xs shrink-0 snap-start flex-col md:w-72 md:max-w-none">
          <!-- colour cap: each bucket's identity colour -->
          <div class="h-1 shrink-0 rounded-t-[18px]" :style="{ background: group.color || '#9ca3af' }" />
          <div class="flex items-center justify-between px-3 pb-2.5 pt-2" :class="bucketMode ? 'col-grip cursor-grab active:cursor-grabbing' : ''">
            <div class="flex min-w-0 items-center gap-2">
              <button
                class="h-2.5 w-2.5 shrink-0 rounded-full ring-offset-1"
                :class="bucketMode ? 'hover:ring-2 hover:ring-[rgb(var(--sp-ink)/0.25)]' : 'pointer-events-none'"
                :style="{ background: group.color || '#9ca3af' }"
                @click.stop="bucketMode && (colorOpen = colorOpen === group.key ? null : group.key)"
              />
              <input
                v-if="editing === group.key"
                v-model="editName"
                v-focus
                class="min-w-0 rounded bg-surface-white px-1 text-sm font-semibold text-ink-gray-8 focus:outline-none"
                @click.stop
                @keyup.enter="commitRename(group)"
                @blur="commitRename(group)"
              />
              <span
                v-else
                class="truncate text-sm font-semibold text-ink-gray-8"
                :class="bucketMode ? 'cursor-text' : ''"
                @click.stop="bucketMode && startRename(group)"
              >
                {{ group.label }}
              </span>
              <span
                class="rounded px-1.5 text-xs sp-tnum"
                :class="overWip(group) ? 'bg-surface-red-1 font-medium text-ink-red-3' : 'text-ink-gray-5'"
              >
                {{ group.cards.length }}<template v-if="group.wip">/{{ group.wip }}</template>
              </span>
            </div>
            <button
              v-if="bucketMode"
              class="sp-reveal rounded p-0.5 text-ink-gray-4 opacity-0 transition hover:bg-[var(--sp-fill-hover)] hover:text-ink-red-3 group-hover/col:opacity-100"
              title="Delete bucket"
              aria-label="Delete bucket"
              @click.stop="$emit('deleteBucket', group)"
            >
              <LucideTrash2 class="h-3.5 w-3.5" />
            </button>

            <!-- color swatch popover -->
            <div v-if="colorOpen === group.key" class="sp-pop absolute z-30 mt-7 grid w-[188px] grid-cols-6 gap-2 p-2.5" @click.stop>
              <button
                v-for="c in COLORS"
                :key="c"
                class="sp-swatch h-5 w-5"
                :class="(group.color || '').toLowerCase() === c ? 'sp-swatch-active' : ''"
                :style="{ background: c, color: c }"
                @click="pickColor(group, c)"
              />
            </div>
          </div>

          <draggable
            v-model="group.winCards"
            :group="{ name: 'cards' }"
            item-key="name"
            ghost-class="sp-ghost"
            drag-class="sp-drag"
            :animation="160"
            v-bind="touchDragOptions"
            class="sp-scroll flex min-h-[12px] flex-1 flex-col gap-2 overflow-y-auto px-2 pb-1"
            @start="dragging = true"
            @end="dragging = false"
            @change="(e) => onChange(e, group)"
          >
            <template #item="{ element }">
              <div>
                <CardItem
                  :card="element"
                  :title-field="titleField"
                  :assignee-field="assigneeField"
                  :badge-field="badgeField"
                  :subtask-count="subtaskCount(element)"
                  :chip-fields="chipFields"
                  :parent-name="element[parentField]"
                  :parent-title="parentMap?.[element[parentField]]"
                  :selected="selected.includes(element.name)"
                  @click="$emit('openCard', element.name)"
                  @toggle="$emit('toggleSelect', element.name)"
                  @open-parent="$emit('openCard', element[parentField])"
                />
                <!-- nested subtasks (nested mode only) -->
                <div v-if="subtaskMode === 'nested' && (subtasksByParent?.[element.name] || []).length" class="mt-1 pl-2">
                  <button
                    class="flex items-center gap-1 px-1 py-0.5 text-xs text-ink-gray-5 hover:text-ink-gray-8"
                    @click.stop="toggleExpand(element.name)"
                  >
                    <LucideChevronRight class="h-3 w-3 transition-transform" :class="{ 'rotate-90': expanded.has(element.name) }" />
                    {{ subtasksByParent[element.name].length }} subtasks
                  </button>
                  <div v-if="expanded.has(element.name)" class="mt-1 flex flex-col gap-1 border-l border-outline-gray-2 pl-2">
                    <button
                      v-for="st in subtasksByParent[element.name]"
                      :key="st.name"
                      class="flex items-center gap-1.5 rounded px-1.5 py-1 text-left text-xs text-ink-gray-7 hover:bg-surface-gray-2"
                      @click.stop="$emit('openCard', st.name)"
                    >
                      <span class="h-1.5 w-1.5 shrink-0 rounded-full bg-ink-gray-4" />
                      <span class="truncate">{{ st[titleField] }}</span>
                    </button>
                  </div>
                </div>
              </div>
            </template>
          </draggable>

          <!-- reveal more cards in big columns (keeps the DOM bounded) -->
          <button
            v-if="moreCount(group)"
            class="mx-2 mb-1 flex items-center justify-center gap-1.5 rounded-md py-1.5 text-xs font-medium sp-ink-3 transition hover:bg-[var(--sp-fill)] hover:text-ink-gray-8"
            @click="showMore(group)"
          >
            <LucideChevronDown class="h-3.5 w-3.5" />
            Show {{ Math.min(PAGE, moreCount(group)) }} more
            <span class="sp-ink-4">· {{ moreCount(group) }} hidden</span>
          </button>

          <div v-if="allowNewCard && group.key !== '__none__'" class="p-2">
            <button
              class="flex w-full items-center gap-1.5 rounded-md px-2 py-1.5 text-sm sp-ink-3 transition hover:bg-[var(--sp-fill)] hover:text-ink-gray-7"
              @click="$emit('newCard', group.key)"
            >
              <LucidePlus class="h-3.5 w-3.5" /> Add task
            </button>
          </div>
        </section>
      </template>
    </draggable>

    <!-- unsorted lane (cards whose bucket was deleted) -->
    <section v-if="noneGroup" class="sp-col flex max-h-full w-[85vw] max-w-xs shrink-0 snap-start flex-col opacity-80 md:w-72 md:max-w-none">
      <div class="px-3 py-2.5 text-sm font-semibold text-ink-gray-6">{{ noneGroup.label }} · {{ noneGroup.cards.length }}</div>
      <draggable
        v-model="noneGroup.cards"
        :group="{ name: 'cards' }"
        item-key="name"
        v-bind="touchDragOptions"
        class="sp-scroll flex min-h-[12px] flex-1 flex-col gap-2 overflow-y-auto px-2 pb-2"
        @start="dragging = true"
        @end="dragging = false"
        @change="(e) => onChange(e, noneGroup)"
      >
        <template #item="{ element }">
          <CardItem
            :card="element"
            :title-field="titleField"
            :assignee-field="assigneeField"
            :badge-field="badgeField"
            :chip-fields="chipFields"
            :subtask-count="subtaskCount(element)"
            :parent-name="element[parentField]"
            :parent-title="parentMap?.[element[parentField]]"
            :selected="selected.includes(element.name)"
            @click="$emit('openCard', element.name)"
            @toggle="$emit('toggleSelect', element.name)"
            @open-parent="$emit('openCard', element[parentField])"
          />
        </template>
      </draggable>
    </section>

    <button
      v-if="bucketMode"
      class="flex h-9 shrink-0 items-center gap-1 rounded-lg px-3 text-sm sp-ink-3 transition hover:bg-[var(--sp-fill)] hover:text-ink-gray-7"
      @click="$emit('addBucket')"
    >
      <LucidePlus class="h-4 w-4" /> Add bucket
    </button>
  </div>
</template>

<script setup>
import { computed, reactive, ref, watch } from 'vue'
import draggable from 'vuedraggable'
import CardItem from '@/components/CardItem.vue'
import { BUCKET_PALETTE } from '@/lib/board'
import { touchDragOptions } from '@/lib/dnd'
import { vFocus } from '@/lib/directives'

const props = defineProps({
  groups: Array,
  titleField: String,
  assigneeField: String,
  badgeField: String,
  chipFields: { type: Array, default: () => [] },
  parentField: String,
  parentMap: { type: Object, default: () => ({}) },
  subtaskMode: { type: String, default: 'separate' },
  subtasksByParent: { type: Object, default: () => ({}) },
  subtaskCount: { type: Function, default: () => 0 },
  selected: { type: Array, default: () => [] },
  bucketMode: { type: Boolean, default: true },
  allowNewCard: { type: Boolean, default: true },
})
const emit = defineEmits([
  'move', 'openCard', 'newCard', 'toggleSelect',
  'renameBucket', 'recolorBucket', 'deleteBucket', 'reorderBuckets', 'addBucket',
])

const COLORS = BUCKET_PALETTE

const editing = ref(null)
const editName = ref('')
const colorOpen = ref(null)
// scroll-snap fights SortableJS auto-scroll — suspend snapping mid-drag
const dragging = ref(false)
const expanded = ref(new Set())
function toggleExpand(name) {
  const s = new Set(expanded.value)
  s.has(name) ? s.delete(name) : s.add(name)
  expanded.value = s
}

// reorderable bucket columns (exclude the unsorted lane)
const cols = ref([])
const noneGroup = computed(() => props.groups.find((g) => g.key === '__none__'))

// big columns render only the first PAGE cards (winCards) with a "Show more"
// reveal, so a 1000-card space doesn't flood the DOM. Dropping at the very
// end of a windowed column lands relative to the last *visible* card — with
// manual ordering the card may settle within the hidden tail, which is the
// honest interpretation of that drop.
const PAGE = 30
const shown = reactive({})
function shownFor(g) {
  return shown[g.key] || PAGE
}
function moreCount(g) {
  return Math.max(0, g.cards.length - shownFor(g))
}
function showMore(g) {
  shown[g.key] = shownFor(g) + PAGE
  rebuildCols()
}
function rebuildCols() {
  cols.value = (props.groups || [])
    .filter((x) => x.key !== '__none__')
    .map((g) => ({ ...g, winCards: g.cards.length > shownFor(g) ? g.cards.slice(0, shownFor(g)) : g.cards }))
}
watch(
  () => (props.groups || []).map((g) => `${g.key}:${g.label}:${g.color}:${g.cards.length}`).join('|'),
  rebuildCols,
  { immediate: true, deep: false },
)

function overWip(group) {
  return group.wip && group.cards.length > group.wip
}
function onChange(evt, group) {
  const element = evt.added?.element || evt.moved?.element
  // neighbours for position math come from the windowed list when present
  if (element) emit('move', { element, group: { ...group, cards: group.winCards || group.cards } })
}
function startRename(group) {
  if (group.key === '__none__') return
  editing.value = group.key
  editName.value = group.label
}
function commitRename(group) {
  // Enter then blur both call this — only act on the first.
  if (editing.value !== group.key) return
  editing.value = null
  const name = (editName.value || '').trim()
  if (name && name !== group.label) emit('renameBucket', { group, bucket_name: name })
}
function pickColor(group, color) {
  colorOpen.value = null
  emit('recolorBucket', { group, color })
}
function emitReorder() {
  emit('reorderBuckets', cols.value.map((g) => g.key))
}
</script>
