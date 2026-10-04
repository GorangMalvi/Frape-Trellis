import { reactive } from 'vue'

// Module-level singleton (same pattern as store.js) — one pair of matchMedia
// listeners for the whole app. `isMobile` tracks Tailwind's `md:` boundary
// (767.98 so it can never disagree with `md:` at exactly 768px); `isTouch`
// tracks coarse/hover-less pointers. Use these ONLY where *behavior* differs
// (drag config, overlay activation, autofocus) — presentation belongs in
// `md:`/`max-md:` classes so nothing double-renders.
const mobileQ = window.matchMedia('(max-width: 767.98px)')
const touchQ = window.matchMedia('(hover: none), (pointer: coarse)')

export const breakpoint = reactive({
  isMobile: mobileQ.matches,
  isTouch: touchQ.matches,
})

mobileQ.addEventListener('change', (e) => (breakpoint.isMobile = e.matches))
touchQ.addEventListener('change', (e) => (breakpoint.isTouch = e.matches))
