<template>
  <div>
    <textarea
      ref="ta"
      :value="modelValue"
      :rows="rows"
      :placeholder="placeholder"
      class="sp-field w-full resize-y"
      @input="$emit('update:modelValue', $event.target.value)"
      @blur="trackCursor"
      @keyup="trackCursor"
      @click="trackCursor"
    />
    <div class="mt-1.5 flex flex-wrap gap-1">
      <button
        v-for="p in placeholders"
        :key="p"
        type="button"
        class="rounded bg-[var(--sp-fill)] px-1.5 py-0.5 font-mono text-[11px] text-ink-gray-6 transition hover:bg-[var(--sp-fill-hover)] hover:text-ink-gray-8"
        @click="insert(p)"
      >
        {{ '{' + p + '}' }}
      </button>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'

const props = defineProps({
  modelValue: { type: String, default: '' },
  placeholder: { type: String, default: 'Message…' },
  rows: { type: Number, default: 2 },
  placeholders: { type: Array, default: () => ['title', 'assignee', 'bucket', 'due_date', 'space', 'link'] },
})
const emit = defineEmits(['update:modelValue'])

const ta = ref(null)
const caret = ref(null)
function trackCursor() {
  caret.value = ta.value ? ta.value.selectionStart : null
}
function insert(key) {
  const token = '{' + key + '}'
  const text = props.modelValue || ''
  const pos = caret.value == null ? text.length : caret.value
  const next = text.slice(0, pos) + token + text.slice(pos)
  emit('update:modelValue', next)
  const newPos = pos + token.length
  caret.value = newPos
  requestAnimationFrame(() => {
    if (ta.value) {
      ta.value.focus()
      ta.value.setSelectionRange(newPos, newPos)
    }
  })
}
</script>
