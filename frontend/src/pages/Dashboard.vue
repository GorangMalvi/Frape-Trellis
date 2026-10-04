<template>
  <div class="flex h-full flex-col">
    <header class="sp-glass-strong z-20 flex items-center gap-2.5 px-4 pt-4 md:px-6">
      <button class="sp-control shrink-0 p-1.5" title="Back to board" aria-label="Back to board" @click="$router.push(backRoute)">
        <LucideArrowLeft class="h-4 w-4" />
      </button>
      <span class="text-lg">{{ cfg?.space?.icon || '📋' }}</span>
      <h1 class="sp-display min-w-0 truncate text-[17px] font-semibold sp-ink-1">
        {{ cfg?.space?.label || space }} <span class="sp-ink-3">· Dashboard</span>
      </h1>
      <div v-if="canManage && !loading && !loadError" class="ml-auto flex shrink-0 flex-wrap items-center justify-end gap-1">
        <template v-if="editing">
          <Button variant="ghost" aria-label="Add widget" @click="addWidget">
            <template #prefix><LucidePlus class="h-4 w-4" /></template>
            <span class="max-sm:hidden">Add widget</span>
          </Button>
          <Button variant="subtle" @click="cancelEdit">Cancel</Button>
          <AccentButton :loading="saving" @click="saveLayout">Save</AccentButton>
        </template>
        <Button v-else variant="ghost" @click="startEdit">
          <template #prefix><LucideSlidersHorizontal class="h-4 w-4" /></template>
          Customize
        </Button>
      </div>
    </header>

    <main class="sp-scroll min-h-0 flex-1 overflow-y-auto px-4 py-5 md:px-6">
      <div v-if="loading" class="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        <div v-for="i in 6" :key="i" class="sp-skeleton h-40 rounded-2xl" />
      </div>

      <EmptyState v-else-if="loadError" title="Couldn’t load this dashboard" :message="loadError">
        <template #icon><LucideCircleAlert class="h-6 w-6" /></template>
        <template #action><AccentButton @click="load">Retry</AccentButton></template>
      </EmptyState>

      <template v-else>
        <p v-if="editing" class="mb-3 text-sm sp-ink-3">
          Drag to reorder · click a widget’s pencil to edit · changes are shared with the space.
        </p>

        <Draggable
          v-if="editing"
          v-model="widgets"
          item-key="id"
          handle=".widget-drag-handle"
          v-bind="touchDragOptions"
          class="grid gap-4 sm:grid-cols-2 lg:grid-cols-3"
          ghost-class="opacity-40"
        >
          <template #item="{ element, index }">
            <div :class="spanClass(element)">
              <DashboardWidget
                :widget="element"
                :cards="allCards"
                :ctx="ctx"
                editing
                @edit="editWidget(index)"
                @remove="removeWidget(index)"
              />
            </div>
          </template>
        </Draggable>

        <div v-else class="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          <div v-for="wdg in widgets" :key="wdg.id" :class="spanClass(wdg)">
            <DashboardWidget :widget="wdg" :cards="allCards" :ctx="ctx" @drill="onDrill" />
          </div>
        </div>

        <EmptyState
          v-if="editing && !widgets.length"
          title="No widgets"
          message="Add a number or chart to build your dashboard."
        >
          <template #icon><LucideLayoutDashboard class="h-6 w-6" /></template>
          <template #action><AccentButton @click="addWidget">Add widget</AccentButton></template>
        </EmptyState>
      </template>
    </main>

    <WidgetEditor
      v-if="editorOpen"
      :widget="editorWidget"
      :ctx="ctx"
      @close="editorOpen = false"
      @save="applyWidget"
    />
  </div>
</template>

<script setup>
import { computed, onUnmounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { Button, call, createResource } from 'frappe-ui'
import Draggable from 'vuedraggable'
import { touchDragOptions } from '@/lib/dnd'
import AccentButton from '@/components/AccentButton.vue'
import EmptyState from '@/components/EmptyState.vue'
import DashboardWidget from '@/components/DashboardWidget.vue'
import WidgetEditor from '@/components/WidgetEditor.vue'
import { ensureUsers } from '@/lib/users'
import { useSpacePointers } from '@/composables/useSpacePointers'
import { errorMessage, pushToast, subscribeDoctype } from '@/store'
import { buildCtx, defaultWidgets, emptyWidget } from '@/lib/dashboard'

const props = defineProps({ space: String })
const router = useRouter()

const config = createResource({ url: 'sprint.api.get_space', makeParams: () => ({ space: props.space }) })
const cards = createResource({ url: 'sprint.api.get_cards', makeParams: () => ({ space: props.space }) })

const cfg = computed(() => config.data)
const { isTicket } = useSpacePointers(cfg)
const canManage = computed(() => !!cfg.value?.can_manage)
const backRoute = computed(() => isTicket.value
  ? { name: 'TicketBoard', params: { space: props.space } }
  : { name: 'Board', params: { space: props.space } })

const loading = computed(() => (config.loading || cards.loading) && !cfg.value)
const loadError = ref(null)
const allCards = computed(() => cards.data || [])
const ctx = computed(() => buildCtx(cfg.value))

// widgets: saved layout, or auto-defaults when the space has none
const widgets = ref([])
function resetWidgets() {
  const saved = cfg.value?.space?.dashboard?.widgets
  widgets.value = saved && saved.length
    ? saved.map((w) => ({ ...w, id: w.id || `w${Math.random().toString(36).slice(2)}` }))
    : defaultWidgets(ctx.value)
}

ensureUsers()
async function load() {
  loadError.value = null
  try {
    await config.fetch()
    await cards.fetch()
    resetWidgets()
    setupRealtime()
  } catch (e) {
    loadError.value = errorMessage(e)
  }
}
watch(() => props.space, load, { immediate: true })

let unsub = null
function setupRealtime() {
  unsub?.()
  const doctype = cfg.value?.space?.doctype
  if (doctype) unsub = subscribeDoctype(doctype, () => cards.reload())
}
onUnmounted(() => unsub?.())

// span: bar charts are wider (span 2 on lg) so long category lists read well
function spanClass(w) {
  if (w.type === 'stat') return ''
  return w.chart === 'donut' ? '' : 'lg:col-span-2'
}

// ---- edit mode -------------------------------------------------------------
const editing = ref(false)
const saving = ref(false)
const editorOpen = ref(false)
const editorWidget = ref(null)
let editorIndex = -1

function startEdit() {
  editing.value = true
}
function cancelEdit() {
  editing.value = false
  resetWidgets() // discard unsaved changes
}
function addWidget() {
  editorWidget.value = null
  editorIndex = -1
  editorOpen.value = true
}
function editWidget(i) {
  editorWidget.value = widgets.value[i]
  editorIndex = i
  editorOpen.value = true
}
function removeWidget(i) {
  widgets.value.splice(i, 1)
}
function applyWidget(w) {
  if (editorIndex >= 0) widgets.value[editorIndex] = w
  else widgets.value.push({ ...w, id: w.id || emptyWidget().id })
  editorOpen.value = false
}
async function saveLayout() {
  saving.value = true
  try {
    await call('sprint.api.save_dashboard', {
      space: props.space,
      widgets: JSON.stringify(widgets.value),
    })
    // reflect the saved layout back into the loaded config
    if (cfg.value?.space) cfg.value.space.dashboard = { widgets: widgets.value }
    editing.value = false
    pushToast('Dashboard saved', 'success')
  } catch (e) {
    pushToast(errorMessage(e))
  } finally {
    saving.value = false
  }
}

// ---- click-to-drill: open the board filtered by the clicked value ----------
function onDrill({ field, value, isChip }) {
  const bucketField = ctx.value.bucketField
  // grouping by bucket → the board is already a kanban by bucket; just go there
  if (field === bucketField) {
    router.push(backRoute.value)
    return
  }
  const filter = { field, operator: isChip ? 'contains' : 'is', value }
  router.push({
    name: isTicket.value ? 'TicketBoard' : 'Board',
    params: { space: props.space },
    query: { view: 'list', filter: JSON.stringify([filter]) },
  })
}
</script>
