<template>
  <aside class="sp-sidebar sp-glass flex w-72 max-w-[85vw] shrink-0 flex-col border-r sp-hair md:w-60">
    <!-- brand -->
    <div class="flex items-center gap-2.5 px-4 pb-3 pt-[calc(env(safe-area-inset-top)+1rem)]">
      <div class="flex h-7 w-7 items-center justify-center rounded-[9px] bg-gradient-to-b from-[#0a84ff] to-[#0071e3] text-sm font-bold text-white shadow-sm">
        S
      </div>
      <span class="sp-display text-[15px] font-semibold sp-ink-1">SASAGEYO</span>
    </div>

    <!-- search trigger -->
    <button
      class="sp-chip mx-3 mb-4 flex items-center gap-2 px-2.5 py-1.5 text-sm sp-ink-3 transition hover:bg-[var(--sp-fill-hover)]"
      @click="openPalette"
    >
      <LucideSearch class="h-3.5 w-3.5" />
      <span>Search…</span>
      <kbd class="ml-auto rounded-md bg-[var(--sp-fill-strong)] px-1.5 py-0.5 text-[10px] font-medium sp-ink-3 [@media(hover:none)]:hidden">⌘K</kbd>
    </button>

    <nav class="sp-scroll flex-1 overflow-y-auto overscroll-contain px-2">
      <!-- home: my tasks + inbox -->
      <button
        class="mb-3 flex w-full items-center gap-2.5 rounded-[10px] px-2 py-1.5 text-left text-sm transition"
        :class="route.name === 'Home' ? 'bg-surface-white font-medium sp-ink-1 shadow-[var(--sp-e1)]' : 'sp-ink-2 hover:bg-[var(--sp-fill)]'"
        @click="router.push({ name: 'Home' })"
      >
        <span class="flex h-6 w-6 items-center justify-center rounded-lg bg-[var(--sp-fill)]">
          <LucideHouse class="h-3.5 w-3.5" />
        </span>
        Home
        <span
          v-if="inbox.unread"
          class="ml-auto rounded-full bg-[color:var(--sp-accent)] px-1.5 py-0.5 text-[10px] font-semibold text-white sp-tnum"
        >
          {{ inbox.unread }}
        </span>
      </button>

      <!-- skeletons -->
      <template v-if="spaces.loading && !spaces.data">
        <div v-for="i in 5" :key="i" class="mb-1 flex items-center gap-2.5 px-2 py-1.5">
          <div class="sp-skeleton h-6 w-6 rounded-lg" />
          <div class="sp-skeleton h-3.5 w-28 rounded" />
        </div>
      </template>

      <div class="px-2 pb-1.5 sp-uppercase">Spaces</div>

      <draggable
        v-model="orderedSpaces"
        item-key="name"
        :animation="160"
        :disabled="!isAdmin"
        ghost-class="sp-ghost"
        v-bind="touchDragOptions"
        @end="persistOrder"
      >
        <template #item="{ element: s }">
          <div :key="s.name" class="group relative mb-0.5">
            <button
              class="flex w-full cursor-grab items-center gap-2.5 rounded-[10px] py-1.5 pl-2 text-left text-sm transition active:cursor-grabbing"
              :class="[
                isAdmin ? 'pr-14' : 'pr-2',
                route.name === 'Board' && s.name === activeSpace
                  ? 'bg-surface-white font-medium sp-ink-1 shadow-[var(--sp-e1)]'
                  : 'sp-ink-2 hover:bg-[var(--sp-fill)]',
              ]"
              @click="open(s)"
            >
              <span
                class="sp-space-icon flex h-6 w-6 shrink-0 items-center justify-center rounded-lg text-sm"
                :style="iconBubbleStyle(s)"
              >
                {{ s.icon || '📋' }}
              </span>
              <span class="truncate">{{ s.label }}</span>
            </button>
            <button
              v-if="isAdmin"
              class="sp-reveal absolute right-7 top-1/2 flex h-6 w-6 -translate-y-1/2 items-center justify-center rounded-md text-ink-gray-4 opacity-0 transition hover:bg-[var(--sp-fill-hover)] hover:text-ink-gray-8 group-hover:opacity-100"
              title="Edit space"
              aria-label="Edit space"
              @click.stop="editSpace(s)"
              @mousedown.stop
            >
              <LucidePencil class="h-3.5 w-3.5" />
            </button>
            <button
              v-if="isAdmin"
              class="sp-reveal absolute right-1 top-1/2 flex h-6 w-6 -translate-y-1/2 items-center justify-center rounded-md text-ink-gray-4 opacity-0 transition hover:bg-[var(--sp-fill-hover)] hover:text-ink-red-3 group-hover:opacity-100"
              title="Delete space"
              aria-label="Delete space"
              @click.stop="deleteSpace(s)"
              @mousedown.stop
            >
              <LucideTrash2 class="h-3.5 w-3.5" />
            </button>
          </div>
        </template>
      </draggable>

      <p
        v-if="spaces.data && !taskSpaces.length"
        class="px-2 py-2 text-xs sp-ink-3"
      >
        No spaces yet.
      </p>

      <button
        v-if="isAdmin"
        class="mt-1 flex w-full items-center gap-2.5 rounded-[10px] px-2 py-1.5 text-left text-sm sp-ink-3 transition hover:bg-[var(--sp-fill)] hover:text-ink-gray-9"
        @click="showNew = true"
      >
        <span class="flex h-6 w-6 items-center justify-center rounded-lg bg-[var(--sp-fill)]">
          <LucidePlus class="h-3.5 w-3.5" />
        </span>
        New space
      </button>

      <div class="mt-5 px-2 pb-1.5 sp-uppercase">Ticketing</div>

      <button
        class="mb-1 flex w-full items-center gap-2.5 rounded-[10px] px-2 py-1.5 text-left text-sm transition"
        :class="route.name === 'TicketIntake' ? 'bg-surface-white font-medium sp-ink-1 shadow-[var(--sp-e1)]' : 'sp-ink-2 hover:bg-[var(--sp-fill)]'"
        @click="openTicketIntake"
      >
        <span class="flex h-6 w-6 items-center justify-center rounded-lg bg-[var(--sp-fill)]">
          <LucideTicketPlus class="h-3.5 w-3.5" />
        </span>
        Raise ticket
      </button>

      <div v-for="s in ticketSpaces" :key="s.name" class="group relative mb-0.5">
        <button
          class="flex w-full items-center gap-2.5 rounded-[10px] py-1.5 pl-2 text-left text-sm transition"
          :class="[
            isAdmin ? 'pr-14' : 'pr-2',
            route.name === 'TicketBoard' && s.name === activeSpace
              ? 'bg-surface-white font-medium sp-ink-1 shadow-[var(--sp-e1)]'
              : 'sp-ink-2 hover:bg-[var(--sp-fill)]',
          ]"
          @click="openTicket(s)"
        >
          <span
            class="sp-space-icon flex h-6 w-6 shrink-0 items-center justify-center rounded-lg text-sm"
            :style="iconBubbleStyle(s)"
          >
            {{ s.icon || 'T' }}
          </span>
          <span class="truncate">{{ s.label }}</span>
        </button>
        <button
          v-if="isAdmin"
          class="sp-reveal absolute right-7 top-1/2 flex h-6 w-6 -translate-y-1/2 items-center justify-center rounded-md text-ink-gray-4 opacity-0 transition hover:bg-[var(--sp-fill-hover)] hover:text-ink-gray-8 group-hover:opacity-100"
          title="Edit ticket space"
          aria-label="Edit ticket space"
          @click.stop="editSpace(s)"
          @mousedown.stop
        >
          <LucidePencil class="h-3.5 w-3.5" />
        </button>
        <button
          v-if="isAdmin"
          class="sp-reveal absolute right-1 top-1/2 flex h-6 w-6 -translate-y-1/2 items-center justify-center rounded-md text-ink-gray-4 opacity-0 transition hover:bg-[var(--sp-fill-hover)] hover:text-ink-red-3 group-hover:opacity-100"
          title="Delete ticket space"
          aria-label="Delete ticket space"
          @click.stop="deleteSpace(s)"
          @mousedown.stop
        >
          <LucideTrash2 class="h-3.5 w-3.5" />
        </button>
      </div>

      <button
        v-if="isAdmin"
        class="mt-1 flex w-full items-center gap-2.5 rounded-[10px] px-2 py-1.5 text-left text-sm sp-ink-3 transition hover:bg-[var(--sp-fill)] hover:text-ink-gray-9"
        @click="showNewTicket = true"
      >
        <span class="flex h-6 w-6 items-center justify-center rounded-lg bg-[var(--sp-fill)]">
          <LucidePlus class="h-3.5 w-3.5" />
        </span>
        New ticket space
      </button>
    </nav>

    <div class="border-t sp-hair px-3 pt-3 pb-[calc(env(safe-area-inset-bottom)+0.75rem)]">
      <!-- current user: account / manage users / sign out -->
      <UserMenu class="mb-3" />

      <!-- appearance -->
      <p class="sp-uppercase mb-1.5 px-1">Appearance</p>
      <div class="sp-chip mb-3 flex gap-0.5 p-0.5">
        <button
          v-for="m in APPEARANCES"
          :key="m.key"
          class="flex flex-1 items-center justify-center gap-1 rounded-[7px] py-1 text-xs font-medium transition"
          :class="theme.appearance === m.key ? 'sp-seg-active text-ink-gray-9' : 'sp-ink-3 hover:text-ink-gray-8'"
          @click="setAppearance(m.key)"
        >
          <LucideSun v-if="m.key === 'light'" class="h-3.5 w-3.5" />
          <LucideMoon v-else-if="m.key === 'dark'" class="h-3.5 w-3.5" />
          <LucideSparkles v-else class="h-3.5 w-3.5" />
          {{ m.label }}
        </button>
      </div>

      <p class="px-1 text-[11px] leading-relaxed sp-ink-3">
        Developed by <span class="font-medium sp-ink-2">Manas</span>
      </p>
    </div>

    <NewSpaceDialog v-if="showNew" @close="showNew = false" @created="onCreated" />
    <NewTicketSpaceDialog v-if="showNewTicket" @close="showNewTicket = false" @created="onTicketCreated" />
    <SpaceSettingsDialog
      v-if="editingSpace"
      :space="editingSpace"
      @close="editingSpace = null"
      @changed="onSpaceSettingsChanged"
    />
  </aside>
</template>

<script setup>
import { computed, onUnmounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { createResource, call } from 'frappe-ui'
import draggable from 'vuedraggable'
import { touchDragOptions } from '@/lib/dnd'
import { openPalette, subscribeDoctype, theme, setAppearance, confirmDelete, pushToast, errorMessage, inbox, setUnread } from '@/store'
import { session } from '@/lib/users'
import NewSpaceDialog from '@/components/NewSpaceDialog.vue'
import NewTicketSpaceDialog from '@/components/NewTicketSpaceDialog.vue'
import SpaceSettingsDialog from '@/components/SpaceSettingsDialog.vue'
import UserMenu from '@/components/UserMenu.vue'

// Administrator — may delete spaces
const isAdmin = computed(() => session.canManage)

const APPEARANCES = [
  { key: 'light', label: 'Light' },
  { key: 'dark', label: 'Dark' },
  { key: 'glass', label: 'Glass' },
]

const showNew = ref(false)
const showNewTicket = ref(false)
const editingSpace = ref(null)
async function onCreated(name) {
  showNew.value = false
  await spaces.reload()
  router.push({ name: 'Board', params: { space: name } })
}
async function onTicketCreated(name) {
  showNewTicket.value = false
  await spaces.reload()
  router.push({ name: 'TicketBoard', params: { space: name } })
}

const route = useRoute()
const router = useRouter()
const activeSpace = computed(() => route.params.space)

const spaces = createResource({
  url: 'sprint.api.get_spaces',
  auto: true,
})
const taskSpaces = computed(() => (spaces.data || []).filter((s) => (s.space_type || 'Task') !== 'Ticket'))
const ticketSpaces = computed(() => (spaces.data || []).filter((s) => (s.space_type || 'Task') === 'Ticket'))

// unread badge on the Home entry; the socket handler bumps it live
call('sprint.api.get_unread_notification_count').then(setUnread).catch(() => {})

function open(s) {
  router.push({ name: 'Board', params: { space: s.name } })
}
function openTicket(s) {
  rememberTicketSpace(s.name)
  router.push({ name: 'TicketBoard', params: { space: s.name } })
}

function openTicketIntake() {
  const space = route.name === 'TicketBoard' ? activeSpace.value : lastTicketSpace()
  router.push({ name: 'TicketIntake', query: space ? { space } : {} })
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

function iconBubbleStyle(s) {
  const color = s?.color || '#8e8e93'
  return {
    background: `linear-gradient(135deg, ${color}ee 0%, ${color}99 100%)`,
  }
}

function editSpace(s) {
  editingSpace.value = s
}

async function onSpaceSettingsChanged() {
  editingSpace.value = null
  await spaces.reload()
}

// Administrator-only: delete a space (2-step — confirm, then password).
async function deleteSpace(s) {
  const ok = await confirmDelete({
    title: `Delete space “${s.label}”?`,
    message: 'This permanently deletes the space and all of its cards. This cannot be undone.',
    confirmLabel: 'Delete space',
    requirePassword: true,
  })
  if (!ok) return
  try {
    const wasActive = s.name === activeSpace.value
    await call('sprint.api.delete_space', { space: s.name })
    await spaces.reload()
    if (wasActive) {
      const next = (spaces.data || [])[0]
      if (next) router.replace({ name: 'Board', params: { space: next.name } })
      else router.replace({ name: 'Home' })
    }
  } catch (e) {
    pushToast(errorMessage(e))
  }
}

// local, reorderable copy of the spaces list
const orderedSpaces = ref([])
watch(
  () => spaces.data,
  (d) => {
    orderedSpaces.value = [...(d || []).filter((s) => (s.space_type || 'Task') !== 'Ticket')]
  },
  { immediate: true },
)

async function persistOrder() {
  await call('sprint.api.reorder_spaces', {
    names: JSON.stringify(orderedSpaces.value.map((s) => s.name)),
  })
}

// realtime: refresh the space list when another user adds/renames/reorders/deletes a space
const unsub = subscribeDoctype('SP Space', () => spaces.reload())
onUnmounted(() => unsub())
</script>
