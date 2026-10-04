import { nextTick, onMounted, onUnmounted, watch } from 'vue'
import { breakpoint } from '@/composables/useBreakpoint'

// One LIFO stack for every open overlay (drawer, dialogs, palette, popovers).
// A single capture-phase keydown listener closes the TOPMOST overlay on
// Escape, so stacked dialogs (confirm over fields-dialog over drawer) unwind
// one layer at a time. Also traps Tab inside the overlay's panel and restores
// focus to the trigger element on close.
const stack = []
let listenerAttached = false

function onGlobalKeydown(e) {
  if (e.key !== 'Escape' || e.defaultPrevented) return
  const top = stack[stack.length - 1]
  if (!top) return
  e.preventDefault()
  e.stopPropagation()
  top.close?.()
}

function ensureListener() {
  if (listenerAttached) return
  window.addEventListener('keydown', onGlobalKeydown, true)
  listenerAttached = true
}

const FOCUSABLE =
  'a[href], button:not([disabled]), input:not([disabled]):not([type="hidden"]), ' +
  'select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])'

function focusables(el) {
  return Array.from(el?.querySelectorAll(FOCUSABLE) || []).filter(
    (n) => n.offsetParent !== null || n === document.activeElement,
  )
}

// useOverlay({ close, panel })            — for overlays mounted with v-if
// useOverlay({ close, panel, active })    — for always-mounted overlays
//                                           toggled by a prop/state getter
// `close` is called on Esc; `panel` is a template ref to the dialog surface.
export function useOverlay({ close, panel, active } = {}) {
  let entry = null
  let restoreTo = null

  function trapTab(e) {
    if (e.key !== 'Tab') return
    const el = panel?.value
    if (!el) return
    const items = focusables(el)
    if (!items.length) {
      e.preventDefault()
      return
    }
    const first = items[0]
    const last = items[items.length - 1]
    if (e.shiftKey && (document.activeElement === first || !el.contains(document.activeElement))) {
      e.preventDefault()
      last.focus()
    } else if (!e.shiftKey && document.activeElement === last) {
      e.preventDefault()
      first.focus()
    }
  }

  function activate() {
    if (entry) return
    ensureListener()
    entry = { close }
    stack.push(entry)
    restoreTo = document.activeElement
    nextTick(() => {
      const el = panel?.value
      if (!el) return
      el.addEventListener('keydown', trapTab)
      // On touch devices, focusing an input on open pops the on-screen
      // keyboard over the dialog — focus the panel itself instead (still
      // required for the Tab trap + Esc handling).
      const auto = breakpoint.isTouch
        ? null
        : el.querySelector('[autofocus]') || focusables(el)[0]
      if (auto) auto.focus()
      else {
        el.tabIndex = -1
        el.focus()
      }
    })
  }

  function deactivate() {
    if (!entry) return
    const i = stack.indexOf(entry)
    if (i >= 0) stack.splice(i, 1)
    entry = null
    panel?.value?.removeEventListener('keydown', trapTab)
    if (restoreTo && document.contains(restoreTo)) restoreTo.focus?.()
    restoreTo = null
  }

  if (active) {
    watch(active, (v) => (v ? activate() : deactivate()), { immediate: true })
    onUnmounted(deactivate)
  } else {
    onMounted(activate)
    onUnmounted(deactivate)
  }
}
