<template>
  <Teleport to="body">
    <transition name="sp-fade" appear>
      <div class="fixed inset-0 z-[70] flex items-center justify-center sp-scrim p-4 backdrop-blur-md max-md:p-0 max-md:backdrop-blur-none" @click.self="$emit('close')">
        <transition name="sp-pop" appear>
          <div ref="panelEl" v-glass="{ scale: -90, chroma: 6, blur: 4, saturate: 1.7, radius: 22 }"role="dialog" aria-modal="true" aria-label="Automation builder" class="sp-modal sp-modal-sheet flex max-h-[88vh] w-full max-w-[880px] flex-col overflow-hidden">
            <!-- header: name + live sentence -->
            <div class="border-b sp-hair px-4 py-4 md:px-6">
              <div class="flex items-center gap-3">
                <input
                  v-model="rule.automation_name"
                  placeholder="Name this automation…"
                  class="sp-display flex-1 border-0 bg-transparent text-lg font-semibold text-ink-gray-9 focus:outline-none focus:ring-0"
                />
                <button class="sp-control p-1.5" aria-label="Close" @click="$emit('close')"><LucideX class="h-4 w-4" /></button>
              </div>
              <p class="mt-1 text-sm sp-ink-3">{{ preview }}</p>
            </div>

            <div class="sp-scroll min-h-0 flex-1 space-y-5 overflow-auto px-4 py-5 md:px-6">
              <!-- WHEN -->
              <section>
                <p class="sp-uppercase mb-2">When</p>
                <div class="grid grid-cols-2 gap-1.5 sm:grid-cols-3">
                  <button
                    v-for="t in TRIGGERS"
                    :key="t.type"
                    class="flex items-center gap-2 rounded-lg border px-2.5 py-2 text-left text-sm transition"
                    :class="rule.trigger_type === t.type ? 'border-transparent bg-[var(--sp-accent-tint)] text-[color:var(--sp-accent)] ring-1 ring-[color:var(--sp-accent)]' : 'sp-hair sp-ink-2 hover:bg-[var(--sp-fill)]'"
                    @click="pickTrigger(t.type)"
                  >
                    <AutomationIcon :kind="t.icon" class="h-4 w-4 shrink-0" />
                    <span class="truncate">{{ t.label }}</span>
                  </button>
                </div>

                <!-- trigger config -->
                <div class="mt-3 space-y-2">
                  <select v-if="rule.trigger_type === 'moved_to_bucket'" v-model="rule.trigger_config.bucket" class="sp-field">
                    <option :value="null">Any bucket</option>
                    <option v-for="b in buckets" :key="b.name" :value="b.name">{{ b.bucket_name }}</option>
                  </select>
                  <template v-else-if="rule.trigger_type === 'field_changed'">
                    <div class="flex flex-wrap gap-2">
                      <select v-model="rule.trigger_config.field" class="sp-field min-w-0">
                        <option value="">Field…</option>
                        <option v-for="f in fields" :key="f.fieldname" :value="f.fieldname">{{ f.label }}</option>
                      </select>
                      <input v-model="rule.trigger_config.to_value" placeholder="changes to… (optional)" class="sp-field flex-1" />
                    </div>
                  </template>
                  <div v-else-if="rule.trigger_type === 'due_date_approaching'" class="flex items-center gap-2 text-sm sp-ink-2">
                    <input v-model.number="rule.trigger_config.days_before" type="number" min="0" class="sp-field w-20" /> days before due
                  </div>
                  <div v-else-if="rule.trigger_type === 'card_inactive'" class="flex items-center gap-2 text-sm sp-ink-2">
                    <input v-model.number="rule.trigger_config.days" type="number" min="1" class="sp-field w-20" /> days without activity
                  </div>
                  <div v-else-if="rule.trigger_type === 'scheduled'" class="flex flex-wrap items-center gap-2 text-sm sp-ink-2">
                    <select v-model="rule.trigger_config.frequency" class="sp-field">
                      <option value="daily">Daily</option>
                      <option value="weekly">Weekly</option>
                      <option value="monthly">Monthly</option>
                    </select>
                    <select v-if="rule.trigger_config.frequency === 'weekly'" v-model.number="rule.trigger_config.weekday" class="sp-field">
                      <option v-for="(d, i) in WEEKDAYS" :key="i" :value="i">{{ d }}</option>
                    </select>
                    <template v-else-if="rule.trigger_config.frequency === 'monthly'">
                      on day <input v-model.number="rule.trigger_config.day_of_month" type="number" min="1" max="28" class="sp-field w-16" />
                    </template>
                    at <input v-model="rule.trigger_config.time" type="time" class="sp-field w-28" />
                  </div>
                  <p v-else-if="explainer" class="text-sm sp-ink-4">{{ explainer }}</p>
                </div>
              </section>

              <!-- IF -->
              <section>
                <p class="sp-uppercase mb-2">If <span class="normal-case sp-ink-4">(optional)</span></p>
                <FilterRows
                  v-model="rule.conditions"
                  :fields="conditionFields"
                  :buckets="buckets"
                  add-label="Add condition"
                  empty-text="Runs on every matching event. Add conditions to narrow it."
                />
              </section>

              <!-- THEN -->
              <section>
                <p class="sp-uppercase mb-2">Then</p>
                <Draggable v-model="rule.actions" item-key="_key" handle=".action-drag-handle" class="space-y-2" ghost-class="opacity-40">
                  <template #item="{ element, index }">
                    <AutomationActionRow
                      :model-value="element"
                      :index="index"
                      :fields="fields"
                      :buckets="buckets"
                      :templates="templates"
                      :bucket-field="bucketField"
                      :is-ticket="isTicket"
                      :cardless="cardless"
                      :problem="problemFor(index)"
                      @update:model-value="(v) => updateAction(index, v)"
                      @remove="removeAction(index)"
                    />
                  </template>
                </Draggable>
                <button class="mt-2 flex items-center gap-1.5 rounded-md px-2 py-1.5 text-sm sp-ink-3 transition hover:bg-[var(--sp-fill)] hover:text-ink-gray-8" @click="addAction">
                  <LucidePlus class="h-3.5 w-3.5" /> Add action
                </button>
              </section>

              <!-- dry-run panel -->
              <section v-if="testOpen" class="rounded-xl border sp-hair bg-[var(--sp-fill)] p-3">
                <div class="mb-2 flex items-center justify-between">
                  <p class="text-sm font-medium sp-ink-2">Test on a card</p>
                  <button class="sp-ink-4 hover:text-ink-gray-8" @click="testOpen = false"><LucideX class="h-4 w-4" /></button>
                </div>
                <input v-model="testQuery" placeholder="Search a card by title…" class="sp-field w-full" />
                <div v-if="testMatches.length && !testReport" class="mt-1.5 flex flex-col gap-1">
                  <button v-for="c in testMatches" :key="c.name" class="rounded-md px-2 py-1 text-left text-sm sp-ink-2 transition hover:bg-[var(--sp-surface)]" @click="runTest(c)">
                    {{ c[titleField] || c.name }}
                  </button>
                </div>
                <div v-if="testReport" class="mt-2 space-y-1.5 text-sm">
                  <p v-if="!testReport.trigger_would_match" class="text-ink-amber-3">This card would be skipped — conditions don't match.</p>
                  <div v-for="(c, i) in testReport.conditions" :key="i" class="flex items-center gap-1.5">
                    <LucideCheck v-if="c.passed" class="h-3.5 w-3.5 text-ink-green-3" />
                    <LucideX v-else class="h-3.5 w-3.5 text-ink-red-3" />
                    <span class="sp-ink-2">{{ c.field }} {{ c.operator }} {{ c.value }}</span>
                  </div>
                  <div v-for="(a, i) in testReport.actions" :key="'a' + i" class="flex items-start gap-1.5">
                    <span class="mt-0.5 sp-ink-4">→</span>
                    <span :class="a.status === 'failed' ? 'font-mono text-ink-red-3' : 'sp-ink-2'">Would {{ a.detail }}</span>
                  </div>
                  <button class="mt-1 text-xs text-[color:var(--sp-accent)]" @click="testReport = null">Try another card</button>
                </div>
              </section>
            </div>

            <!-- footer -->
            <div class="flex flex-wrap items-center gap-2 gap-y-2 border-t sp-hair px-4 py-3 md:px-6">
              <button
                class="flex items-center gap-1.5 rounded-md px-2.5 py-1.5 text-sm sp-ink-2 transition hover:bg-[var(--sp-fill)] disabled:opacity-40"
                :disabled="rule.trigger_type === 'scheduled' || !rule.name"
                :title="rule.trigger_type === 'scheduled' ? 'Scheduled rules have no source card to test' : (!rule.name ? 'Save first, then test' : 'Preview what this rule would do')"
                @click="openTest"
              >
                <LucideFlaskConical class="h-4 w-4" /> Test on a card
              </button>
              <p v-if="errors.length" class="text-xs text-ink-red-3">{{ errors[0].message }}</p>
              <div class="ml-auto flex gap-2">
                <Button variant="subtle" @click="$emit('close')">Cancel</Button>
                <AccentButton :loading="saving" :disabled="errors.length > 0" @click="save">Save automation</AccentButton>
              </div>
            </div>
          </div>
        </transition>
      </div>
    </transition>
  </Teleport>
</template>

<script setup>
import { computed, reactive, ref, watch } from 'vue'
import { Button, call, createResource } from 'frappe-ui'
import Draggable from 'vuedraggable'
import AccentButton from '@/components/AccentButton.vue'
import AutomationIcon from '@/components/AutomationIcon.vue'
import AutomationActionRow from '@/components/AutomationActionRow.vue'
import FilterRows from '@/components/FilterRows.vue'
import { useOverlay } from '@/composables/useOverlay'
import { useSpacePointers } from '@/composables/useSpacePointers'
import { pushToast, errorMessage } from '@/store'
import { userLabel } from '@/lib/users'
import {
  TRIGGERS, WEEKDAYS, emptyAction, emptyTriggerConfig, normalizeRule,
  validateRule, serializeActions, sentenceText, triggerMeta, isCardlessTrigger,
} from '@/lib/automation'

const props = defineProps({
  space: String,
  config: Object,
  templates: { type: Array, default: () => [] },
  automation: { type: Object, default: null },
  recipe: { type: Object, default: null },
})
const emit = defineEmits(['close', 'saved'])

const panelEl = ref(null)
useOverlay({ close: () => emit('close'), panel: panelEl })

const { titleField, bucketField, isTicket } = useSpacePointers(() => props.config)
const fields = computed(() => props.config?.fields || [])
const buckets = computed(() => props.config?.buckets || [])
const cardless = computed(() => isCardlessTrigger(rule.trigger_type))

// condition fields: exclude heavy/body types (mirror board's filterable set)
const conditionFields = computed(() =>
  fields.value.filter((f) => !['Text Editor', 'Long Text', 'Code'].includes(f.fieldtype)))

const rule = reactive(initRule())
function initRule() {
  if (props.automation) return normalizeRule(props.automation)
  if (props.recipe) {
    const r = normalizeRule({
      automation_name: props.recipe.name,
      trigger_type: props.recipe.trigger_type,
      trigger_config: props.recipe.trigger_config,
      conditions: props.recipe.conditions,
      actions: props.recipe.actions,
    })
    return r
  }
  return normalizeRule({ trigger_type: 'card_created', trigger_config: {}, actions: [emptyAction('notify')] })
}

const explainer = computed(() => {
  const t = rule.trigger_type
  if (t === 'card_created') return 'Fires when a new card is added to this space.'
  if (t === 'assignee_changed') return 'Fires when a card is reassigned.'
  if (t === 'comment_added') return 'Fires when someone comments on a card.'
  if (t === 'due_date_arrived') return 'Fires on the morning of the due date.'
  return ''
})

const ctx = computed(() => ({
  fields: fields.value, buckets: buckets.value, templates: props.templates, userLabel,
}))
const preview = computed(() => sentenceText(rule, ctx.value))
const errors = computed(() => validateRule(rule))
function problemFor(i) {
  return errors.value.find((e) => e.path === `actions.${i}`)?.message || ''
}

function pickTrigger(type) {
  rule.trigger_type = type
  rule.trigger_config = emptyTriggerConfig(type)
  // scheduled rules can't lead with card-editing actions
  if (isCardlessTrigger(type)) {
    rule.actions = rule.actions.filter((a) => !['set_field', 'move_to_bucket', 'assign', 'apply_template'].includes(a.type))
    if (!rule.actions.length) rule.actions = [emptyAction('create_card')]
  }
}
function addAction() {
  rule.actions.push(emptyAction(cardless.value ? 'notify' : 'set_field'))
}
function updateAction(i, v) {
  rule.actions[i] = v
}
function removeAction(i) {
  rule.actions.splice(i, 1)
}

const saving = ref(false)
async function save() {
  if (errors.value.length) {
    pushToast(errors.value[0].message)
    return
  }
  saving.value = true
  try {
    const payload = {
      space: props.space,
      automation_name: rule.automation_name.trim(),
      enabled: rule.enabled ? 1 : 0,
      trigger_type: rule.trigger_type,
      trigger_config: JSON.stringify(rule.trigger_config || {}),
      conditions: JSON.stringify(rule.conditions || []),
      actions: JSON.stringify(serializeActions(rule.actions)),
    }
    if (rule.name) payload.name = rule.name
    // only send a webhook secret if the user typed one on a webhook action
    const wh = rule.actions.find((a) => a.type === 'webhook' && a.secret)
    if (wh) payload.webhook_secret = wh.secret
    await call('sprint.automation.save_automation', payload)
    pushToast('Automation saved', 'success')
    emit('saved')
  } catch (e) {
    pushToast(errorMessage(e))
  } finally {
    saving.value = false
  }
}

// ---- dry-run ---------------------------------------------------------------
const testOpen = ref(false)
const testQuery = ref('')
const testReport = ref(null)
const cards = createResource({ url: 'sprint.api.get_cards', makeParams: () => ({ space: props.space }) })
function openTest() {
  testOpen.value = true
  testReport.value = null
  if (!cards.data) cards.fetch()
}
const testMatches = computed(() => {
  const q = testQuery.value.toLowerCase().trim()
  if (!q) return []
  return (cards.data || [])
    .filter((c) => String(c[titleField.value] || '').toLowerCase().includes(q))
    .slice(0, 8)
})
async function runTest(card) {
  if (!rule.name) {
    pushToast('Save the automation first, then test it.')
    return
  }
  try {
    testReport.value = await call('sprint.automation.run_automation_test', {
      automation: rule.name, card: card.name,
    })
  } catch (e) {
    pushToast(errorMessage(e))
  }
}
</script>
