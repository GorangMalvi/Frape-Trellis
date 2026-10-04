<template>
  <Autocomplete
    :options="options"
    :model-value="modelValue || ''"
    :placeholder="placeholder || 'Select…'"
    :disabled="disabled"
    @update:model-value="onUpdate"
  />
</template>

<script setup>
import { ref, onMounted, watch } from 'vue'
import { Autocomplete, call } from 'frappe-ui'
import { ensureUsers, userOptions } from '@/lib/users'

const props = defineProps({
  modelValue: String,
  doctype: String,
  placeholder: String,
  options: Array,
  disabled: { type: Boolean, default: false },
})
const emit = defineEmits(['update:modelValue'])

const options = ref([])

onMounted(load)
watch(() => props.options, load)

async function load() {
  if (props.options) {
    options.value = [{ label: '—', value: '' }, ...props.options]
    return
  }
  if (props.doctype === 'User') {
    await ensureUsers()
    options.value = [{ label: '—', value: '' }, ...userOptions()]
  } else {
    const rows = await call('frappe.client.get_list', {
      doctype: props.doctype,
      fields: ['name'],
      limit_page_length: 100,
      order_by: 'modified desc',
    })
    options.value = [{ label: '—', value: '' }, ...rows.map((r) => ({ label: r.name, value: r.name }))]
  }
}

function onUpdate(val) {
  if (props.disabled) return
  emit('update:modelValue', val?.value ?? val ?? '')
}
</script>
