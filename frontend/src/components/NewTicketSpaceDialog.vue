<template>
  <Teleport to="body">
    <transition name="sp-fade" appear>
      <div class="fixed inset-0 z-[70] flex items-center justify-center sp-scrim p-4 backdrop-blur-md" @click.self="$emit('close')">
        <transition name="sp-pop" appear>
          <div ref="panelEl" v-glass="{ scale: -90, chroma: 6, blur: 4, saturate: 1.7, radius: 22 }"role="dialog" aria-modal="true" aria-label="New ticket space" class="sp-modal max-h-[88vh] w-full max-w-[520px] overflow-auto p-5">
            <h2 class="sp-display text-lg font-semibold text-ink-gray-9">New ticket space</h2>

            <div class="mt-4">
              <label class="mb-1 block text-sm font-medium sp-ink-2">Name</label>
              <input
                v-model="label"
                ref="nameEl"
                placeholder="Ticket space name"
                class="h-9 w-full rounded-md border sp-hair px-2.5 text-sm focus:border-outline-gray-3 focus:outline-none"
                @keyup.enter="create"
              />
            </div>

            <div class="mt-3">
              <p class="mb-2 text-sm font-medium sp-ink-2">Icon</p>
              <div class="grid grid-cols-[repeat(auto-fill,minmax(2.25rem,1fr))] gap-1.5">
                <button
                  v-for="item in ICONS"
                  :key="item"
                  class="sp-space-icon-choice flex h-8 w-8 items-center justify-center rounded-md text-base transition hover:bg-[var(--sp-fill-hover)]"
                  :class="icon === item ? 'sp-space-icon-choice-active' : 'bg-[var(--sp-fill)]'"
                  @click="icon = item"
                >
                  {{ item }}
                </button>
              </div>
              <input
                v-model="icon"
                class="mt-2 h-9 w-20 rounded-md border sp-hair px-2.5 text-center text-base focus:border-outline-gray-3 focus:outline-none"
                maxlength="4"
              />
            </div>

            <div class="mt-3 flex items-center gap-1.5">
              <span class="mr-1 text-xs sp-ink-3">Color</span>
              <button
                v-for="c in COLORS"
                :key="c"
                class="h-5 w-5 rounded-full transition"
                :class="color === c ? 'ring-2 ring-offset-1 ring-ink-gray-5' : ''"
                :style="{ background: c }"
                @click="color = c"
              />
            </div>

            <div class="mt-4">
              <p class="sp-uppercase mb-1.5">Members</p>
              <div class="flex gap-2">
                <select v-model="memberDraft" class="h-9 min-w-0 flex-1 rounded-md border sp-hair bg-surface-white px-2 text-sm focus:outline-none">
                  <option value="">Select user…</option>
                  <option v-for="u in availableUsers" :key="u.value" :value="u.value">{{ u.label }}</option>
                </select>
                <Button variant="subtle" @click="addMember">Add</Button>
              </div>
              <div class="mt-2 flex flex-wrap gap-1.5">
                <span v-for="u in members" :key="u" class="sp-chip inline-flex items-center gap-1 px-2 py-1 text-xs">
                  {{ userLabel(u) }}
                  <button class="sp-ink-3 hover:text-ink-red-3" @click="members = members.filter((x) => x !== u)">
                    <LucideX class="h-3 w-3" />
                  </button>
                </span>
              </div>
            </div>

            <div class="mt-4">
              <p class="sp-uppercase mb-1.5">Buckets</p>
              <div class="flex flex-col gap-1.5">
                <div v-for="(b, i) in buckets" :key="i" class="flex items-center gap-2">
                  <input v-model="b.bucket_name" class="h-8 flex-1 rounded-md border sp-hair px-2.5 text-sm focus:border-outline-gray-3 focus:outline-none" />
                  <button class="sp-control p-1.5" @click="buckets.splice(i, 1)"><LucideX class="h-3.5 w-3.5" /></button>
                </div>
              </div>
              <button class="mt-1.5 flex items-center gap-1 text-sm sp-ink-2 hover:text-ink-gray-8" @click="buckets.push({ bucket_name: '' })">
                <LucidePlus class="h-3.5 w-3.5" /> Add bucket
              </button>
            </div>

            <p v-if="error" class="mt-3 text-sm text-ink-red-3">{{ error }}</p>

            <div class="mt-5 flex justify-end gap-2">
              <Button variant="subtle" @click="$emit('close')">Cancel</Button>
              <AccentButton :loading="creating" @click="create">Create ticket space</AccentButton>
            </div>
          </div>
        </transition>
      </div>
    </transition>
  </Teleport>
</template>

<script setup>
import { computed, nextTick, onMounted, ref } from 'vue'
import { Button, call } from 'frappe-ui'
import AccentButton from '@/components/AccentButton.vue'
import { bucketColorFor } from '@/lib/board'
import { ensureUsers, userLabel, userOptions } from '@/lib/users'
import { SPACE_COLORS, SPACE_ICONS } from '@/lib/spaceOptions'
import { useOverlay } from '@/composables/useOverlay'
import { breakpoint } from '@/composables/useBreakpoint'

const emit = defineEmits(['close', 'created'])

const panelEl = ref(null)
useOverlay({ close: () => emit('close'), panel: panelEl })

const COLORS = SPACE_COLORS
const ICONS = SPACE_ICONS

const label = ref('')
const icon = ref('T')
const color = ref(COLORS[0])
const memberDraft = ref('')
const members = ref([])
const buckets = ref([{ bucket_name: 'Open' }, { bucket_name: 'In Progress' }, { bucket_name: 'Closed' }])
const creating = ref(false)
const error = ref('')
const nameEl = ref(null)

const availableUsers = computed(() => userOptions().filter((u) => !members.value.includes(u.value)))

onMounted(async () => {
  await ensureUsers()
  nextTick(() => !breakpoint.isTouch && nameEl.value?.focus())
})

function addMember() {
  if (!memberDraft.value || members.value.includes(memberDraft.value)) return
  members.value.push(memberDraft.value)
  memberDraft.value = ''
}

async function create() {
  error.value = ''
  if (!label.value.trim()) {
    error.value = 'Please enter a ticket space name.'
    return
  }
  if (!members.value.length) {
    error.value = 'Add at least one member.'
    return
  }
  creating.value = true
  try {
    const res = await call('sprint.api.create_ticket_space_api', {
      label: label.value.trim(),
      icon: icon.value,
      color: color.value,
      members: JSON.stringify(members.value),
      buckets: JSON.stringify(
        buckets.value
          .filter((b) => b.bucket_name.trim())
          .map((b, i) => ({ bucket_name: b.bucket_name.trim(), color: bucketColorFor(b.bucket_name, i) })),
      ),
    })
    emit('created', res.name)
  } catch (e) {
    error.value = e?.messages?.[0] || e?.message || 'Could not create ticket space.'
  } finally {
    creating.value = false
  }
}
</script>
