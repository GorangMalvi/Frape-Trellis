<template>
  <div class="rounded-lg border sp-hair p-2.5" :class="hasProblem ? 'border-ink-red-3' : ''">
    <div class="flex items-center gap-2">
      <LucideGripVertical class="action-drag-handle h-4 w-4 shrink-0 cursor-grab sp-ink-4" />
      <span class="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-[var(--sp-fill)] text-[11px] font-semibold sp-ink-3 sp-tnum">{{ index + 1 }}</span>
      <select :value="model.type" class="sp-field" @change="changeType($event.target.value)">
        <option v-for="a in actionOptions" :key="a.type" :value="a.type">{{ a.label }}</option>
      </select>
      <button class="ml-auto rounded-md p-1 text-ink-gray-5 transition hover:bg-[var(--sp-fill)] hover:text-ink-red-3" aria-label="Remove action" @click="$emit('remove')">
        <LucideX class="h-3.5 w-3.5" />
      </button>
    </div>

    <div class="mt-2 space-y-2 pl-0 sm:pl-11">
      <!-- set_field -->
      <template v-if="model.type === 'set_field'">
        <div class="flex flex-wrap gap-2">
          <select v-model="model.field" class="sp-field min-w-0" @change="emitUpdate">
            <option value="">Field…</option>
            <option v-for="f in writableFields" :key="f.fieldname" :value="f.fieldname">{{ f.label }}</option>
          </select>
          <select v-if="selectedFieldType === 'Select'" v-model="model.value" class="sp-field flex-1" @change="emitUpdate">
            <option value="">—</option>
            <option v-for="o in selectOptions" :key="o" :value="o">{{ o }}</option>
          </select>
          <input v-else v-model="model.value" placeholder="Value" class="sp-field flex-1" @input="emitUpdate" />
        </div>
      </template>

      <!-- move_to_bucket -->
      <select v-else-if="model.type === 'move_to_bucket'" v-model="model.bucket" class="sp-field w-full" @change="emitUpdate">
        <option value="">Bucket…</option>
        <option v-for="b in buckets" :key="b.name" :value="b.name">{{ b.bucket_name }}</option>
      </select>

      <!-- assign -->
      <template v-else-if="model.type === 'assign'">
        <div class="sp-chip flex w-min gap-0.5 p-0.5">
          <button class="rounded-[7px] px-2.5 py-1 text-xs font-medium transition" :class="model.mode !== 'round_robin' ? 'sp-seg-active text-ink-gray-9' : 'sp-ink-3'" @click="setMode('one')">One person</button>
          <button class="rounded-[7px] px-2.5 py-1 text-xs font-medium transition" :class="model.mode === 'round_robin' ? 'sp-seg-active text-ink-gray-9' : 'sp-ink-3'" @click="setMode('round_robin')">Round robin</button>
        </div>
        <LinkField v-if="model.mode !== 'round_robin'" :model-value="model.user" doctype="User" placeholder="Person…" @update:model-value="(v) => { model.user = v; emitUpdate() }" />
        <div v-else class="flex flex-wrap gap-1">
          <button
            v-for="u in userOpts"
            :key="u.value"
            class="rounded-md px-2 py-0.5 text-xs font-medium transition"
            :class="(model.users || []).includes(u.value) ? 'bg-[var(--sp-accent-tint)] text-[color:var(--sp-accent)]' : 'bg-[var(--sp-fill)] text-ink-gray-6 hover:bg-[var(--sp-fill-hover)]'"
            @click="toggleUser(u.value)"
          >{{ u.label }}</button>
        </div>
      </template>

      <!-- apply_template / create_card -->
      <template v-else-if="model.type === 'apply_template' || model.type === 'create_card'">
        <select v-model="model.template" class="sp-field w-full" @change="emitUpdate">
          <option value="">Template…</option>
          <option v-for="t in templates" :key="t.name" :value="t.name">{{ t.template_name }}</option>
        </select>
        <label v-if="model.type === 'create_card' && !cardless" class="flex items-center gap-2 text-xs sp-ink-2">
          <input type="checkbox" v-model="model.as_subtask" class="rounded" @change="emitUpdate" />
          as a subtask of the trigger card
        </label>
        <p v-if="!templates.length" class="text-xs sp-ink-4">No templates yet — create one from a card first.</p>
      </template>

      <!-- notify -->
      <template v-else-if="model.type === 'notify'">
        <div class="flex flex-wrap gap-1">
          <button
            v-for="r in recipientOptions"
            :key="r.value"
            class="rounded-md px-2 py-0.5 text-xs font-medium transition"
            :class="(model.recipients || []).includes(r.value) ? 'bg-[var(--sp-accent-tint)] text-[color:var(--sp-accent)]' : 'bg-[var(--sp-fill)] text-ink-gray-6 hover:bg-[var(--sp-fill-hover)]'"
            @click="toggleRecipient(r.value)"
          >{{ r.label }}</button>
        </div>
        <PlaceholderInput :model-value="model.message" placeholder="Notification message…" @update:model-value="(v) => { model.message = v; emitUpdate() }" />
      </template>

      <!-- add_comment -->
      <PlaceholderInput v-else-if="model.type === 'add_comment'" :model-value="model.message" placeholder="Comment text…" @update:model-value="(v) => { model.message = v; emitUpdate() }" />

      <!-- webhook -->
      <template v-else-if="model.type === 'webhook'">
        <input v-model="model.url" placeholder="https://…" class="sp-field w-full" @input="emitUpdate" />
        <input v-model="model.secret" type="password" placeholder="Signing secret (optional) — sent as X-Sprint-Signature" class="sp-field w-full" @input="emitUpdate" />
      </template>
    </div>

    <p v-if="hasProblem" class="mt-1.5 pl-0 text-xs text-ink-red-3 sm:pl-11">{{ problem }}</p>
  </div>
</template>

<script setup>
import { computed, reactive, watch } from 'vue'
import LinkField from '@/components/LinkField.vue'
import PlaceholderInput from '@/components/PlaceholderInput.vue'
import { ACTIONS, emptyAction } from '@/lib/automation'
import { userOptions } from '@/lib/users'

const props = defineProps({
  modelValue: { type: Object, required: true },
  index: { type: Number, default: 0 },
  fields: { type: Array, default: () => [] },
  buckets: { type: Array, default: () => [] },
  templates: { type: Array, default: () => [] },
  bucketField: { type: String, default: 'bucket' },
  isTicket: { type: Boolean, default: false },
  cardless: { type: Boolean, default: false },
  problem: { type: String, default: '' },
})
const emit = defineEmits(['update:modelValue', 'remove'])

const model = reactive({ ...props.modelValue })
watch(() => props.modelValue, (v) => Object.assign(model, v))

const hasProblem = computed(() => !!props.problem)
const userOpts = computed(() => userOptions())

// a scheduled (cardless) rule can only offer actions that don't need a card
const actionOptions = computed(() =>
  props.cardless ? ACTIONS.filter((a) => !a.cardRequired) : ACTIONS,
)

const writableFields = computed(() =>
  props.fields.filter((f) => f.fieldname !== props.bucketField && !f.read_only &&
    !['Text Editor', 'Long Text', 'Code'].includes(f.fieldtype)),
)
const selectedFieldType = computed(() =>
  props.fields.find((f) => f.fieldname === model.field)?.fieldtype)
const selectOptions = computed(() =>
  (props.fields.find((f) => f.fieldname === model.field)?.options || '').split('\n').filter(Boolean))

const recipientOptions = computed(() => {
  const base = [{ value: 'assignee', label: 'Assignee' }, { value: 'watchers', label: 'Watchers' }]
  if (props.isTicket) base.push({ value: 'requester', label: 'Requester' })
  return base
})

function emitUpdate() {
  emit('update:modelValue', { ...model })
}
function changeType(type) {
  const fresh = emptyAction(type)
  fresh._key = model._key
  Object.keys(model).forEach((k) => delete model[k])
  Object.assign(model, fresh)
  emitUpdate()
}
function setMode(mode) {
  model.mode = mode
  emitUpdate()
}
function toggleUser(u) {
  const arr = model.users ? [...model.users] : []
  const i = arr.indexOf(u)
  if (i >= 0) arr.splice(i, 1)
  else arr.push(u)
  model.users = arr
  emitUpdate()
}
function toggleRecipient(r) {
  const arr = model.recipients ? [...model.recipients] : []
  const i = arr.indexOf(r)
  if (i >= 0) arr.splice(i, 1)
  else arr.push(r)
  model.recipients = arr
  emitUpdate()
}
</script>
