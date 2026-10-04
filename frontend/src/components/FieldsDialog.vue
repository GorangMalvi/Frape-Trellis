<template>
  <Teleport to="body">
    <transition name="sp-fade" appear>
      <div class="fixed inset-0 z-[70] flex items-center justify-center sp-scrim p-4 max-md:p-0" @click.self="$emit('close')">
        <transition name="sp-pop" appear>
          <div ref="panelEl" v-glass="{ scale: -90, chroma: 6, blur: 4, saturate: 1.7, radius: 22 }"role="dialog" aria-modal="true" aria-label="Fields" class="sp-modal sp-modal-sheet flex max-h-[88vh] w-full max-w-[980px] flex-col overflow-hidden">
            <div class="flex items-center justify-between border-b sp-hair px-5 py-4">
              <div>
                <h2 class="text-base font-semibold text-ink-gray-9">Field settings</h2>
                <p class="mt-0.5 text-sm sp-ink-3">{{ config?.space?.label }} · labels, options, order, and custom fields.</p>
              </div>
              <button class="sp-control p-1.5" @click="$emit('close')"><LucideX class="h-4 w-4" /></button>
            </div>

            <div class="grid min-h-0 flex-1 grid-cols-1 max-md:grid-rows-[minmax(0,40%)_minmax(0,60%)] md:grid-cols-[320px,1fr]">
              <aside class="flex min-h-0 flex-col border-b sp-hair md:border-b-0 md:border-r">
                <div class="flex items-center justify-between px-4 py-3">
                  <p class="sp-uppercase">Fields</p>
                  <button class="sp-control flex items-center gap-1.5 px-2 py-1.5 text-sm" @click="startCreate">
                    <LucidePlus class="h-3.5 w-3.5" />
                    New
                  </button>
                </div>

                <div class="sp-scroll min-h-0 flex-1 overflow-auto px-3 pb-3">
                  <Draggable
                    v-model="orderedFields"
                    item-key="fieldname"
                    handle=".field-drag-handle"
                    class="space-y-1"
                    ghost-class="opacity-40"
                    @end="saveOrder"
                  >
                    <template #item="{ element: f }">
                      <button
                        class="flex w-full items-center gap-2 rounded-md px-2 py-2 text-left transition"
                        :class="selected === f.fieldname && !creating ? 'bg-[var(--sp-fill-strong)] text-ink-gray-9' : 'hover:bg-[var(--sp-fill)]'"
                        @click="selectField(f.fieldname)"
                      >
                        <LucideListTree class="field-drag-handle h-4 w-4 shrink-0 cursor-grab sp-ink-4" />
                        <LucideTag v-if="isChip(f)" class="h-4 w-4 shrink-0 sp-ink-3" />
                        <LucideList v-else-if="f.fieldtype === 'Select'" class="h-4 w-4 shrink-0 sp-ink-3" />
                        <LucideHash v-else-if="isNumericField(f)" class="h-4 w-4 shrink-0 sp-ink-3" />
                        <LucideCalendar v-else-if="f.fieldtype === 'Date'" class="h-4 w-4 shrink-0 sp-ink-3" />
                        <LucideClock v-else-if="f.fieldtype === 'Duration'" class="h-4 w-4 shrink-0 sp-ink-3" />
                        <LucideSquareCheck v-else-if="f.fieldtype === 'Check'" class="h-4 w-4 shrink-0 sp-ink-3" />
                        <LucideUser v-else-if="f.fieldtype === 'Link' && f.options === 'User'" class="h-4 w-4 shrink-0 sp-ink-3" />
                        <LucideAlignLeft v-else class="h-4 w-4 shrink-0 sp-ink-3" />
                        <span class="min-w-0 flex-1">
                          <span class="block truncate text-sm font-medium">{{ f.label || f.fieldname }}</span>
                          <span class="block truncate text-xs sp-ink-3">{{ f.fieldname }}</span>
                        </span>
                        <span class="rounded bg-[var(--sp-fill)] px-1.5 py-0.5 text-[11px] font-medium sp-ink-2">
                          {{ typeLabel(f) }}
                        </span>
                        <LucideLock v-if="!canDelete(f)" class="h-3.5 w-3.5 shrink-0 sp-ink-4" />
                      </button>
                    </template>
                  </Draggable>

                  <p v-if="!orderedFields.length" class="rounded-md border sp-hair p-3 text-sm sp-ink-3">
                    No editable fields found for this space.
                  </p>
                </div>

                <p v-if="ordering" class="border-t sp-hair px-4 py-2 text-xs sp-ink-3">Saving field order...</p>
              </aside>

              <main class="sp-scroll min-h-0 overflow-auto p-4 md:p-5">
                <div v-if="creating" class="mx-auto max-w-xl">
                  <div class="mb-5">
                    <p class="sp-uppercase mb-1">New field</p>
                    <h3 class="text-lg font-semibold sp-ink-1">Create a field</h3>
                  </div>

                  <div class="space-y-4">
                    <label class="block">
                      <span class="mb-1.5 block text-sm font-medium sp-ink-2">Label</span>
                      <input
                        v-model="newLabel"
                        placeholder="Category"
                        class="h-10 w-full rounded-md border sp-hair px-3 text-sm focus:border-outline-gray-3 focus:outline-none"
                      />
                    </label>

                    <label class="block">
                      <span class="mb-1.5 block text-sm font-medium sp-ink-2">Type</span>
                      <select v-model="newKind" class="h-10 w-full rounded-md border sp-hair bg-surface-white px-3 text-sm focus:outline-none">
                        <option v-for="k in KINDS" :key="k.value" :value="k.value">{{ k.label }}</option>
                      </select>
                    </label>

                    <label v-if="newKind === 'multiselect' || newKind === 'select'" class="block">
                      <span class="mb-1.5 block text-sm font-medium sp-ink-2">Options</span>
                      <ChipField v-model="newOptions" placeholder="Add a choice..." />
                    </label>
                  </div>

                  <p v-if="error" class="mt-4 text-sm text-ink-red-3">{{ error }}</p>

                  <div class="mt-6 flex justify-end gap-2">
                    <Button @click="cancelCreate">Cancel</Button>
                    <Button variant="solid" :loading="adding" @click="addField">Create field</Button>
                  </div>
                </div>

                <div v-else-if="selectedField" class="mx-auto max-w-xl">
                  <div class="mb-5 flex items-start justify-between gap-4">
                    <div>
                      <p class="sp-uppercase mb-1">{{ selectedField.fieldname }}</p>
                      <h3 class="text-lg font-semibold sp-ink-1">{{ selectedField.label || selectedField.fieldname }}</h3>
                    </div>
                    <span class="rounded-md bg-[var(--sp-fill)] px-2 py-1 text-xs font-medium sp-ink-2">
                      {{ typeLabel(selectedField) }}
                    </span>
                  </div>

                  <div class="space-y-4">
                    <label class="block">
                      <span class="mb-1.5 block text-sm font-medium sp-ink-2">Label</span>
                      <input
                        v-model="labelDraft"
                        class="h-10 w-full rounded-md border sp-hair px-3 text-sm focus:border-outline-gray-3 focus:outline-none"
                      />
                    </label>

                    <div class="grid gap-3 sm:grid-cols-2">
                      <label class="flex items-start gap-2 rounded-lg border sp-hair p-3">
                        <input v-model="reqdDraft" type="checkbox" class="mt-0.5 rounded" />
                        <span>
                          <span class="block text-sm font-medium sp-ink-1">Mandatory</span>
                          <span class="block text-xs sp-ink-4">Always required, regardless of dependency rules.</span>
                        </span>
                      </label>
                      <label class="flex items-start gap-2 rounded-lg border sp-hair p-3">
                        <input v-model="readOnlyAlwaysDraft" type="checkbox" class="mt-0.5 rounded" />
                        <span>
                          <span class="block text-sm font-medium sp-ink-1">Read Only</span>
                          <span class="block text-xs sp-ink-4">Always locked, regardless of dependency rules.</span>
                        </span>
                      </label>
                    </div>

                    <label v-if="hasEditableOptions(selectedField)" class="block">
                      <span class="mb-1.5 block text-sm font-medium sp-ink-2">Options</span>
                      <ChipField v-model="optionsDraft" placeholder="Add a choice..." />
                    </label>

                    <div
                      v-if="selectedField.fieldtype === 'Select' && !isChip(selectedField)"
                      class="rounded-lg border sp-hair bg-[var(--sp-fill)] p-3"
                    >
                      <div class="flex items-center justify-between gap-3">
                        <div>
                          <p class="text-sm font-medium sp-ink-1">Use multiple values</p>
                          <p class="mt-0.5 text-xs sp-ink-3">Converts this Select field to a chip-style multi-select field.</p>
                        </div>
                        <Button :loading="converting === selectedField.fieldname" @click="convert(selectedField.fieldname)">
                          Make multi-select
                        </Button>
                      </div>
                    </div>

                    <div class="rounded-lg border sp-hair p-4">
                      <p class="sp-uppercase mb-3">Dependencies</p>
                      <div class="space-y-3">
                        <DependencyBuilder
                          v-model="dependsDraft"
                          label="Display Depends On (JS)"
                          placeholder='eval:doc.priority == "High"'
                          :fields="fields"
                          :buckets="config?.buckets || []"
                          :bucket-field="config?.space?.bucket_field || 'bucket'"
                          :chip-fields="chipFields"
                          :chip-options="chipOptions"
                        />
                        <DependencyBuilder
                          v-model="mandatoryDraft"
                          label="Mandatory Depends On (JS)"
                          placeholder="eval:doc.needs_approval"
                          :fields="fields"
                          :buckets="config?.buckets || []"
                          :bucket-field="config?.space?.bucket_field || 'bucket'"
                          :chip-fields="chipFields"
                          :chip-options="chipOptions"
                        />
                        <DependencyBuilder
                          v-model="readOnlyDraft"
                          label="Read Only Depends On (JS)"
                          placeholder='eval:doc.status == "Closed"'
                          :fields="fields"
                          :buckets="config?.buckets || []"
                          :bucket-field="config?.space?.bucket_field || 'bucket'"
                          :chip-fields="chipFields"
                          :chip-options="chipOptions"
                        />
                      </div>
                      <p class="mt-2 text-xs sp-ink-4">Use native Frappe expressions: a fieldname, or eval: JavaScript using doc.</p>
                    </div>
                  </div>

                  <p v-if="error" class="mt-4 text-sm text-ink-red-3">{{ error }}</p>

                  <div class="mt-6 flex items-center justify-between gap-3 border-t sp-hair pt-4">
                    <button
                      class="inline-flex items-center gap-1.5 rounded-md px-2.5 py-1.5 text-sm text-ink-red-3 transition hover:bg-surface-red-1 disabled:cursor-not-allowed disabled:opacity-40"
                      :disabled="!canDelete(selectedField) || deleting"
                      @click="deleteSelected"
                    >
                      <LucideTrash2 class="h-4 w-4" />
                      Delete field
                    </button>
                    <Button variant="solid" :loading="saving" @click="saveSelected">Save changes</Button>
                  </div>

                  <p v-if="!canDelete(selectedField)" class="mt-2 text-xs sp-ink-4">
                    This field is used by the space or ticket system and cannot be deleted.
                  </p>
                </div>

                <div v-else class="flex h-full min-h-[260px] items-center justify-center text-sm sp-ink-3">
                  Select a field or create a new one.
                </div>
              </main>
            </div>
          </div>
        </transition>
      </div>
    </transition>
  </Teleport>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { Button, call } from 'frappe-ui'
import Draggable from 'vuedraggable'
import ChipField from '@/components/ChipField.vue'
import DependencyBuilder from '@/components/DependencyBuilder.vue'
import { errorMessage, confirmDelete } from '@/store'
import { useOverlay } from '@/composables/useOverlay'

const props = defineProps({ space: String, config: Object })
const emit = defineEmits(['close', 'changed'])

const panelEl = ref(null)
useOverlay({ close: () => emit('close'), panel: panelEl })

const KINDS = [
  { value: 'multiselect', label: 'Multi-select' },
  { value: 'select', label: 'Single-select' },
  { value: 'text', label: 'Text' },
  { value: 'number', label: 'Number' },
  { value: 'duration', label: 'Time estimate (h/m)' },
  { value: 'date', label: 'Date' },
  { value: 'check', label: 'Checkbox' },
  { value: 'user', label: 'User' },
]

const orderedFields = ref([])
const selected = ref('')
const creating = ref(false)
const labelDraft = ref('')
const optionsDraft = ref('')
const reqdDraft = ref(false)
const readOnlyAlwaysDraft = ref(false)
const dependsDraft = ref('')
const mandatoryDraft = ref('')
const readOnlyDraft = ref('')
const newLabel = ref('')
const newKind = ref('multiselect')
const newOptions = ref('')
const saving = ref(false)
const adding = ref(false)
const deleting = ref(false)
const ordering = ref(false)
const converting = ref(null)
const error = ref('')

const fields = computed(() => props.config?.fields || [])
const chipFields = computed(() => props.config?.space?.chip_fields || [])
const chipOptions = computed(() => props.config?.space?.chip_options || {})
const protectedFields = computed(() => {
  const space = props.config?.space || {}
  return new Set([
    'name',
    'owner',
    'creation',
    'modified',
    'modified_by',
    'idx',
    'docstatus',
    'parent',
    'parentfield',
    'parenttype',
    'title',
    'bucket',
    'parent_task',
    'position',
    'requester',
    space.title_field,
    space.bucket_field,
    space.assignee_field,
    space.body_field,
    space.parent_field,
    space.badge_field,
  ].filter(Boolean))
})
const selectedField = computed(() => orderedFields.value.find((f) => f.fieldname === selected.value) || null)

watch(
  fields,
  (next) => {
    orderedFields.value = (next || []).map((f) => ({ ...f }))
    if (!creating.value && (!selected.value || !orderedFields.value.some((f) => f.fieldname === selected.value))) {
      selected.value = orderedFields.value[0]?.fieldname || ''
    }
    seedSelected()
  },
  { immediate: true, deep: true },
)
watch(selectedField, seedSelected)
watch(chipOptions, seedSelected, { deep: true })

function seedSelected() {
  if (!selectedField.value) {
    labelDraft.value = ''
    optionsDraft.value = ''
    reqdDraft.value = false
    readOnlyAlwaysDraft.value = false
    dependsDraft.value = ''
    mandatoryDraft.value = ''
    readOnlyDraft.value = ''
    return
  }
  labelDraft.value = selectedField.value.label || ''
  optionsDraft.value = optionList(selectedField.value).join(',')
  reqdDraft.value = !!selectedField.value.reqd
  readOnlyAlwaysDraft.value = !!selectedField.value.read_only
  dependsDraft.value = selectedField.value.depends_on || ''
  mandatoryDraft.value = selectedField.value.mandatory_depends_on || ''
  readOnlyDraft.value = selectedField.value.read_only_depends_on || ''
}

function isChip(f) {
  return chipFields.value.includes(f?.fieldname)
}
function canDelete(f) {
  return !!f?.can_delete && !protectedFields.value.has(f.fieldname)
}
function hasEditableOptions(f) {
  return !!f && (isChip(f) || f.fieldtype === 'Select')
}
function optionList(f) {
  if (!f) return []
  if (isChip(f)) return chipOptions.value[f.fieldname] || []
  return (f.options || '').split('\n').map((s) => s.trim()).filter(Boolean)
}
function listFrom(str) {
  return (str || '').split(',').map((s) => s.trim()).filter(Boolean)
}
function typeLabel(f) {
  if (isChip(f)) return 'Multi'
  if (f.fieldtype === 'Select') return 'Select'
  if (f.fieldtype === 'Data') return 'Text'
  if (isNumericField(f)) return 'Number'
  if (f.fieldtype === 'Link' && f.options === 'User') return 'User'
  if (f.fieldtype === 'Small Text') return 'Text'
  return f.fieldtype || 'Field'
}
function isNumericField(f) {
  return ['Int', 'Float', 'Currency', 'Percent'].includes(f?.fieldtype)
}
function patchLocalField(fieldname, patch) {
  const i = orderedFields.value.findIndex((f) => f.fieldname === fieldname)
  if (i !== -1) orderedFields.value[i] = { ...orderedFields.value[i], ...patch }
}
function selectField(fieldname) {
  creating.value = false
  error.value = ''
  selected.value = fieldname
}
function startCreate() {
  creating.value = true
  error.value = ''
}
function cancelCreate() {
  creating.value = false
  error.value = ''
  selected.value = selected.value || orderedFields.value[0]?.fieldname || ''
}

async function addField() {
  error.value = ''
  if (!newLabel.value.trim()) {
    error.value = 'Enter a field label.'
    return
  }
  adding.value = true
  try {
    const res = await call('sprint.api.add_field', {
      space: props.space,
      label: newLabel.value.trim(),
      kind: newKind.value,
      options: JSON.stringify(listFrom(newOptions.value)),
    })
    const fieldtype = {
      multiselect: 'Small Text',
      select: 'Select',
      text: 'Data',
      number: 'Int',
      duration: 'Duration',
      date: 'Date',
      check: 'Check',
      user: 'Link',
    }[newKind.value]
    orderedFields.value.push({
      fieldname: res.fieldname,
      label: res.label,
      fieldtype,
      options: newKind.value === 'select' ? listFrom(newOptions.value).join('\n') : newKind.value === 'user' ? 'User' : '',
      can_delete: true,
    })
    selected.value = res.fieldname
    creating.value = false
    newLabel.value = ''
    newOptions.value = ''
    emit('changed')
  } catch (e) {
    error.value = errorMessage(e, 'Could not add field.')
  } finally {
    adding.value = false
  }
}

async function saveSelected() {
  if (!selectedField.value) return
  error.value = ''
  if (!labelDraft.value.trim()) {
    error.value = 'Enter a field label.'
    return
  }
  saving.value = true
  try {
    const args = {
      space: props.space,
      fieldname: selectedField.value.fieldname,
      label: labelDraft.value.trim(),
      reqd: reqdDraft.value ? 1 : 0,
      read_only: readOnlyAlwaysDraft.value ? 1 : 0,
      depends_on: dependsDraft.value.trim(),
      mandatory_depends_on: mandatoryDraft.value.trim(),
      read_only_depends_on: readOnlyDraft.value.trim(),
    }
    if (hasEditableOptions(selectedField.value)) {
      args.options = JSON.stringify(listFrom(optionsDraft.value))
    }
    const res = await call('sprint.api.update_field', args)
    patchLocalField(res.fieldname, {
      label: res.label,
      reqd: reqdDraft.value ? 1 : 0,
      read_only: readOnlyAlwaysDraft.value ? 1 : 0,
      depends_on: dependsDraft.value.trim(),
      mandatory_depends_on: mandatoryDraft.value.trim(),
      read_only_depends_on: readOnlyDraft.value.trim(),
      options: selectedField.value.fieldtype === 'Select' && !isChip(selectedField.value)
        ? (res.options || []).join('\n')
        : selectedField.value.options,
    })
    emit('changed')
  } catch (e) {
    error.value = errorMessage(e, 'Could not save field.')
  } finally {
    saving.value = false
  }
}

async function deleteSelected() {
  if (!selectedField.value || !canDelete(selectedField.value)) return
  const field = selectedField.value
  const ok = await confirmDelete({
    title: `Delete “${field.label || field.fieldname}”?`,
    message: 'Existing values in this field will be removed. This cannot be undone.',
    confirmLabel: 'Delete field',
  })
  if (!ok) return
  error.value = ''
  deleting.value = true
  try {
    await call('sprint.api.delete_field', { space: props.space, fieldname: field.fieldname })
    const index = orderedFields.value.findIndex((f) => f.fieldname === field.fieldname)
    orderedFields.value = orderedFields.value.filter((f) => f.fieldname !== field.fieldname)
    selected.value = orderedFields.value[index]?.fieldname || orderedFields.value[index - 1]?.fieldname || orderedFields.value[0]?.fieldname || ''
    emit('changed')
  } catch (e) {
    error.value = errorMessage(e, 'Could not delete field.')
  } finally {
    deleting.value = false
  }
}

async function saveOrder() {
  error.value = ''
  ordering.value = true
  try {
    await call('sprint.api.reorder_fields', {
      space: props.space,
      fieldnames: JSON.stringify(orderedFields.value.map((f) => f.fieldname)),
    })
    emit('changed')
  } catch (e) {
    error.value = errorMessage(e, 'Could not save field order.')
    orderedFields.value = fields.value.map((f) => ({ ...f }))
  } finally {
    ordering.value = false
  }
}

async function convert(fieldname) {
  converting.value = fieldname
  error.value = ''
  try {
    await call('sprint.api.convert_to_multiselect', { space: props.space, fieldname })
    patchLocalField(fieldname, { fieldtype: 'Small Text', options: '' })
    emit('changed')
  } catch (e) {
    error.value = errorMessage(e, 'Could not convert field.')
  } finally {
    converting.value = null
  }
}
</script>
