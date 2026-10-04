<template>
  <Teleport to="body">
    <transition name="sp-fade" appear>
      <div class="fixed inset-0 z-[70] flex items-center justify-center sp-scrim p-4" @click.self="$emit('close')">
        <transition name="sp-pop" appear>
          <div ref="panelEl" v-glass="{ scale: -90, chroma: 6, blur: 4, saturate: 1.7, radius: 22 }"role="dialog" aria-modal="true" aria-label="Ticket members" class="sp-modal max-h-[85vh] w-full max-w-[460px] overflow-y-auto p-5">
            <div class="flex items-center justify-between">
              <div>
                <h2 class="text-base font-semibold text-ink-gray-9">Ticket members</h2>
                <p class="mt-0.5 text-sm sp-ink-3">{{ config?.space?.label }}</p>
              </div>
              <button class="sp-control p-1.5" @click="$emit('close')"><LucideX class="h-4 w-4" /></button>
            </div>

            <div class="mt-4 flex gap-2">
              <select v-model="draft" class="h-9 min-w-0 flex-1 rounded-md border sp-hair bg-surface-white px-2 text-sm focus:outline-none">
                <option value="">Select user…</option>
                <option v-for="u in availableUsers" :key="u.value" :value="u.value">{{ u.label }}</option>
              </select>
              <Button variant="subtle" @click="add">Add</Button>
            </div>

            <div class="mt-3 flex flex-wrap gap-1.5">
              <span v-for="u in members" :key="u" class="sp-chip inline-flex items-center gap-1 px-2 py-1 text-xs">
                {{ userLabel(u) }}
                <button class="sp-ink-3 hover:text-ink-red-3" @click="members = members.filter((x) => x !== u)">
                  <LucideX class="h-3 w-3" />
                </button>
              </span>
            </div>

            <p v-if="error" class="mt-3 text-sm text-ink-red-3">{{ error }}</p>

            <div class="mt-5 flex justify-end gap-2">
              <Button variant="subtle" @click="$emit('close')">Cancel</Button>
              <AccentButton :loading="saving" @click="save">Save members</AccentButton>
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

const draft = ref('')
const members = ref([])
const saving = ref(false)
const error = ref('')

const availableUsers = computed(() => userOptions().filter((u) => !members.value.includes(u.value)))

onMounted(async () => {
  await ensureUsers()
  members.value = await call('sprint.api.get_ticket_members', { space: props.space })
})

function add() {
  if (!draft.value || members.value.includes(draft.value)) return
  members.value.push(draft.value)
  draft.value = ''
}

async function save() {
  error.value = ''
  if (!members.value.length) {
    error.value = 'Add at least one member.'
    return
  }
  saving.value = true
  try {
    await call('sprint.api.set_ticket_members', {
      space: props.space,
      members: JSON.stringify(members.value),
    })
    emit('changed')
    emit('close')
  } catch (e) {
    error.value = e?.messages?.[0] || e?.message || 'Could not save members.'
  } finally {
    saving.value = false
  }
}
</script>
