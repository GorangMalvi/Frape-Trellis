<template>
  <Teleport to="body">
    <transition name="sp-fade">
      <div
        v-if="ui.paletteOpen"
        class="fixed inset-0 z-[60] flex items-start justify-center sp-scrim px-4 pt-[6vh] backdrop-blur-md md:pt-[12vh]"
        @click.self="close"
      >
        <transition name="sp-pop" appear>
          <div ref="panelEl" v-glass="{ scale: -100, chroma: 6, blur: 5, saturate: 1.7, radius: 22 }"role="dialog" aria-modal="true" aria-label="Command palette" class="sp-modal w-full max-w-[640px] overflow-hidden">
            <!-- input -->
            <div class="flex items-center gap-2 border-b sp-hair px-4">
              <LucideSearch class="h-4 w-4 text-ink-gray-5" />
              <input
                ref="inputEl"
                v-model="query"
                placeholder="Search spaces, tasks, or run a command…"
                class="w-full bg-transparent py-3.5 text-sm text-ink-gray-9 placeholder:text-ink-gray-4 focus:outline-none"
                @keydown.down.prevent="move(1)"
                @keydown.up.prevent="move(-1)"
                @keydown.enter.prevent="run(flat[active])"
              />
              <kbd class="rounded bg-surface-gray-3 px-1.5 py-0.5 text-[10px] text-ink-gray-6 [@media(hover:none)]:hidden">esc</kbd>
            </div>

            <!-- results -->
            <div ref="listEl" class="sp-scroll max-h-[60dvh] overflow-y-auto py-2 md:max-h-[52vh]">
              <template v-for="section in sections" :key="section.title">
                <div v-if="section.items.length" class="px-2">
                  <p class="px-2 py-1 text-[11px] font-semibold uppercase tracking-wider text-ink-gray-4">
                    {{ section.title }}
                  </p>
                  <button
                    v-for="item in section.items"
                    :key="item.key"
                    :data-idx="item._idx"
                    class="flex w-full items-center gap-2.5 rounded-[10px] px-2.5 py-2 text-left text-sm transition"
                    :class="item._idx === active ? 'bg-[var(--sp-accent-tint)] text-ink-gray-9' : 'hover:bg-[var(--sp-fill)]'"
                    @mousemove="active = item._idx"
                    @click="run(item)"
                  >
                    <span class="flex h-5 w-5 shrink-0 items-center justify-center">
                      <LucidePlus v-if="item.kind === 'new'" class="h-4 w-4 text-ink-gray-6" />
                      <LucideRefreshCw v-else-if="item.kind === 'refresh'" class="h-4 w-4 text-ink-gray-6" />
                      <LucideCircleDot v-else-if="item.kind === 'card'" class="h-4 w-4 text-ink-gray-5" />
                      <span v-else class="text-sm">{{ item.emoji || '•' }}</span>
                    </span>
                    <span class="truncate text-ink-gray-8">{{ item.label }}</span>
                    <kbd
                      v-if="item.hint"
                      class="ml-auto rounded bg-surface-gray-3 px-1.5 py-0.5 text-[10px] text-ink-gray-6 [@media(hover:none)]:hidden"
                    >
                      {{ item.hint }}
                    </kbd>
                  </button>
                </div>
              </template>

              <p v-if="!flat.length" class="px-4 py-6 text-center text-sm text-ink-gray-4">
                No results for “{{ query }}”
              </p>
            </div>
          </div>
        </transition>
      </div>
    </transition>
  </Teleport>
</template>

<script setup>
import { computed, nextTick, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { createResource } from 'frappe-ui'
import { ui, closePalette, openCard, triggerNewTask, triggerRefresh } from '@/store'
import { useOverlay } from '@/composables/useOverlay'

const route = useRoute()
const router = useRouter()

const query = ref('')
const active = ref(0)
const inputEl = ref(null)
const listEl = ref(null)
const panelEl = ref(null)
useOverlay({ close: closePalette, panel: panelEl, active: () => ui.paletteOpen })

const spaces = createResource({ url: 'sprint.api.get_spaces' })
const cards = createResource({ url: 'sprint.api.get_cards' })

watch(
  () => ui.paletteOpen,
  (open) => {
    if (!open) return
    query.value = ''
    active.value = 0
    spaces.fetch()
    if (route.params.space) cards.fetch({ space: route.params.space })
    nextTick(() => inputEl.value?.focus())
  },
)

function close() {
  closePalette()
}

const COMMANDS = [
  { key: 'cmd-new', kind: 'new', label: 'New task', hint: 'C', action: triggerNewTask },
  { key: 'cmd-refresh', kind: 'refresh', label: 'Refresh board', hint: 'R', action: triggerRefresh },
]

function match(text) {
  return (text || '').toLowerCase().includes(query.value.toLowerCase())
}

const sections = computed(() => {
  const q = query.value.trim()
  const cmds = COMMANDS.filter((c) => !q || match(c.label)).map((c) => ({ ...c }))
  const sp = (spaces.data || [])
    .filter((s) => !q || match(s.label))
    .map((s) => ({ key: 's-' + s.name, kind: 'space', label: s.label, emoji: s.icon || '📋', name: s.name }))
  const cd = !q
    ? []
    : (cards.data || [])
        .filter((c) => match(c.title || c.subject || c.name))
        .slice(0, 8)
        .map((c) => ({ key: 'c-' + c.name, kind: 'card', label: c.title || c.subject || c.name, name: c.name }))

  const out = [
    { title: 'Actions', items: cmds },
    { title: 'Spaces', items: sp },
    { title: 'Tasks', items: cd },
  ]
  let i = 0
  for (const s of out) for (const it of s.items) it._idx = i++
  return out
})

const flat = computed(() => sections.value.flatMap((s) => s.items))

watch(flat, () => {
  if (active.value >= flat.value.length) active.value = 0
})

function move(delta) {
  const n = flat.value.length
  if (!n) return
  active.value = (active.value + delta + n) % n
  nextTick(() => {
    listEl.value?.querySelector(`[data-idx="${active.value}"]`)?.scrollIntoView({ block: 'nearest' })
  })
}

function run(item) {
  if (!item) return
  if (item.action) item.action()
  else if (item.kind === 'space') {
    router.push({ name: 'Board', params: { space: item.name } })
    closePalette()
  } else if (item.kind === 'card') {
    openCard(item.name)
  }
}
</script>
