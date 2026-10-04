<template>
  <div class="relative z-40 sp-glass-strong border-b sp-hair">
    <!-- row 1: view tabs -->
    <div class="sp-scroll flex items-center gap-1 overflow-x-auto px-4 pt-2">
      <button
        v-for="v in views"
        :key="v.key"
        class="group flex shrink-0 items-center gap-1.5 whitespace-nowrap border-b-2 px-3 py-2 text-sm transition"
        :class="
          v.key === activeKey
            ? 'border-[color:var(--sp-accent)] font-medium text-ink-gray-9'
            : 'border-transparent text-ink-gray-5 hover:text-ink-gray-8'
        "
        @click="$emit('select', v.key)"
      >
        <LucideLayoutGrid v-if="v.view_type === 'Board' || v.view_type === 'board'" class="h-4 w-4" />
        <LucideCalendar v-else-if="v.view_type === 'Calendar' || v.view_type === 'calendar'" class="h-4 w-4" />
        <LucideList v-else class="h-4 w-4" />
        {{ v.view_name }}
        <!-- shared (team) vs private indicator; click to toggle on your own views -->
        <template v-if="!v._builtin">
          <LucideUsers
            v-if="v.is_shared"
            class="h-3.5 w-3.5"
            :class="canToggle(v) ? 'sp-ink-3 hover:text-ink-gray-8' : 'sp-ink-4'"
            :title="canToggle(v) ? 'Shared with the team — click to make private' : 'Shared with the team'"
            @click.stop="canToggle(v) && $emit('toggle-share', v)"
          />
          <LucideLock
            v-else
            class="h-3.5 w-3.5 sp-ink-4 hover:text-ink-gray-8"
            title="Private to you — click to share"
            @click.stop="canToggle(v) && $emit('toggle-share', v)"
          />
        </template>
        <LucideX
          v-if="!v._builtin && v.key === activeKey"
          class="h-3 w-3 text-ink-gray-4 hover:text-ink-red-3"
          @click.stop="$emit('delete', v.name)"
        />
      </button>
      <button
        class="ml-1 flex shrink-0 items-center gap-1 whitespace-nowrap rounded-md px-2 py-1.5 text-sm text-ink-gray-5 hover:bg-surface-gray-2"
        @click="$emit('new')"
      >
        <LucidePlus class="h-4 w-4" /> View
      </button>

      <div class="ml-auto flex shrink-0 items-center gap-2 pb-1">
        <div class="sp-chip flex items-center gap-1 px-2 py-1">
          <LucideSearch class="h-4 w-4 sp-ink-3" />
          <input
            :value="search"
            placeholder="Search…"
            class="w-24 bg-transparent text-sm transition-[width] focus:outline-none focus:w-36 md:w-32"
            @input="$emit('search', $event.target.value)"
          />
        </div>
      </div>
    </div>

    <!-- row 2: controls (single scrollable strip on phones, wraps on desktop) -->
    <div class="sp-scroll flex items-center gap-2 px-4 py-2 max-md:overflow-x-auto md:flex-wrap">
      <!-- view type toggle -->
      <div class="sp-chip flex shrink-0 items-center gap-0.5 p-0.5">
        <button
          class="flex items-center gap-1 rounded-[7px] px-2.5 py-1 text-xs font-medium transition"
          :class="view.view_type === 'board' ? 'sp-seg-active text-ink-gray-9' : 'text-ink-gray-5 hover:text-ink-gray-8'"
          @click="$emit('change', { view_type: 'board' })"
        >
          <LucideLayoutGrid class="h-4 w-4" /> Board
        </button>
        <button
          class="flex items-center gap-1 rounded-[7px] px-2.5 py-1 text-xs font-medium transition"
          :class="view.view_type === 'list' ? 'sp-seg-active text-ink-gray-9' : 'text-ink-gray-5 hover:text-ink-gray-8'"
          @click="$emit('change', { view_type: 'list' })"
        >
          <LucideList class="h-4 w-4" /> List
        </button>
        <button
          v-if="dueField"
          class="flex items-center gap-1 rounded-[7px] px-2.5 py-1 text-xs font-medium transition"
          :class="view.view_type === 'calendar' ? 'sp-seg-active text-ink-gray-9' : 'text-ink-gray-5 hover:text-ink-gray-8'"
          @click="$emit('change', { view_type: 'calendar' })"
        >
          <LucideCalendar class="h-4 w-4" /> Calendar
        </button>
      </div>

      <!-- subtasks: separate vs nested -->
      <div class="sp-chip flex shrink-0 items-center gap-0.5 p-0.5" title="How subtasks appear">
        <button
          class="rounded-[7px] px-2.5 py-1 text-xs font-medium transition"
          :class="subtaskMode === 'separate' ? 'sp-seg-active text-ink-gray-9' : 'text-ink-gray-5 hover:text-ink-gray-8'"
          @click="$emit('subtask-mode', 'separate')"
        >
          Separate
        </button>
        <button
          class="rounded-[7px] px-2.5 py-1 text-xs font-medium transition"
          :class="subtaskMode === 'nested' ? 'sp-seg-active text-ink-gray-9' : 'text-ink-gray-5 hover:text-ink-gray-8'"
          @click="$emit('subtask-mode', 'nested')"
        >
          Nested
        </button>
      </div>

      <!-- me mode -->
      <button
        v-if="assigneeField"
        class="sp-control flex shrink-0 items-center gap-1.5 px-2.5 py-1.5 text-sm"
        :class="view.me_mode ? 'sp-control-active' : ''"
        @click="$emit('change', { me_mode: !view.me_mode })"
      >
        <LucideUser class="h-4 w-4" /> Me
      </button>

      <!-- group by (list only — the board is always a kanban by bucket) -->
      <label v-if="isList" class="sp-chip flex shrink-0 items-center gap-1.5 px-2.5 py-1.5 text-sm sp-ink-2" aria-label="Group by">
        <LucideListTree class="h-3.5 w-3.5" />
        <span class="max-md:hidden">Group:</span>
        <select
          :value="view.group_by"
          class="bg-transparent text-ink-gray-8 focus:outline-none"
          @change="$emit('change', { group_by: $event.target.value })"
        >
          <option v-for="o in groupOptions" :key="o.value" :value="o.value">{{ o.label }}</option>
        </select>
      </label>

      <!-- sort (the calendar is always ordered by date) -->
      <label v-if="!isCalendar" class="sp-chip flex shrink-0 items-center gap-1.5 px-2.5 py-1.5 text-sm sp-ink-2" aria-label="Sort by">
        <LucideArrowDownNarrowWide class="h-3.5 w-3.5" />
        <span class="max-md:hidden">Sort:</span>
        <select
          :value="view.sort_field || ''"
          class="bg-transparent text-ink-gray-8 focus:outline-none"
          @change="$emit('change', { sort_field: $event.target.value })"
        >
          <option value="">Default</option>
          <option v-for="f in fields" :key="f.fieldname" :value="f.fieldname">{{ f.label }}</option>
        </select>
        <button
          v-if="view.sort_field"
          class="text-ink-gray-5 hover:text-ink-gray-8"
          @click="$emit('change', { sort_dir: view.sort_dir === 'asc' ? 'desc' : 'asc' })"
        >
          {{ view.sort_dir === 'asc' ? '↑' : '↓' }}
        </button>
      </label>

      <!-- filters -->
      <FilterPopover :filters="view.filters" :fields="fields" :buckets="buckets" @update="(f) => $emit('change', { filters: f })" />

      <!-- save -->
      <div class="ml-auto flex shrink-0 items-center gap-2">
        <!-- on a saved view: a single Save that updates it in place (no name prompt) -->
        <template v-if="!activeIsBuiltin">
          <AccentButton v-if="dirty" @click="$emit('save')">
            <template #prefix><LucideSave class="h-4 w-4" /></template>
            Save changes
          </AccentButton>
          <Button v-else variant="subtle" @click="$emit('save')">
            <template #prefix><LucideCheck class="h-4 w-4" /></template>
            Saved
          </Button>
        </template>
        <!-- on a builtin list view: saving creates a new view (hidden on the board) -->
        <Button v-else-if="!isBoard" variant="ghost" @click="$emit('new')">Save as view</Button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { Button } from 'frappe-ui'
import FilterPopover from '@/components/FilterPopover.vue'
import AccentButton from '@/components/AccentButton.vue'

const props = defineProps({
  views: Array,
  activeKey: String,
  view: Object,
  fields: { type: Array, default: () => [] },
  buckets: { type: Array, default: () => [] },
  bucketField: String,
  assigneeField: String,
  dueField: String,
  dirty: Boolean,
  search: { type: String, default: '' },
  subtaskMode: { type: String, default: 'separate' },
  currentUser: { type: String, default: '' },
})
defineEmits(['select', 'change', 'save', 'new', 'delete', 'search', 'subtask-mode', 'toggle-share'])

// you can flip sharing only on views you own
function canToggle(v) {
  return v.owner && v.owner === props.currentUser
}

const activeIsBuiltin = computed(() => props.views.find((v) => v.key === props.activeKey)?._builtin)
const isBoard = computed(() => props.view?.view_type === 'board')
const isList = computed(() => props.view?.view_type === 'list')
const isCalendar = computed(() => props.view?.view_type === 'calendar')

const groupOptions = computed(() => {
  const opts = [{ value: props.bucketField, label: 'Bucket' }]
  for (const f of props.fields) {
    if ((f.fieldtype === 'Select' || f.fieldtype === 'Link') && f.fieldname !== props.bucketField) {
      opts.push({ value: f.fieldname, label: f.label })
    }
  }
  return opts
})
</script>
