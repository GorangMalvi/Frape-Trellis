<template>
  <div class="relative flex h-full flex-col sp-ground text-ink-gray-9 md:flex-row">
    <!-- Glass theme: full-bleed photographic backdrop the glass surfaces refract
         (hidden on the noShell auth pages, which own their own backdrop) -->
    <div
      v-if="isGlass && !noShell"
      class="sp-app-backdrop"
      :style="{ backgroundImage: `url(${appBg})` }"
      aria-hidden="true"
    />
    <MobileTopBar v-if="!noShell" />
    <!-- scrim behind the mobile sidebar drawer -->
    <transition name="sp-fade">
      <div
        v-if="!noShell && ui.sidebarOpen"
        class="sp-scrim fixed inset-0 z-40 touch-none md:hidden"
        @click="closeSidebar"
      />
    </transition>
    <!-- On phones the sidebar is an off-canvas drawer; from md: it is the
         static column it always was. -->
    <Sidebar
      v-if="!noShell"
      ref="sidebarEl"
      class="sp-drawer fixed inset-y-0 left-0 z-50 md:static md:z-10 md:translate-x-0"
      :class="ui.sidebarOpen ? 'max-md:translate-x-0' : 'max-md:-translate-x-full'"
    />
    <main class="relative z-10 min-w-0 flex-1">
      <router-view />
    </main>
    <template v-if="!noShell">
      <CommandPalette />
      <ConfirmDialog
        :open="confirm.open"
        :title="confirm.title"
        :message="confirm.message"
        :confirm-label="confirm.confirmLabel"
        :require-password="confirm.requirePassword"
        @confirm="resolveConfirm(true)"
        @cancel="resolveConfirm(false)"
      />
    </template>
    <ToastHost />
  </div>
</template>

<script setup>
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import Sidebar from '@/components/Sidebar.vue'
import MobileTopBar from '@/components/MobileTopBar.vue'
import CommandPalette from '@/components/CommandPalette.vue'
import ToastHost from '@/components/ToastHost.vue'
import ConfirmDialog from '@/components/ConfirmDialog.vue'
import { ui, theme, openPalette, closePalette, closeSidebar, triggerNewTask, triggerRefresh, confirm, resolveConfirm } from '@/store'
import { useOverlay } from '@/composables/useOverlay'
import { breakpoint } from '@/composables/useBreakpoint'
import appBg from '@/assets/app-bg.webp'

// Login / set-password render full-screen — no sidebar, palette or confirm.
const route = useRoute()
const noShell = computed(() => !!route.meta.noShell)

// Mobile sidebar drawer: Esc/focus handling only while it actually overlays
// content — on desktop the sidebar is static and must NOT trap focus.
const sidebarEl = ref(null)
const sidebarPanel = computed(() => sidebarEl.value?.$el)
useOverlay({
  close: closeSidebar,
  panel: sidebarPanel,
  active: () => ui.sidebarOpen && breakpoint.isMobile && !noShell.value,
})
watch(() => route.fullPath, closeSidebar)
watch(() => breakpoint.isMobile, (m) => !m && closeSidebar())
// Glass theme: show the app-wide photographic backdrop behind the glass surfaces.
const isGlass = computed(() => theme.appearance === 'glass')

function isTyping(e) {
  const el = e.target
  return (
    el &&
    (el.tagName === 'INPUT' ||
      el.tagName === 'TEXTAREA' ||
      el.isContentEditable)
  )
}

function onKey(e) {
  // ⌘K / Ctrl+K toggles the palette from anywhere
  if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k') {
    e.preventDefault()
    ui.paletteOpen ? closePalette() : openPalette()
    return
  }
  // Escape is handled by the overlay stack (useOverlay) — closes topmost layer
  if (isTyping(e) || e.metaKey || e.ctrlKey || e.altKey) return

  // single-key shortcuts (only when not typing)
  if (e.key === '/') {
    e.preventDefault()
    openPalette()
  } else if (e.key.toLowerCase() === 'c') {
    triggerNewTask()
  } else if (e.key.toLowerCase() === 'r') {
    triggerRefresh()
  }
}

onMounted(() => window.addEventListener('keydown', onKey))
onUnmounted(() => window.removeEventListener('keydown', onKey))
</script>
