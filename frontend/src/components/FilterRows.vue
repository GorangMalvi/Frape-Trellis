<template>
  <div>
    <div v-if="!rows.length" class="px-1 py-2 text-sm text-ink-gray-5">
      {{ emptyText }}
    </div>

    <div v-for="(f, i) in rows" :key="i" class="mb-2 flex flex-wrap items-center gap-1.5">
      <select v-model="f.field" class="sp-field min-w-0 max-sm:max-w-[45%]" @change="onFieldChange(f)">
        <option v-for="fld in fields" :key="fld.fieldname" :value="fld.fieldname">{{ fld.label }}</option>
      </select>
      <select :value="f.operator" class="sp-field min-w-0 max-sm:max-w-[40%]" @change="onOperatorChange(f, $event.target.value)">
        <option v-for="op in OPERATORS" :key="op" :value="op">{{ op }}</option>
      </select>
      <template v-if="!['is empty', 'is set'].includes(f.operator)">
        <!-- multi-value (is any of / is none of) -->
        <div
          v-if="isMulti(f) && optionsFor(f).length"
          class="sp-scroll sp-field flex max-h-24 min-w-0 flex-1 flex-wrap content-start gap-1 overflow-auto py-1.5 max-sm:basis-full"
        >
          <button
            v-for="o in optionsFor(f)"
            :key="o.value"
            class="rounded-md px-2 py-0.5 text-xs font-medium transition"
            :class="isPicked(f, o.value)
              ? 'bg-[var(--sp-accent-tint)] text-[color:var(--sp-accent)]'
              : 'bg-[var(--sp-fill)] text-ink-gray-6 hover:bg-[var(--sp-fill-hover)]'"
            @click="toggleValue(f, o.value)"
          >
            {{ o.label }}
          </button>
        </div>
        <input
          v-else-if="isMulti(f)"
          :value="(f.value || []).join(', ')"
          placeholder="value, value, …"
          class="sp-field min-w-0 flex-1 max-sm:basis-full"
          @input="f.value = $event.target.value.split(',').map((s) => s.trim()).filter(Boolean)"
        />

        <!-- single value -->
        <select v-else-if="optionsFor(f).length" v-model="f.value" class="sp-field min-w-0 flex-1 max-sm:basis-full">
          <option value="">—</option>
          <option v-for="o in optionsFor(f)" :key="o.value" :value="o.value">{{ o.label }}</option>
        </select>
        <input v-else v-model="f.value" placeholder="value" class="sp-field min-w-0 flex-1 max-sm:basis-full" />
      </template>
      <button class="rounded-md p-1 text-ink-gray-5 transition hover:bg-[var(--sp-fill)] hover:text-ink-gray-8" aria-label="Remove condition" @click="remove(i)">
        <LucideX class="h-3.5 w-3.5" />
      </button>
    </div>

    <button class="flex items-center gap-1 text-sm text-ink-gray-6 hover:text-ink-gray-8" @click="addRow">
      <LucidePlus class="h-3.5 w-3.5" /> {{ addLabel }}
    </button>
  </div>
</template>

<script setup>
// The {field, operator, value} row editor shared by the board Filter popover
// and the automation IF section. Operators + value-widget resolution match
// matchFilter in lib/board.js (and match_conditions on the backend). Emits a
// fresh array on every change; the parent owns the state (v-model).
import { computed, onMounted } from 'vue'
import { ensureUsers, userOptions } from '@/lib/users'

const props = defineProps({
  modelValue: { type: Array, default: () => [] },
  fields: { type: Array, default: () => [] },
  buckets: { type: Array, default: () => [] },
  addLabel: { type: String, default: 'Add filter' },
  emptyText: { type: String, default: 'No conditions yet.' },
})
const emit = defineEmits(['update:modelValue'])

const OPERATORS = ['is', 'is not', 'is any of', 'is none of', 'contains', 'is empty', 'is set']
const MULTI = ['is any of', 'is none of']

onMounted(ensureUsers)

// work on a local proxy so widget edits mutate rows, then emit a fresh copy
const rows = computed({
  get: () => props.modelValue || [],
  set: (v) => emit('update:modelValue', v),
})
function commit() {
  emit('update:modelValue', [...rows.value])
}

function isMulti(f) {
  return MULTI.includes(f.operator)
}
function isPicked(f, value) {
  return Array.isArray(f.value) && f.value.map(String).includes(String(value))
}
function toggleValue(f, value) {
  const arr = Array.isArray(f.value) ? [...f.value] : []
  const i = arr.findIndex((v) => String(v) === String(value))
  if (i >= 0) arr.splice(i, 1)
  else arr.push(value)
  f.value = arr
  commit()
}
function onOperatorChange(f, op) {
  const wasMulti = MULTI.includes(f.operator)
  const willMulti = MULTI.includes(op)
  f.operator = op
  if (willMulti && !Array.isArray(f.value)) {
    f.value = f.value ? [f.value] : []
  } else if (!willMulti && wasMulti) {
    f.value = Array.isArray(f.value) ? f.value[0] || '' : ''
  }
  commit()
}

function optionsFor(f) {
  const fld = props.fields.find((x) => x.fieldname === f.field)
  if (!fld) return []
  if (fld.fieldtype === 'Select') {
    return (fld.options || '').split('\n').filter(Boolean).map((o) => ({ value: o, label: o }))
  }
  if (fld.fieldtype === 'Link' && fld.options === 'SP Bucket') {
    return props.buckets.map((b) => ({ value: b.name, label: b.bucket_name }))
  }
  if (fld.fieldtype === 'Link' && fld.options === 'User') {
    return userOptions()
  }
  return []
}
function onFieldChange(f) {
  f.value = MULTI.includes(f.operator) ? [] : ''
  commit()
}
function addRow() {
  const first = props.fields[0]
  emit('update:modelValue', [...rows.value, { field: first?.fieldname || '', operator: 'is', value: '' }])
}
function remove(i) {
  const next = [...rows.value]
  next.splice(i, 1)
  emit('update:modelValue', next)
}
</script>
