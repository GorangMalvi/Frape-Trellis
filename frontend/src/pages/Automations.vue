<template>
  <div class="flex h-full flex-col">
    <header class="sp-glass-strong z-20 flex items-center gap-2.5 px-4 pt-4 md:px-6">
      <button class="sp-control shrink-0 p-1.5" title="Back to board" aria-label="Back to board" @click="$router.push(backRoute)">
        <LucideArrowLeft class="h-4 w-4" />
      </button>
      <span class="text-lg">{{ cfg?.space?.icon || '📋' }}</span>
      <h1 class="sp-display min-w-0 truncate text-[17px] font-semibold sp-ink-1">
        {{ cfg?.space?.label || space }} <span class="sp-ink-3">· Automations</span>
      </h1>
      <div class="ml-auto flex shrink-0 items-center gap-1">
        <Button variant="ghost" @click="openRecipes">
          <template #prefix><LucideSparkles class="h-4 w-4" /></template>
          <span class="max-sm:hidden">Recipes</span>
        </Button>
        <AccentButton @click="newRule">
          <template #prefix><LucidePlus class="h-4 w-4" /></template>
          <span class="max-sm:hidden">New automation</span><span class="sm:hidden">New</span>
        </AccentButton>
      </div>
    </header>

    <main class="sp-scroll min-h-0 flex-1 overflow-y-auto px-4 py-5 md:px-6">
      <EmptyState
        v-if="cfg && !cfg.can_manage"
        title="Managers only"
        message="Automations are managed by space admins."
      >
        <template #icon><LucideLock class="h-6 w-6" /></template>
      </EmptyState>

      <template v-else>
        <!-- quota banner -->
        <div v-if="quota" class="sp-card mb-4 flex items-center gap-3 px-4 py-2.5">
          <LucideGauge class="h-4 w-4 sp-ink-3" />
          <span class="text-sm sp-ink-2 sp-tnum">{{ quota.used }} of {{ quota.limit }} daily runs used</span>
          <span class="ml-2 h-1.5 flex-1 overflow-hidden rounded-full bg-[var(--sp-fill)]">
            <span class="block h-full rounded-full" :style="{ width: quotaPct + '%', background: quotaColor }" />
          </span>
          <span v-if="quota.remaining === 0" class="text-xs font-medium text-ink-red-3">Paused for today</span>
        </div>

        <!-- tabs -->
        <div class="mb-4 flex gap-1">
          <button v-for="t in TABS" :key="t.key" class="sp-control px-3 py-1.5 text-sm" :class="tab === t.key ? 'sp-control-active' : ''" @click="setTab(t.key)">{{ t.label }}</button>
        </div>

        <!-- RULES -->
        <template v-if="tab === 'rules'">
          <div v-if="automations.loading && !automations.data" class="space-y-2">
            <div v-for="i in 3" :key="i" class="sp-skeleton h-16 rounded-2xl" />
          </div>
          <template v-else-if="rules.length">
            <div class="overflow-hidden rounded-2xl sp-surface shadow-[var(--sp-e1)] ring-1 ring-[color:var(--sp-line)]">
              <div v-for="(r, ri) in rules" :key="r.name" class="flex items-center gap-3 px-4 py-3" :class="ri ? 'border-t sp-hair' : ''">
                <AccentSwitch :model-value="!!r.enabled" @update:model-value="(v) => toggle(r, v)" />
                <span class="flex h-7 w-7 shrink-0 items-center justify-center rounded-lg bg-[var(--sp-fill)] sp-ink-2">
                  <AutomationIcon :kind="triggerIcon(r.trigger_type)" class="h-4 w-4" />
                </span>
                <button class="min-w-0 flex-1 text-left" @click="editRule(r)">
                  <span class="block truncate text-sm font-medium text-ink-gray-8">{{ r.automation_name }}</span>
                  <span class="block truncate text-xs sp-ink-3" :class="r.enabled ? '' : 'opacity-60'">{{ sentence(r) }}</span>
                </button>
                <span class="shrink-0 text-xs sp-ink-4 sp-tnum max-sm:hidden">{{ r.run_count || 0 }} runs</span>
                <button class="sp-control p-1.5 max-sm:hidden" title="Edit" aria-label="Edit automation" @click="editRule(r)"><LucidePencil class="h-3.5 w-3.5" /></button>
                <button class="sp-control p-1.5" title="Delete" aria-label="Delete automation" @click="removeRule(r)"><LucideTrash2 class="h-3.5 w-3.5" /></button>
              </div>
            </div>
          </template>
          <template v-else>
            <EmptyState title="Automate the busywork" message="Rules run when something happens in this space — assign, notify, move, comment, or call a webhook.">
              <template #icon><LucideZap class="h-6 w-6" /></template>
              <template #action><AccentButton @click="newRule">New automation</AccentButton></template>
            </EmptyState>
            <p class="sp-uppercase mb-2 mt-4">Start from a recipe</p>
            <AutomationRecipes :recipes="recipes" @pick="pickRecipe" />
          </template>
        </template>

        <!-- RUNS -->
        <AutomationRunLog v-else :space="space" :rules="rules" :is-ticket="isTicket" />
      </template>
    </main>

    <!-- builder -->
    <AutomationBuilder
      v-if="builderOpen"
      :space="space"
      :config="cfg"
      :templates="templates"
      :automation="editing"
      :recipe="recipeDraft"
      @close="closeBuilder"
      @saved="onSaved"
    />

    <!-- recipe picker modal -->
    <Teleport to="body">
      <transition name="sp-fade">
        <div v-if="recipesOpen" class="fixed inset-0 z-[70] flex items-start justify-center sp-scrim p-4 pt-[10vh] backdrop-blur-md" @click.self="recipesOpen = false">
          <transition name="sp-pop" appear>
            <div ref="recipePanel" v-glass="{ scale: -90, chroma: 6, blur: 4, saturate: 1.7, radius: 22 }"role="dialog" aria-modal="true" aria-label="Recipes" class="sp-modal max-h-[85vh] w-full max-w-[720px] overflow-y-auto p-5">
              <div class="mb-3 flex items-center justify-between">
                <h2 class="sp-display text-base font-semibold sp-ink-1">Automation recipes</h2>
                <button class="sp-control p-1.5" aria-label="Close" @click="recipesOpen = false"><LucideX class="h-4 w-4" /></button>
              </div>
              <AutomationRecipes :recipes="recipes" @pick="pickRecipe" />
            </div>
          </transition>
        </div>
      </transition>
    </Teleport>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Button, call, createResource } from 'frappe-ui'
import AccentButton from '@/components/AccentButton.vue'
import AccentSwitch from '@/components/AccentSwitch.vue'
import AutomationIcon from '@/components/AutomationIcon.vue'
import AutomationBuilder from '@/components/AutomationBuilder.vue'
import AutomationRunLog from '@/components/AutomationRunLog.vue'
import AutomationRecipes from '@/components/AutomationRecipes.vue'
import EmptyState from '@/components/EmptyState.vue'
import { useOverlay } from '@/composables/useOverlay'
import { useSpacePointers } from '@/composables/useSpacePointers'
import { confirmDelete, pushToast, errorMessage } from '@/store'
import { ensureUsers, userLabel } from '@/lib/users'
import { triggerMeta, sentenceText } from '@/lib/automation'

const props = defineProps({ space: String })
const route = useRoute()
const router = useRouter()

const TABS = [{ key: 'rules', label: 'Rules' }, { key: 'runs', label: 'Run history' }]
const tab = ref(route.query.tab === 'runs' ? 'runs' : 'rules')
function setTab(k) {
  tab.value = k
  router.replace({ query: { ...route.query, tab: k } })
}

ensureUsers()
const config = createResource({ url: 'sprint.api.get_space', makeParams: () => ({ space: props.space }), auto: true })
const automations = createResource({ url: 'sprint.automation.get_automations', makeParams: () => ({ space: props.space }), auto: true })
const cfg = computed(() => config.data)
const { isTicket } = useSpacePointers(cfg)
const rules = computed(() => automations.data?.rules || [])
const quota = computed(() => automations.data?.quota)
const quotaPct = computed(() => quota.value ? Math.min(100, Math.round((quota.value.used / quota.value.limit) * 100)) : 0)
const quotaColor = computed(() => quotaPct.value >= 100 ? 'var(--sp-danger, #ef4444)' : quotaPct.value >= 80 ? '#f59e0b' : 'var(--sp-accent)')

const backRoute = computed(() => isTicket.value
  ? { name: 'TicketBoard', params: { space: props.space } }
  : { name: 'Board', params: { space: props.space } })

const templates = ref([])
call('sprint.api.get_templates', { space: props.space }).then((t) => (templates.value = t || [])).catch(() => {})
const recipes = ref([])
function loadRecipes() {
  if (recipes.value.length) return
  call('sprint.automation.get_automation_recipes').then((r) => (recipes.value = r || [])).catch(() => {})
}
loadRecipes()

const ctx = computed(() => ({ fields: cfg.value?.fields || [], buckets: cfg.value?.buckets || [], templates: templates.value, userLabel }))
function sentence(r) {
  return sentenceText(r, ctx.value)
}
function triggerIcon(type) {
  return triggerMeta(type).icon
}

// ---- builder ---------------------------------------------------------------
const builderOpen = ref(false)
const editing = ref(null)
const recipeDraft = ref(null)
function newRule() {
  editing.value = null
  recipeDraft.value = null
  builderOpen.value = true
}
function editRule(r) {
  editing.value = r
  recipeDraft.value = null
  builderOpen.value = true
}
function closeBuilder() {
  builderOpen.value = false
  editing.value = null
  recipeDraft.value = null
}
function onSaved() {
  closeBuilder()
  automations.reload()
}
async function toggle(r, val) {
  try {
    await call('sprint.automation.toggle_automation', { name: r.name, enabled: val ? 1 : 0 })
    r.enabled = val ? 1 : 0
  } catch (e) {
    pushToast(errorMessage(e))
    automations.reload()
  }
}
async function removeRule(r) {
  const ok = await confirmDelete({
    title: `Delete “${r.automation_name}”?`,
    message: 'The rule stops running. Its run history is kept.',
  })
  if (!ok) return
  try {
    await call('sprint.automation.delete_automation', { name: r.name })
    automations.reload()
  } catch (e) {
    pushToast(errorMessage(e))
  }
}

// ---- recipes ---------------------------------------------------------------
const recipesOpen = ref(false)
const recipePanel = ref(null)
useOverlay({ close: () => (recipesOpen.value = false), panel: recipePanel, active: () => recipesOpen.value })
function openRecipes() {
  loadRecipes()
  recipesOpen.value = true
}
function pickRecipe(r) {
  recipesOpen.value = false
  editing.value = null
  recipeDraft.value = r
  builderOpen.value = true
}
</script>
