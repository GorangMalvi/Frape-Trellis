<template>
  <Teleport to="body">
    <transition name="sp-fade" appear>
      <div class="fixed inset-0 z-[70] flex items-center justify-center sp-scrim p-4" @click.self="$emit('close')">
        <transition name="sp-pop" appear>
          <div ref="panelEl" v-glass="{ scale: -90, chroma: 6, blur: 4, saturate: 1.7, radius: 22 }"role="dialog" aria-modal="true" aria-label="Space access" class="sp-modal flex max-h-[88vh] w-full max-w-[620px] flex-col overflow-hidden">
            <div class="flex items-center justify-between border-b sp-hair px-5 py-4">
              <div>
                <h2 class="text-base font-semibold text-ink-gray-9">Space access</h2>
                <p class="mt-0.5 text-sm sp-ink-3">{{ config?.space?.label }}</p>
              </div>
              <button class="sp-control p-1.5" @click="$emit('close')"><LucideX class="h-4 w-4" /></button>
            </div>

            <div class="sp-scroll min-h-0 flex-1 overflow-y-auto px-5 py-4">
              <div class="grid gap-3 sm:grid-cols-2">
                <label class="block">
                  <span class="mb-1.5 block text-sm font-medium sp-ink-2">Who can view</span>
                  <select v-model="readAccess" class="h-10 w-full rounded-md border sp-hair bg-surface-white px-3 text-sm focus:outline-none">
                    <option value="All">All</option>
                    <option value="Selected Users">Selected users</option>
                  </select>
                </label>
                <label class="block">
                  <span class="mb-1.5 block text-sm font-medium sp-ink-2">Who can edit</span>
                  <select v-model="writeAccess" class="h-10 w-full rounded-md border sp-hair bg-surface-white px-3 text-sm focus:outline-none">
                    <option value="All">All</option>
                    <option value="Selected Users">Selected users</option>
                  </select>
                </label>
              </div>

              <div class="mt-4 flex gap-2">
                <select v-model="draft" class="h-9 min-w-0 flex-1 rounded-md border sp-hair bg-surface-white px-2 text-sm focus:outline-none">
                  <option value="">Select user...</option>
                  <option v-for="u in availableUsers" :key="u.value" :value="u.value">{{ u.label }}</option>
                </select>
                <Button variant="subtle" @click="add">Add</Button>
              </div>

              <div class="mt-3 overflow-hidden rounded-lg border sp-hair">
                <div class="sticky top-0 z-10 grid grid-cols-[1fr,44px,44px,32px] sm:grid-cols-[1fr,86px,86px,36px] gap-2 border-b sp-hair bg-surface-gray-2 px-3 py-2 text-xs font-semibold uppercase tracking-wide sp-ink-3">
                  <span>User</span>
                  <span>View</span>
                  <span>Edit</span>
                  <span />
                </div>
                <div class="max-h-[44vh] overflow-y-auto">
                  <div
                    v-for="row in users"
                    :key="row.user"
                    class="grid grid-cols-[1fr,44px,44px,32px] sm:grid-cols-[1fr,86px,86px,36px] items-center gap-2 border-b sp-hair px-3 py-2 last:border-0"
                  >
                    <span class="truncate text-sm sp-ink-1">{{ userLabel(row.user) }}</span>
                    <input v-model="row.can_read" type="checkbox" class="rounded" :disabled="row.can_write" />
                    <input v-model="row.can_write" type="checkbox" class="rounded" @change="row.can_read = row.can_read || row.can_write" />
                    <button class="sp-control p-1.5" @click="users = users.filter((x) => x.user !== row.user)">
                      <LucideX class="h-3.5 w-3.5" />
                    </button>
                  </div>
                </div>
                <p v-if="!users.length" class="px-3 py-4 text-center text-sm sp-ink-3">
                  Add users when either mode is set to selected users.
                </p>
              </div>

              <p class="mt-2 text-xs sp-ink-4">Administrator can always access spaces to manage settings.</p>
              <p v-if="error" class="mt-3 text-sm text-ink-red-3">{{ error }}</p>
            </div>

            <div class="flex justify-end gap-2 border-t sp-hair px-5 py-4">
              <Button variant="subtle" @click="$emit('close')">Cancel</Button>
              <AccentButton :loading="saving" @click="save">Save access</AccentButton>
            </div>
          </div>
        </transition>
      </div>
    </transition>
  </Teleport>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { Button, call } from 'frappe-ui'
import AccentButton from '@/components/AccentButton.vue'
import { ensureUsers, userLabel, userOptions } from '@/lib/users'
import { useOverlay } from '@/composables/useOverlay'

const props = defineProps({ space: String, config: Object })
const emit = defineEmits(['close', 'changed'])

const panelEl = ref(null)
useOverlay({ close: () => emit('close'), panel: panelEl })

const readAccess = ref('All')
const writeAccess = ref('All')
const users = ref([])
const draft = ref('')
const saving = ref(false)
const error = ref('')

const availableUsers = computed(() => userOptions().filter((u) => !users.value.some((row) => row.user === u.value)))

onMounted(async () => {
  await ensureUsers()
  const data = await call('sprint.api.get_space_access', { space: props.space })
  readAccess.value = data.read_access || 'All'
  writeAccess.value = data.write_access || 'All'
  users.value = (data.users || []).map((row) => ({ ...row }))
})

function add() {
  if (!draft.value || users.value.some((row) => row.user === draft.value)) return
  users.value.push({ user: draft.value, can_read: true, can_write: false })
  draft.value = ''
}

async function save() {
  error.value = ''
  saving.value = true
  try {
    await call('sprint.api.set_space_access', {
      space: props.space,
      read_access: readAccess.value,
      write_access: writeAccess.value,
      users: JSON.stringify(users.value),
    })
    emit('changed')
    emit('close')
  } catch (e) {
    error.value = e?.messages?.[0] || e?.message || 'Could not save access.'
  } finally {
    saving.value = false
  }
}
</script>
