// v-glass — apply real liquid-glass SVG refraction to an element, but ONLY when
// the "Glass" appearance is active (and transparency isn't reduced). Inert in
// Light/Dark, so it's a safe no-op to sprinkle on any hero panel. Reacts live to
// theme toggles and cleans up on unmount.
//
// Usage: <div class="sp-modal" v-glass="{ scale:-90, blur:4, radius:22 }">…</div>
//
// The CSS `[data-glass]` skin already frosts every surface; this upgrades the
// floating hero panels (palette, drawer, dialogs, bulk bar) to true refraction.
import { watch } from 'vue'
import liquidGlass from '@/lib/liquidGlass'
import { theme } from '@/store'

const entries = new Map() // el -> { opts, handle }
let watching = false

function reduceTransparency() {
  return (
    typeof window !== 'undefined' &&
    window.matchMedia &&
    window.matchMedia('(prefers-reduced-transparency: reduce)').matches
  )
}

function glassOn() {
  return theme.appearance === 'glass' && !reduceTransparency()
}

function attach(el) {
  const e = entries.get(el)
  if (!e || e.handle) return
  e.handle = liquidGlass(el, e.opts)
}
function detach(el) {
  const e = entries.get(el)
  if (e && e.handle) {
    e.handle.destroy()
    e.handle = null
  }
}

function ensureWatcher() {
  if (watching) return
  watching = true
  // one app-lifetime watcher drives every attached element on/off together
  watch(
    () => glassOn(),
    (on) => {
      for (const el of entries.keys()) (on ? attach : detach)(el)
    },
  )
}

export default {
  mounted(el, binding) {
    entries.set(el, { opts: binding.value || {}, handle: null })
    ensureWatcher()
    if (glassOn()) attach(el)
  },
  updated(el, binding) {
    const e = entries.get(el)
    if (e) e.opts = binding.value || e.opts
  },
  unmounted(el) {
    detach(el)
    entries.delete(el)
  },
}
