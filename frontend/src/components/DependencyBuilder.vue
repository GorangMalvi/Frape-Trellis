<template>
  <div class="rounded-md border sp-hair p-3">
    <div class="mb-2 flex items-center justify-between gap-3">
      <div>
        <p class="text-sm font-medium sp-ink-1">{{ label }}</p>
        <p class="mt-0.5 text-xs sp-ink-4">Build a Frappe expression from field conditions.</p>
      </div>
      <button class="sp-control flex items-center gap-1 px-2 py-1 text-xs" @click="addCondition">
        <LucidePlus class="h-3.5 w-3.5" />
        Condition
      </button>
    </div>

    <div v-if="conditions.length" class="space-y-2">
      <div
        v-for="(row, index) in conditions"
        :key="row.id"
        class="grid items-center gap-2 md:grid-cols-[72px,1fr,104px,1fr,auto]"
      >
        <select
          v-model="row.join"
          :disabled="index === 0"
          class="h-9 rounded-md border sp-hair bg-surface-white px-2 text-xs focus:outline-none disabled:opacity-40"
          @change="syncExpression"
        >
          <option value="AND">AND</option>
          <option value="OR">OR</option>
        </select>

        <select
          v-model="row.fieldname"
          class="h-9 min-w-0 rounded-md border sp-hair bg-surface-white px-2 text-sm focus:outline-none"
          @change="onFieldChange(row)"
        >
          <option value="">Field</option>
          <option v-for="f in fields" :key="f.fieldname" :value="f.fieldname">{{ f.label || f.fieldname }}</option>
        </select>

        <select
          v-model="row.operator"
          class="h-9 rounded-md border sp-hair bg-surface-white px-2 text-sm focus:outline-none"
          @change="syncExpression"
        >
          <option value="==">is</option>
          <option value="!=">is not</option>
          <option value="set">is set</option>
          <option value="not_set">is empty</option>
        </select>

        <select
          v-if="valueOptions(row).length && needsValue(row)"
          v-model="row.value"
          class="h-9 min-w-0 rounded-md border sp-hair bg-surface-white px-2 text-sm focus:outline-none"
          @change="syncExpression"
        >
          <option value="">Value</option>
          <option v-for="opt in valueOptions(row)" :key="opt.value" :value="opt.value">{{ opt.label }}</option>
        </select>
        <input
          v-else-if="needsValue(row)"
          v-model="row.value"
          placeholder="Value"
          class="h-9 min-w-0 rounded-md border sp-hair px-2 text-sm focus:border-outline-gray-3 focus:outline-none"
          @input="syncExpression"
        />
        <span v-else class="text-xs sp-ink-4">No value</span>

        <button class="sp-control p-1.5" @click="removeCondition(index)">
          <LucideX class="h-3.5 w-3.5" />
        </button>
      </div>
    </div>

    <button v-else class="w-full rounded-md border border-dashed sp-hair py-2 text-sm sp-ink-3 transition hover:border-outline-gray-3 hover:text-ink-gray-8" @click="addCondition">
      Add first condition
    </button>

    <label class="mt-3 block">
      <span class="mb-1 block text-xs font-medium sp-ink-3">Expression</span>
      <textarea
        :value="modelValue"
        rows="2"
        :placeholder="placeholder"
        class="w-full resize-y rounded-md border sp-hair px-3 py-2 font-mono text-sm focus:border-outline-gray-3 focus:outline-none"
        @input="$emit('update:modelValue', $event.target.value)"
      />
    </label>
  </div>
</template>

<script setup>
import { ref, watch } from 'vue'

const props = defineProps({
  modelValue: { type: String, default: '' },
  label: { type: String, required: true },
  placeholder: { type: String, default: 'eval:doc.priority == "High"' },
  fields: { type: Array, default: () => [] },
  buckets: { type: Array, default: () => [] },
  bucketField: { type: String, default: 'bucket' },
  chipFields: { type: Array, default: () => [] },
  chipOptions: { type: Object, default: () => ({}) },
})
const emit = defineEmits(['update:modelValue'])

let nextId = 1
const conditions = ref([])
let syncing = false

watch(
  () => props.modelValue,
  (value) => {
    if (syncing) return
    conditions.value = parseExpression(value)
  },
  { immediate: true },
)

function addCondition() {
  const row = {
    id: nextId++,
    join: conditions.value.length ? 'AND' : 'AND',
    fieldname: props.fields[0]?.fieldname || '',
    operator: '==',
    value: '',
  }
  row.value = defaultValue(row)
  conditions.value.push(row)
  syncExpression()
}
function removeCondition(index) {
  conditions.value.splice(index, 1)
  syncExpression()
}
function onFieldChange(row) {
  row.value = defaultValue(row)
  syncExpression()
}
function fieldFor(row) {
  return props.fields.find((f) => f.fieldname === row.fieldname)
}
function needsValue(row) {
  return !['set', 'not_set'].includes(row.operator)
}
function defaultValue(row) {
  return valueOptions(row)[0]?.value || ''
}
function valueOptions(row) {
  const field = fieldFor(row)
  if (!field) return []
  if (field.fieldname === props.bucketField) {
    return props.buckets.map((b) => ({ label: b.bucket_name || b.name, value: b.name }))
  }
  if (props.chipFields.includes(field.fieldname)) {
    return (props.chipOptions[field.fieldname] || []).map((value) => ({ label: value, value }))
  }
  if (field.fieldtype === 'Select') {
    return (field.options || '').split('\n').filter(Boolean).map((value) => ({ label: value, value }))
  }
  if (field.fieldtype === 'Check') {
    return [
      { label: 'Yes', value: '1' },
      { label: 'No', value: '0' },
    ]
  }
  return []
}
function fieldRef(fieldname) {
  return /^[A-Za-z_$][\w$]*$/.test(fieldname) ? `doc.${fieldname}` : `doc[${JSON.stringify(fieldname)}]`
}
function literal(value, field) {
  if (field?.fieldtype === 'Check' && value === '1') return '1'
  if (field?.fieldtype === 'Check' && value === '0') return '0'
  return JSON.stringify(value)
}
function conditionExpression(row) {
  if (!row.fieldname) return ''
  const field = fieldFor(row)
  const ref = fieldRef(row.fieldname)
  if (row.operator === 'set') return ref
  if (row.operator === 'not_set') return `!${ref}`
  return `${ref} ${row.operator} ${literal(row.value, field)}`
}
function syncExpression() {
  const expr = conditions.value
    .map((row, index) => {
      const condition = conditionExpression(row)
      if (!condition) return ''
      return `${index === 0 ? '' : ` ${row.join === 'OR' ? '||' : '&&'} `}${condition}`
    })
    .join('')
  syncing = true
  emit('update:modelValue', expr ? `eval:${expr}` : '')
  queueMicrotask(() => {
    syncing = false
  })
}
function parseExpression(expression) {
  const text = String(expression || '').trim()
  if (!text.startsWith('eval:')) return []
  const body = text.slice(5).trim()
  if (!body) return []

  const tokens = body.split(/\s+(&&|\|\|)\s+/)
  const rows = []
  for (let i = 0; i < tokens.length; i += 2) {
    const raw = tokens[i]?.trim()
    if (!raw) continue
    const row = parseCondition(raw)
    if (!row) return []
    row.id = nextId++
    row.join = i === 0 ? 'AND' : tokens[i - 1] === '||' ? 'OR' : 'AND'
    rows.push(row)
  }
  return rows
}
function parseCondition(raw) {
  const empty = raw.match(/^!(.+)$/)
  if (empty) {
    const fieldname = parseFieldRef(empty[1].trim())
    return fieldname ? { fieldname, operator: 'not_set', value: '' } : null
  }

  const comparison = raw.match(/^(.+?)\s*(==|!=)\s*(.+)$/)
  if (comparison) {
    const fieldname = parseFieldRef(comparison[1].trim())
    if (!fieldname) return null
    return {
      fieldname,
      operator: comparison[2],
      value: parseLiteral(comparison[3].trim()),
    }
  }

  const fieldname = parseFieldRef(raw)
  return fieldname ? { fieldname, operator: 'set', value: '' } : null
}
function parseFieldRef(raw) {
  const dot = raw.match(/^doc\.([A-Za-z_$][\w$]*)$/)
  if (dot) return dot[1]
  const bracket = raw.match(/^doc\[(.+)\]$/)
  if (!bracket) return ''
  try {
    return JSON.parse(bracket[1])
  } catch {
    return ''
  }
}
function parseLiteral(raw) {
  if (raw === '1' || raw === '0') return raw
  try {
    return String(JSON.parse(raw))
  } catch {
    return raw.replace(/^['"]|['"]$/g, '')
  }
}
</script>
