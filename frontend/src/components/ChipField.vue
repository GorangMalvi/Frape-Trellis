<template>
  <div class="relative">
    <div
      class="flex flex-wrap items-center gap-1 rounded-lg bg-[var(--sp-fill)] px-2 py-1.5 transition focus-within:bg-[var(--sp-fill-hover)]"
      :class="disabled ? 'cursor-not-allowed opacity-60' : ''"
      @click="focusInput"
    >
      <span
        v-for="(chip, i) in chips"
        :key="i"
        class="flex items-center gap-1 rounded-md bg-[var(--sp-fill-strong)] px-1.5 py-0.5 text-xs font-medium text-ink-gray-8"
      >
        {{ chip }}
        <button class="text-ink-gray-4 hover:text-ink-red-3 disabled:cursor-not-allowed" :disabled="disabled" @click.stop="remove(i)">
          <LucideX class="h-3 w-3" />
        </button>
      </span>
      <input
        ref="inputEl"
        v-model="draft"
        :placeholder="chips.length ? '' : placeholder"
        :disabled="disabled"
        class="min-w-[60px] flex-1 border-0 bg-transparent text-sm focus:outline-none focus:ring-0"
        @focus="open = true"
        @keydown.enter.prevent="commit"
        @keydown="onKey"
        @blur="onBlur"
      />
    </div>

    <!-- suggestions from the predefined option list -->
    <div
      v-if="open && suggestions.length"
      class="sp-pop absolute left-0 right-0 z-30 mt-1 max-h-48 overflow-auto p-1"
    >
      <button
        v-for="opt in suggestions"
        :key="opt"
        type="button"
        class="flex w-full items-center rounded px-2 py-1 text-left text-sm text-ink-gray-7 hover:bg-surface-gray-3"
        @mousedown.prevent="add(opt)"
      >
        {{ opt }}
      </button>
    </div>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue'

const props = defineProps({
  modelValue: { type: String, default: '' },
  options: { type: Array, default: () => [] },
  placeholder: { type: String, default: 'Add tag…' },
  disabled: { type: Boolean, default: false },
})
const emit = defineEmits(['update:modelValue'])

const inputEl = ref(null)
const draft = ref('')
const open = ref(false)

const chips = computed(() =>
  (props.modelValue || '').split(',').map((c) => c.trim()).filter(Boolean),
)

// predefined options not already chosen, filtered by what's typed
const suggestions = computed(() => {
  const sel = new Set(chips.value)
  const q = draft.value.trim().toLowerCase()
  return props.options.filter((o) => !sel.has(o) && (!q || o.toLowerCase().includes(q)))
})

function emitChips(list) {
  emit('update:modelValue', list.join(','))
}
function add(v) {
  if (props.disabled) return
  if (!v || chips.value.includes(v)) return
  emitChips([...chips.value, v])
  draft.value = ''
  inputEl.value?.focus() // keep the dropdown open for adding more
}
function commit() {
  add(draft.value.trim())
}
function remove(i) {
  if (props.disabled) return
  const list = [...chips.value]
  list.splice(i, 1)
  emitChips(list)
}
function onKey(e) {
  if (props.disabled) return
  if (e.key === ',') {
    e.preventDefault()
    commit()
  } else if (e.key === 'Backspace' && !draft.value && chips.value.length) {
    remove(chips.value.length - 1)
  }
}
function onBlur() {
  if (props.disabled) return
  commit()
  setTimeout(() => (open.value = false), 120)
}
function focusInput() {
  if (props.disabled) return
  inputEl.value?.focus()
}
</script>
