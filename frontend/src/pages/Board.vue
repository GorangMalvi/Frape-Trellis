<template>
  <div v-if="!space" class="flex h-full items-center justify-center text-ink-gray-5">
    Select a space from the sidebar.
  </div>

  <div v-else class="flex h-full flex-col">
    <!-- space header -->
    <header class="sp-glass-strong z-20 flex items-center justify-between px-4 pb-1 pt-4 md:px-6">
      <div class="flex min-w-0 items-center gap-2.5">
        <span class="text-lg">{{ cfg?.space?.icon || '📋' }}</span>
        <h1 class="sp-display truncate text-[17px] font-semibold sp-ink-1">{{ cfg?.space?.label || space }}</h1>
        <span class="rounded-full bg-[var(--sp-fill)] px-2 py-0.5 text-xs font-medium sp-ink-3 sp-tnum">{{ visibleCount }}</span>
      </div>
      <!-- desktop: labelled action row -->
      <div class="hidden items-center gap-1 md:flex">
        <Button variant="ghost" @click="$router.push({ name: 'Dashboard', params: { space } })">
          <template #prefix><LucideChartNoAxesColumn class="h-4 w-4" /></template>
          Dashboard
        </Button>
        <template v-if="canManage">
        <Button variant="ghost" @click="accessOpen = true">
          <template #prefix><LucideLock class="h-4 w-4" /></template>
          Access
        </Button>
        <Button v-if="!isTicket" variant="ghost" @click="$router.push({ name: 'Data', params: { space } })">
          <template #prefix><LucideArrowDownUp class="h-4 w-4" /></template>
          Data
        </Button>
        <Button v-if="isTicket" variant="ghost" @click="membersOpen = true">
          <template #prefix><LucideUsers class="h-4 w-4" /></template>
          Members
        </Button>
        <Button variant="ghost" @click="$router.push({ name: 'Automations', params: { space } })">
          <template #prefix><LucideZap class="h-4 w-4" /></template>
          Automations
        </Button>
        <Button variant="ghost" @click="fieldsOpen = true">
          <template #prefix><LucideSlidersHorizontal class="h-4 w-4" /></template>
          Fields
        </Button>
        <Button variant="ghost" @click="promptAddBucket">
          <template #prefix><LucidePlus class="h-4 w-4" /></template>
          Bucket
        </Button>
        </template>
      </div>
      <!-- mobile: same actions behind one overflow button -->
      <button
        class="sp-control flex h-9 w-9 shrink-0 items-center justify-center md:hidden"
        aria-label="Space actions"
        @click="actionsOpen = true"
      >
        <LucideEllipsis class="h-5 w-5" />
      </button>
      <BottomSheet v-if="actionsOpen" :title="cfg?.space?.label || space" @close="actionsOpen = false">
        <button
          v-for="a in headerActions"
          :key="a.key"
          class="flex w-full items-center gap-3 rounded-[10px] px-3 py-2.5 text-left text-sm sp-ink-1 transition hover:bg-[var(--sp-fill)]"
          @click="runHeaderAction(a)"
        >
          <span class="flex h-7 w-7 items-center justify-center rounded-lg bg-[var(--sp-fill)] sp-ink-2">
            <LucideChartNoAxesColumn v-if="a.key === 'dashboard'" class="h-4 w-4" />
            <LucideLock v-else-if="a.key === 'access'" class="h-4 w-4" />
            <LucideArrowDownUp v-else-if="a.key === 'data'" class="h-4 w-4" />
            <LucideUsers v-else-if="a.key === 'members'" class="h-4 w-4" />
            <LucideZap v-else-if="a.key === 'automations'" class="h-4 w-4" />
            <LucideSlidersHorizontal v-else-if="a.key === 'fields'" class="h-4 w-4" />
            <LucidePlus v-else class="h-4 w-4" />
          </span>
          {{ a.label }}
        </button>
      </BottomSheet>
    </header>

    <Toolbar
      v-if="cfg"
      :views="allViews"
      :active-key="activeKey"
      :view="view"
      :fields="filterableFields"
      :buckets="cfg?.buckets || []"
      :bucket-field="bucketField"
      :assignee-field="assigneeField"
      :due-field="dueField"
      :search="search"
      :dirty="dirty"
      :subtask-mode="subtaskMode"
      :current-user="currentUser"
      @select="selectView"
      @change="patchView"
      @save="updateView"
      @new="newView"
      @delete="deleteView"
      @toggle-share="toggleShare"
      @search="(s) => (search = s)"
      @subtask-mode="(m) => (subtaskMode = m)"
    />

    <!-- views -->
    <div class="min-h-0 flex-1">
      <!-- load failed: error panel with retry (instead of an eternal skeleton) -->
      <EmptyState
        v-if="loadError && !cfg"
        title="Couldn’t load this space"
        :message="loadError"
      >
        <template #icon><LucideCircleAlert class="h-6 w-6" /></template>
        <template #action>
          <AccentButton @click="load">Retry</AccentButton>
        </template>
      </EmptyState>

      <template v-else-if="loading">
        <div v-if="view.view_type === 'board'" class="flex gap-4 p-5">
          <div v-for="i in 4" :key="i" class="w-[85vw] max-w-xs shrink-0 rounded-xl bg-surface-gray-2 p-2 md:w-72 md:max-w-none">
            <div class="sp-skeleton mb-3 ml-1 mt-1 h-3.5 w-24 rounded" />
            <div v-for="j in 3" :key="j" class="sp-skeleton mb-2 h-16 rounded-lg" />
          </div>
        </div>
        <div v-else class="px-5 py-4">
          <div class="sp-skeleton mb-3 h-3.5 w-40 rounded" />
          <div v-for="i in 8" :key="i" class="sp-skeleton mb-2 h-9 rounded-lg" />
        </div>
      </template>

      <!-- space has no cards at all -->
      <EmptyState
        v-else-if="!(cards.data || []).length"
        :title="isTicket ? 'No tickets yet' : 'No tasks yet'"
        :message="isTicket
          ? 'Raise the first ticket and it will show up here.'
          : 'Create the first task to get this space moving.'"
      >
        <template #icon><LucideInbox class="h-6 w-6" /></template>
        <template #action>
          <AccentButton @click="newCard((cfg?.buckets || [])[0]?.name || '__none__')">
            {{ isTicket ? 'Raise ticket' : 'New task' }}
          </AccentButton>
        </template>
      </EmptyState>

      <!-- filters/search hide everything -->
      <EmptyState
        v-else-if="visibleCount === 0"
        title="No matching tasks"
        message="Nothing matches the current filters and search."
      >
        <template #icon><LucideSearchX class="h-6 w-6" /></template>
        <template #action>
          <Button variant="subtle" @click="clearFiltersAndSearch">Clear filters &amp; search</Button>
        </template>
      </EmptyState>

      <CalendarView
        v-else-if="view.view_type === 'calendar' && dueField"
        :cards="visibleCards"
        :due-field="dueField"
        :title-field="titleField"
        :badge-field="badgeField"
        :assignee-field="assigneeField"
        :allow-new-card="!isTicket"
        @open-card="openCard"
        @new-card="newCardOnDate"
        @reschedule="onReschedule"
      />

      <BoardView
        v-else-if="view.view_type === 'board'"
        :groups="groups"
        :title-field="titleField"
        :assignee-field="assigneeField"
        :badge-field="badgeField"
        :chip-fields="chipFields"
        :subtask-count="subtaskCount"
        :selected="selected"
        :bucket-mode="bucketMode && canManage"
        :parent-field="parentField"
        :parent-map="parentMap"
        :subtask-mode="subtaskMode"
        :subtasks-by-parent="subtasksByParent"
        :allow-new-card="!isTicket"
        @move="onMove"
        @open-card="openCard"
        @new-card="newCard"
        @toggle-select="toggleSelect"
        @add-bucket="promptAddBucket"
        @rename-bucket="renameBucket"
        @recolor-bucket="recolorBucket"
        @delete-bucket="deleteBucket"
        @reorder-buckets="reorderBuckets"
      />
      <ListView
        v-else
        :groups="groups"
        :columns="listColumns"
        :title-field="titleField"
        :badge-field="badgeField"
        :chip-fields="chipFields"
        :subtask-count="subtaskCount"
        :selected="selected"
        :group-field="groupFieldDef"
        :buckets="cfg?.buckets || []"
        :bucket-field="bucketField"
        :allow-new-card="!isTicket"
        @open-card="openCard"
        @new-card="newCard"
        @edit="onEdit"
        @toggle-select="toggleSelect"
      />
    </div>

    <BulkBar
      :count="selected.length"
      :buckets="cfg?.buckets || []"
      :fields="cfg?.fields || []"
      :assignee-field="assigneeField"
      :badge-field="badgeField"
      @set="bulkSet"
      @delete="bulkDelete"
      @clear="clearSelection"
    />

    <TaskDrawer
      v-if="drawerName"
      :doctype="doctype"
      :name="drawerName"
      :config="cfg"
      @close="drawerName = null"
      @saved="cards.reload()"
      @open-task="(n) => (drawerName = n)"
    />

    <FieldsDialog
      v-if="fieldsOpen"
      :space="space"
      :config="cfg"
      @close="fieldsOpen = false"
      @changed="() => { config.reload(); cards.reload() }"
    />

    <TicketMembersDialog
      v-if="membersOpen"
      :space="space"
      :config="cfg"
      @close="membersOpen = false"
      @changed="config.reload()"
    />

    <SpaceAccessDialog
      v-if="accessOpen"
      :space="space"
      :config="cfg"
      @close="accessOpen = false"
      @changed="() => { config.reload(); cards.reload() }"
    />

    <AddBucketDialog
      v-if="addBucketOpen"
      :loading="addingBucket"
      :index="(cfg?.buckets || []).length"
      @close="addBucketOpen = false"
      @create="createBucket"
    />

    <SaveViewDialog
      v-if="saveViewOpen"
      :loading="savingView"
      @close="saveViewOpen = false"
      @create="createView"
    />

    <TaskDrawer
      v-if="newDraft"
      creating
      :doctype="doctype"
      :config="cfg"
      :preset-field="newDraft.field"
      :preset-value="newDraft.value"
      @close="newDraft = null"
      @created="onCreatedNew"
    />
  </div>
</template>

<script setup>
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Button, createResource, call } from 'frappe-ui'
import Toolbar from '@/components/Toolbar.vue'
import BoardView from '@/components/BoardView.vue'
import ListView from '@/components/ListView.vue'
import CalendarView from '@/components/CalendarView.vue'
import TaskDrawer from '@/components/TaskDrawer.vue'
import FieldsDialog from '@/components/FieldsDialog.vue'
import AddBucketDialog from '@/components/AddBucketDialog.vue'
import SaveViewDialog from '@/components/SaveViewDialog.vue'
import BulkBar from '@/components/BulkBar.vue'
import BottomSheet from '@/components/BottomSheet.vue'
import EmptyState from '@/components/EmptyState.vue'
import AccentButton from '@/components/AccentButton.vue'
import TicketMembersDialog from '@/components/TicketMembersDialog.vue'
import SpaceAccessDialog from '@/components/SpaceAccessDialog.vue'
import { applyFilters, sortCards, buildGroups, midpoint } from '@/lib/board'
import { useSpacePointers } from '@/composables/useSpacePointers'
import { useViewState } from '@/composables/useViewState'
import { fieldIsMandatory, fieldIsVisible } from '@/lib/depends'
import { ui, subscribeDoctype, pushToast, errorMessage, confirmDelete } from '@/store'
import { setCurrentUser, setCanManage } from '@/lib/users'

const props = defineProps({ space: String, mode: { type: String, default: 'task' } })
const route = useRoute()
const router = useRouter()

const config = createResource({ url: 'sprint.api.get_space', makeParams: () => ({ space: props.space }) })
const cards = createResource({ url: 'sprint.api.get_cards', makeParams: () => ({ space: props.space }) })
const views = createResource({ url: 'sprint.api.get_views', makeParams: () => ({ space: props.space }) })

const cfg = computed(() => config.data)
const doctype = computed(() => cfg.value?.space?.doctype)
const {
  titleField, bucketField, assigneeField, badgeField, dueField,
  chipFields, parentField, bodyField, isTicket: spaceIsTicket,
} = useSpacePointers(cfg)
const isTicket = computed(() => spaceIsTicket.value || props.mode === 'ticket')
const currentUser = computed(() => cfg.value?.current_user)
// Administrator gets structural controls (Data/Fields/buckets)
// and must re-enter their password to delete anything.
const canManage = computed(() => !!cfg.value?.can_manage)
// keep the avatar "me = orange" rule + structural gating in sync with the session
watch(
  cfg,
  (c) => {
    setCurrentUser(c?.current_user)
    setCanManage(c?.can_manage)
  },
  { immediate: true },
)
const loading = computed(() => (config.loading || cards.loading) && !cfg.value)

const search = ref('')
const loadError = ref(null)
const drawerName = ref(null)
const newDraft = ref(null)
const fieldsOpen = ref(false)
const membersOpen = ref(false)
const accessOpen = ref(false)

// ---- view state -----------------------------------------------------------
// subtask display: 'separate' = subtasks are their own cards; 'nested' =
// subtasks hidden as cards and shown under their parent via an expander.
const subtaskMode = ref('separate')

const {
  view, activeKey, savedViews, allViews,
  selectView, patchView, dirty, restoreViewState, setRestoring,
} = useViewState({
  space: () => props.space,
  views,
  bucketField,
  dueField,
  search,
  subtaskMode,
})

const baseCards = computed(() => {
  const all = cards.data || []
  return subtaskMode.value === 'nested' ? all.filter((c) => !c[parentField.value]) : all
})

const visibleCards = computed(() =>
  applyFilters(baseCards.value, {
    filters: view.filters,
    meMode: view.me_mode,
    assigneeField: assigneeField.value,
    currentUser: currentUser.value,
    search: search.value,
    titleField: titleField.value,
  }),
)

// name -> title (for parent labels) and parent -> [subtasks] (for nesting)
const parentMap = computed(() => {
  const m = {}
  for (const c of cards.data || []) m[c.name] = c[titleField.value]
  return m
})
const subtasksByParent = computed(() => {
  const m = {}
  for (const c of cards.data || []) {
    const p = c[parentField.value]
    if (p) (m[p] = m[p] || []).push(c)
  }
  return m
})
const visibleCount = computed(() => visibleCards.value.length)

const groups = ref([])
function rebuildGroups() {
  const g = buildGroups(visibleCards.value, {
    groupByField: view.group_by || bucketField.value,
    bucketField: bucketField.value,
    buckets: cfg.value?.buckets || [],
    fields: cfg.value?.fields || [],
  })
  // no explicit sort → honour manual drag order (position)
  const sf = view.sort_field || 'position'
  const sd = view.sort_field ? view.sort_dir : 'asc'
  for (const grp of g) grp.cards = sortCards(grp.cards, sf, sd)
  groups.value = g
}
watch(
  [
    visibleCards,
    () => view.group_by,
    () => view.sort_field,
    () => view.sort_dir,
    () => bucketField.value,
    () => cfg.value?.buckets,
    () => cfg.value?.fields,
  ],
  rebuildGroups,
  { immediate: true },
)

const subtaskMap = computed(() => {
  const m = {}
  for (const c of cards.data || []) {
    const p = c[parentField.value]
    if (p) m[p] = (m[p] || 0) + 1
  }
  return m
})
const subtaskCount = (card) => subtaskMap.value[card.name] || 0

const filterableFields = computed(() =>
  (cfg.value?.fields || []).filter(
    (f) => ![bodyField.value, parentField.value].includes(f.fieldname),
  ),
)
const listColumns = computed(() =>
  (cfg.value?.fields || []).filter(
    (f) => ![titleField.value, bucketField.value, parentField.value, bodyField.value].includes(f.fieldname),
  ),
)
// field def for the current group-by (lets the list show user avatars/names
// for user-grouped headers instead of raw email ids)
const groupFieldDef = computed(
  () => (cfg.value?.fields || []).find((f) => f.fieldname === (view.group_by || bucketField.value)) || null,
)

// ---- mutations ------------------------------------------------------------
function clearFiltersAndSearch() {
  view.filters = []
  view.me_mode = false
  search.value = ''
}

async function load() {
  if (!props.space) return
  setRestoring(true) // don't clobber storage while (re)loading a space
  loadError.value = null
  if (props.mode !== 'ticket') {
    try {
      localStorage.setItem('sprint.lastSpace', props.space)
    } catch { /* ignore */ }
  }
  // restore first so the loading skeleton matches the view we'll land on
  const restored = restoreViewState()
  if (!restored) selectView('board')
  try {
    await config.fetch()
    // re-apply the builtin default now that the real bucket_field is known
    if (!restored) selectView(activeKey.value || 'board')
    await cards.fetch()
    const qTicket = route.query.ticket
    if (props.mode === 'ticket' && qTicket) {
      drawerName.value = qTicket
      router.replace({ name: 'TicketBoard', params: { space: props.space } })
    }
    // cross-space open (Home / inbox click-through): ?card=<name>
    const qCard = route.query.card
    if (props.mode !== 'ticket' && qCard) {
      drawerName.value = qCard
      router.replace({ name: props.mode === 'ticket' ? 'TicketBoard' : 'Board', params: { space: props.space } })
    }
    // dashboard drill-through: ?view=list&filter=<json> applies a filter
    applyDrillQuery()
    views.fetch()
    setupRealtime()
  } catch (e) {
    loadError.value = errorMessage(e)
  } finally {
    setRestoring(false)
  }
}
watch(() => props.space, load, { immediate: true })

// dashboard click-to-drill: apply ?filter=<json> (+ optional ?view=list) then
// clean the URL so a refresh doesn't re-pin it.
function applyDrillQuery() {
  const raw = route.query.filter
  if (!raw) return
  try {
    const filters = JSON.parse(raw)
    if (Array.isArray(filters) && filters.length) {
      if (route.query.view === 'list') patchView({ view_type: 'list' })
      patchView({ filters })
    }
  } catch { /* ignore malformed drill query */ }
  const clean = { ...route.query }
  delete clean.filter
  delete clean.view
  router.replace({ params: { space: props.space }, query: clean })
}

// ---- realtime: live-update board when other users change things ----------
let unsubs = []
function clearSubs() {
  unsubs.forEach((fn) => fn())
  unsubs = []
}
function setupRealtime() {
  clearSubs()
  if (!doctype.value) return
  unsubs.push(subscribeDoctype(doctype.value, () => cards.reload()))
  unsubs.push(subscribeDoctype('SP Bucket', () => config.reload()))
}
onUnmounted(clearSubs)

async function onMove({ element, group }) {
  const list = group.cards
  const idx = list.findIndex((c) => c.name === element.name)
  const pos = midpoint(list[idx - 1]?.position, list[idx + 1]?.position)

  const field = view.group_by || bucketField.value
  const target = group.key === '__none__' ? null : group.key
  const values = { position: pos }
  const nextDoc = { ...element, position: pos }
  if (element[field] !== target) {
    values[field] = target
    nextDoc[field] = target
  }
  const missing = missingMandatoryFields(nextDoc)
  if (missing.length) {
    pushToast(`Please fill before moving: ${missing.join(', ')}`)
    cards.reload()
    return
  }
  element.position = pos
  if (element[field] !== target) element[field] = target
  try {
    if (isTicket.value) {
      await call('sprint.api.update_ticket', {
        doctype: doctype.value,
        name: element.name,
        values: JSON.stringify(values),
      })
    } else {
      await call('sprint.api.update_card', {
        doctype: doctype.value,
        name: element.name,
        values: JSON.stringify(values),
      })
    }
  } catch (e) {
    pushToast(errorMessage(e))
    cards.reload() // revert the optimistic move — server rejected it
  }
}

async function onEdit({ name, field, value }) {
  // ListView already updated the card object optimistically. If the edited
  // field is what we're grouping by (e.g. moving a card to another bucket
  // while grouped by bucket), re-group so the row jumps to its new section.
  const card = (cards.data || []).find((c) => c.name === name)
  const missing = missingMandatoryFields({ ...(card || {}), [field]: value })
  if (missing.length) {
    pushToast(`Please fill before saving: ${missing.join(', ')}`)
    cards.reload()
    return
  }
  if (field === (view.group_by || bucketField.value)) rebuildGroups()
  try {
    await call('sprint.api.set_field', {
      doctype: doctype.value,
      name,
      fieldname: field,
      value: value == null ? '' : value,
    })
  } catch (e) {
    pushToast(errorMessage(e))
    cards.reload() // revert the optimistic inline edit
  }
}

function missingMandatoryFields(doc) {
  return (cfg.value?.fields || [])
    .filter((f) => fieldIsVisible(f, doc) && fieldIsMandatory(f, doc))
    .filter((f) => doc[f.fieldname] == null || String(doc[f.fieldname]).trim() === '')
    .map((f) => f.label || f.fieldname)
}

// "+ Add task" opens a blank card modal (create mode); nothing is written
// until the user hits "Create task".
function newCard(groupKey) {
  if (isTicket.value) {
    router.push({ name: 'TicketIntake' })
    return
  }
  const field = view.group_by || bucketField.value
  newDraft.value = { field, value: groupKey === '__none__' ? null : groupKey }
}

// calendar: "+" on a day pre-fills the due date
function newCardOnDate(date) {
  if (isTicket.value) {
    router.push({ name: 'TicketIntake' })
    return
  }
  newDraft.value = { field: dueField.value, value: date }
}

// calendar: drag a card onto a day (or back to the "no date" tray)
async function onReschedule({ name, due }) {
  const card = (cards.data || []).find((c) => c.name === name)
  if (card) card[dueField.value] = due
  try {
    await call('sprint.api.set_field', {
      doctype: doctype.value,
      name,
      fieldname: dueField.value,
      value: due == null ? '' : due,
    })
  } catch (e) {
    pushToast(errorMessage(e))
    cards.reload() // revert the optimistic reschedule
  }
}
function onCreatedNew(name) {
  newDraft.value = null
  cards.reload()
  openCard(name) // reopen as the saved card so subtasks/comments are available
}

const addBucketOpen = ref(false)
const addingBucket = ref(false)
function promptAddBucket() {
  addBucketOpen.value = true
}
async function createBucket({ bucket_name, color }) {
  addingBucket.value = true
  try {
    await call('sprint.api.add_bucket', { space: props.space, bucket_name, color })
    addBucketOpen.value = false
    await reloadConfigAndGroups()
  } catch (e) {
    pushToast(errorMessage(e))
  } finally {
    addingBucket.value = false
  }
}

async function reloadConfigAndGroups() {
  await config.fetch()
  rebuildGroups()
}

// bucket management is only meaningful while grouping by bucket
const bucketMode = computed(() => (view.group_by || bucketField.value) === bucketField.value)

async function renameBucket({ group, bucket_name }) {
  group.label = bucket_name
  await call('sprint.api.update_bucket', { name: group.key, bucket_name })
  await reloadConfigAndGroups()
}
async function recolorBucket({ group, color }) {
  group.color = color
  await call('sprint.api.update_bucket', { name: group.key, color })
  await reloadConfigAndGroups()
}
async function deleteBucket(group) {
  const ok = await confirmDelete({
    title: `Delete bucket “${group.label}”?`,
    message: group.cards.length
      ? `Its ${group.cards.length} task(s) become unsorted. This cannot be undone.`
      : 'This cannot be undone.',
    requirePassword: canManage.value,
  })
  if (!ok) return
  await call('sprint.api.delete_bucket', { name: group.key })
  await reloadConfigAndGroups()
  cards.reload()
}
async function reorderBuckets(orderedKeys) {
  await call('sprint.api.reorder_buckets', { names: JSON.stringify(orderedKeys) })
  await reloadConfigAndGroups()
}

const saveViewOpen = ref(false)
const savingView = ref(false)
function newView() {
  saveViewOpen.value = true
}
const API_VIEW_TYPE = { board: 'Board', list: 'List', calendar: 'Calendar' }

async function createView({ name, is_shared }) {
  savingView.value = true
  try {
    const saved = await call('sprint.api.save_view', {
      space: props.space,
      view_name: name,
      view_type: API_VIEW_TYPE[view.view_type] || 'Board',
      group_by: view.group_by,
      sort_field: view.sort_field,
      sort_dir: view.sort_dir,
      me_mode: view.me_mode ? 1 : 0,
      is_shared,
      filters: JSON.stringify(view.filters || []),
    })
    await views.reload()
    activeKey.value = saved.name
    saveViewOpen.value = false
  } catch (e) {
    pushToast(errorMessage(e))
  } finally {
    savingView.value = false
  }
}

// flip a saved view between shared (team) and private (just me)
async function toggleShare(v) {
  try {
    await call('sprint.api.save_view', {
      name: v.name,
      space: props.space,
      view_name: v.view_name,
      view_type: API_VIEW_TYPE[v.view_type] || 'Board',
      group_by: v.group_by,
      sort_field: v.sort_field,
      sort_dir: v.sort_dir,
      me_mode: v.me_mode ? 1 : 0,
      is_shared: v.is_shared ? 0 : 1,
      filters: JSON.stringify(v.filters || []),
    })
    await views.reload()
    pushToast(v.is_shared ? 'View is now private' : 'View shared with the team', 'success')
  } catch (e) {
    pushToast(errorMessage(e))
  }
}

async function updateView() {
  const v = savedViews.value.find((x) => x.key === activeKey.value)
  if (!v) return
  try {
    await call('sprint.api.save_view', {
      name: v.name,
      space: props.space,
      view_name: v.view_name,
      view_type: API_VIEW_TYPE[view.view_type] || 'Board',
      group_by: view.group_by,
      sort_field: view.sort_field,
      sort_dir: view.sort_dir,
      me_mode: view.me_mode ? 1 : 0,
      is_shared: v.is_shared ? 1 : 0,
      filters: JSON.stringify(view.filters || []),
    })
    await views.reload()
    pushToast(`Saved to “${v.view_name}”`, 'success')
  } catch (e) {
    pushToast(errorMessage(e))
  }
}

async function deleteView(name) {
  const ok = await confirmDelete({
    title: 'Delete this view?',
    message: 'The view configuration will be removed. Cards are not affected.',
    requirePassword: canManage.value,
  })
  if (!ok) return
  await call('sprint.api.delete_view', { name })
  await views.reload()
  selectView('board')
}

function openCard(name) {
  drawerName.value = name
}

// ---- multi-select + bulk actions ----------------------------------------
const selected = ref([])
function toggleSelect(name) {
  const i = selected.value.indexOf(name)
  if (i >= 0) selected.value.splice(i, 1)
  else selected.value.push(name)
}
function clearSelection() {
  selected.value = []
}
async function bulkSet(values) {
  await call('sprint.api.bulk_set', {
    doctype: doctype.value,
    names: JSON.stringify(selected.value),
    values: JSON.stringify(values),
  })
  clearSelection()
  cards.reload()
}
async function bulkDelete() {
  const n = selected.value.length
  const ok = await confirmDelete({
    title: `Delete ${n} task${n === 1 ? '' : 's'}?`,
    message: 'This cannot be undone.',
    requirePassword: canManage.value,
  })
  if (!ok) return
  await call('sprint.api.bulk_delete', {
    doctype: doctype.value,
    names: JSON.stringify(selected.value),
  })
  clearSelection()
  cards.reload()
}
// clear selection when switching space
watch(() => props.space, clearSelection)

// ---- mobile header overflow sheet ---------------------------------------
const actionsOpen = ref(false)
const headerActions = computed(() => {
  const acts = [{ key: 'dashboard', label: 'Dashboard', run: () => router.push({ name: 'Dashboard', params: { space: props.space } }) }]
  if (canManage.value) {
    acts.push({ key: 'access', label: 'Access', run: () => (accessOpen.value = true) })
    if (!isTicket.value) acts.push({ key: 'data', label: 'Data', run: () => router.push({ name: 'Data', params: { space: props.space } }) })
    if (isTicket.value) acts.push({ key: 'members', label: 'Members', run: () => (membersOpen.value = true) })
    acts.push(
      { key: 'automations', label: 'Automations', run: () => router.push({ name: 'Automations', params: { space: props.space } }) },
      { key: 'fields', label: 'Fields', run: () => (fieldsOpen.value = true) },
      { key: 'bucket', label: 'New bucket', run: promptAddBucket },
    )
  }
  return acts
})
function runHeaderAction(a) {
  actionsOpen.value = false
  a.run()
}

// command palette hooks — "new task" opens the create drawer directly
function registerHooks() {
  ui._openCard = (name) => (drawerName.value = name)
  ui._newTask = () => newCard((cfg.value?.buckets || [])[0]?.name || '__none__')
  ui._refresh = () => cards.reload()
}
onMounted(registerHooks)
watch(() => props.space, registerHooks)
</script>
