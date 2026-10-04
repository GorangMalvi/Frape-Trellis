<template>
  <div class="flex h-full flex-col">
    <header class="sp-glass-strong z-20 flex items-center justify-center px-6 py-4 text-center">
      <div class="w-full max-w-3xl">
        <h1 class="sp-display text-[18px] font-semibold sp-ink-1">Raise ticket</h1>
      </div>
    </header>

    <main class="sp-scroll flex min-h-0 flex-1 justify-center overflow-y-auto px-4 py-6 md:px-6">
      <div class="w-full max-w-3xl">
        <div v-if="spaces.loading && !spaces.data" class="space-y-3">
          <div class="sp-skeleton h-9 w-64 rounded" />
          <div class="sp-skeleton h-32 w-full rounded-lg" />
        </div>

        <div v-else-if="!ticketSpaces.length" class="rounded-lg border sp-hair bg-surface-white p-5">
          <p class="text-sm sp-ink-2">No ticket spaces are available.</p>
        </div>

        <div v-else class="space-y-5">
          <label class="block">
            <span class="mb-1.5 block text-sm font-medium sp-ink-2">Ticket space</span>
            <select v-model="selectedSpace" class="h-10 w-full rounded-md border sp-hair bg-surface-white px-3 text-sm focus:outline-none">
              <option v-for="s in ticketSpaces" :key="s.name" :value="s.name">{{ s.label }}</option>
            </select>
          </label>

          <div v-if="config.loading && !cfg" class="sp-skeleton h-48 rounded-lg" />

          <div v-else-if="cfg" class="rounded-lg border sp-hair bg-surface-white p-5">
            <div class="grid gap-4">
              <label class="block">
                <span class="mb-1.5 block text-sm font-medium sp-ink-2">Title *</span>
                <input v-model="form.title" class="h-10 w-full rounded-md border sp-hair px-3 text-sm focus:border-outline-gray-3 focus:outline-none" />
              </label>

              <label class="block">
                <span class="mb-1.5 block text-sm font-medium sp-ink-2">Description</span>
                <textarea v-model="form.description" rows="6" class="w-full resize-y rounded-md border sp-hair px-3 py-2 text-sm focus:border-outline-gray-3 focus:outline-none" />
              </label>

              <div class="grid gap-4 sm:grid-cols-2">
                <label class="block">
                  <span class="mb-1.5 block text-sm font-medium sp-ink-2">Priority</span>
                  <select v-model="form.priority" class="h-10 w-full rounded-md border sp-hair bg-surface-white px-3 text-sm focus:outline-none">
                    <option v-for="p in priorities" :key="p" :value="p">{{ p }}</option>
                  </select>
                </label>

                <label class="block">
                  <span class="mb-1.5 block text-sm font-medium sp-ink-2">Responsible person *</span>
                  <select v-model="form.assignee" class="h-10 w-full rounded-md border sp-hair bg-surface-white px-3 text-sm focus:outline-none">
                    <option value="">Select person…</option>
                    <option v-for="u in memberOptions" :key="u.value" :value="u.value">{{ u.label }}</option>
                  </select>
                </label>
              </div>

              <div v-if="customFields.length" class="grid gap-4 sm:grid-cols-2">
                <label v-for="f in customFields" :key="f.fieldname" class="block">
                  <span class="mb-1.5 block text-sm font-medium sp-ink-2">{{ f.label }}{{ fieldRequired(f) ? ' *' : '' }}</span>
                  <ChipField
                    v-if="chipFields.includes(f.fieldname)"
                    :model-value="values[f.fieldname] || ''"
                    :options="chipOptions[f.fieldname] || []"
                    :disabled="fieldReadOnly(f)"
                    @update:model-value="(v) => (values[f.fieldname] = v)"
                  />
                  <select
                    v-else-if="f.fieldtype === 'Select'"
                    v-model="values[f.fieldname]"
                    :disabled="fieldReadOnly(f)"
                    class="h-10 w-full rounded-md border sp-hair bg-surface-white px-3 text-sm focus:outline-none disabled:cursor-not-allowed disabled:opacity-60"
                  >
                    <option value="">—</option>
                    <option v-for="o in (f.options || '').split('\n').filter(Boolean)" :key="o" :value="o">{{ o }}</option>
                  </select>
                  <input
                    v-else-if="f.fieldtype === 'Date'"
                    v-model="values[f.fieldname]"
                    type="date"
                    :disabled="fieldReadOnly(f)"
                    class="h-10 w-full rounded-md border sp-hair px-3 text-sm focus:outline-none disabled:cursor-not-allowed disabled:opacity-60"
                  />
                  <input
                    v-else
                    v-model="values[f.fieldname]"
                    :disabled="fieldReadOnly(f)"
                    class="h-10 w-full rounded-md border sp-hair px-3 text-sm focus:outline-none disabled:cursor-not-allowed disabled:opacity-60"
                  />
                </label>
              </div>
            </div>

            <p v-if="error" class="mt-4 text-sm text-ink-red-3">{{ error }}</p>

            <div class="mt-5 flex justify-end">
              <AccentButton :loading="submitting" @click="submit">Submit ticket</AccentButton>
            </div>
          </div>
        </div>
      </div>
    </main>
  </div>
</template>

<script setup>
import { computed, onMounted, onUnmounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { call, createResource } from 'frappe-ui'
import AccentButton from '@/components/AccentButton.vue'
import ChipField from '@/components/ChipField.vue'
import { fieldIsMandatory, fieldIsReadOnly, fieldIsVisible } from '@/lib/depends'
import { ensureUsers, userLabel } from '@/lib/users'
import { useSpacePointers } from '@/composables/useSpacePointers'
import { errorMessage } from '@/store'

const router = useRouter()
const route = useRoute()

const selectedSpace = ref('')
const members = ref([])
const form = reactive({ title: '', description: '', priority: 'Medium', assignee: '' })
const values = reactive({})
const submitting = ref(false)
const error = ref('')

const spaces = createResource({
  url: 'sprint.api.get_spaces',
  auto: true,
  onSuccess(data) {
    selectInitialSpace(data || [])
  },
})
const config = createResource({
  url: 'sprint.api.get_space',
  makeParams: () => ({ space: selectedSpace.value }),
})

const ticketSpaces = computed(() => (spaces.data || []).filter((s) => (s.space_type || 'Task') === 'Ticket'))
const cfg = computed(() => config.data)
const { chipFields, chipOptions } = useSpacePointers(cfg)
const priorities = computed(() => {
  const f = (cfg.value?.fields || []).find((x) => x.fieldname === (cfg.value?.space?.badge_field || 'priority'))
  return (f?.options || 'Low\nMedium\nHigh\nUrgent').split('\n').filter(Boolean)
})
const memberOptions = computed(() => members.value.map((u) => ({ label: userLabel(u), value: u })))
const customFields = computed(() => {
  const hidden = new Set([
    cfg.value?.space?.title_field || 'title',
    cfg.value?.space?.body_field || 'description',
    cfg.value?.space?.bucket_field || 'bucket',
    cfg.value?.space?.assignee_field || 'assignee',
    cfg.value?.space?.badge_field || 'priority',
    cfg.value?.space?.parent_field || 'parent_task',
    'requester',
    'position',
  ])
  return (cfg.value?.fields || []).filter((f) => !hidden.has(f.fieldname) && fieldVisible(f))
})
function fieldVisible(f) {
  return fieldIsVisible(f, dependencyDoc())
}
function fieldRequired(f) {
  return fieldIsMandatory(f, dependencyDoc())
}
function fieldReadOnly(f) {
  return fieldIsReadOnly(f, dependencyDoc())
}
function dependencyDoc() {
  return { ...form, ...values }
}

function selectInitialSpace(data) {
  const tickets = (data || []).filter((s) => (s.space_type || 'Task') === 'Ticket')
  if (!tickets.length) return
  const valid = new Set(tickets.map((s) => s.name))
  if (selectedSpace.value && valid.has(selectedSpace.value)) return
  const querySpace = typeof route.query.space === 'string' ? route.query.space : ''
  const storedSpace = lastTicketSpace()
  selectedSpace.value = [querySpace, storedSpace, tickets[0].name].find((space) => valid.has(space)) || tickets[0].name
}

function rememberTicketSpace(space) {
  try {
    localStorage.setItem('sprint.lastTicketSpace', space)
  } catch { /* ignore */ }
}

function lastTicketSpace() {
  try {
    return localStorage.getItem('sprint.lastTicketSpace') || ''
  } catch {
    return ''
  }
}

async function refreshCurrentConfig() {
  if (!selectedSpace.value) return
  await config.fetch()
}

function refreshOnVisible() {
  if (document.visibilityState === 'visible') refreshCurrentConfig()
}

watch(
  selectedSpace,
  async (space) => {
    if (!space) return
    rememberTicketSpace(space)
    error.value = ''
    Object.keys(values).forEach((k) => delete values[k])
    form.title = ''
    form.description = ''
    form.priority = 'Medium'
    form.assignee = ''
    await ensureUsers()
    await config.fetch()
    members.value = await call('sprint.api.get_ticket_members', { space })
    form.assignee = members.value[0] || ''
    if (priorities.value.length && !priorities.value.includes(form.priority)) form.priority = priorities.value[0]
  },
  { immediate: true },
)

onMounted(() => {
  window.addEventListener('focus', refreshCurrentConfig)
  document.addEventListener('visibilitychange', refreshOnVisible)
})

onUnmounted(() => {
  window.removeEventListener('focus', refreshCurrentConfig)
  document.removeEventListener('visibilitychange', refreshOnVisible)
})

async function submit() {
  error.value = ''
  if (!selectedSpace.value || !cfg.value) return
  if (!form.title.trim()) {
    error.value = 'Title is required.'
    return
  }
  if (!form.assignee) {
    error.value = 'Responsible person is required.'
    return
  }
  for (const f of customFields.value.filter((x) => fieldRequired(x))) {
    if (values[f.fieldname] == null || String(values[f.fieldname]).trim() === '') {
      error.value = `${f.label} is required.`
      return
    }
  }
  submitting.value = true
  try {
    const bucket = (cfg.value.buckets || [])[0]?.name || ''
    const res = await call('sprint.api.create_ticket', {
      space: selectedSpace.value,
      title: form.title.trim(),
      description: form.description,
      assignee: form.assignee,
      priority: form.priority,
      bucket,
      values: JSON.stringify(values),
    })
    router.push({ name: 'TicketBoard', params: { space: selectedSpace.value }, query: { ticket: res.name } })
  } catch (e) {
    error.value = errorMessage(e, 'Could not submit ticket.')
  } finally {
    submitting.value = false
  }
}
</script>
