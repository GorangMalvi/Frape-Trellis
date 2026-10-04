import { reactive, ref } from 'vue'
import { stripHtml } from '@/lib/format'

// ---- toasts ------------------------------------------------------------
export const toasts = ref([])
let toastId = 0
export function pushToast(message, type = 'error', timeout = 5000) {
  const id = ++toastId
  toasts.value.push({ id, message, type })
  if (timeout) setTimeout(() => dismissToast(id), timeout)
  return id
}
export function dismissToast(id) {
  const i = toasts.value.findIndex((t) => t.id === id)
  if (i >= 0) toasts.value.splice(i, 1)
}

// Pull a human message out of a Frappe/frappe-ui error.
export function errorMessage(e, fallback) {
  if (!e) return fallback || 'Something went wrong'
  if (Array.isArray(e.messages) && e.messages.length) return stripHtml(e.messages[0])
  const sm = e._server_messages || e.exc
  if (sm) {
    try {
      const arr = JSON.parse(sm)
      const first = typeof arr[0] === 'string' ? JSON.parse(arr[0]) : arr[0]
      if (first?.message) return stripHtml(first.message)
    } catch {
      /* fall through */
    }
  }
  return stripHtml(e.message) || fallback || 'Could not save — please try again'
}

// Lightweight global UI state to bridge the command palette and the board
// without a full store library.
export const ui = reactive({
  paletteOpen: false,
  // mobile off-canvas sidebar drawer (App.vue renders the scrim + transform)
  sidebarOpen: false,
  // hooks the active Board registers so the palette can drive it
  _openCard: null,
  _newTask: null,
  _refresh: null,
})

export function openPalette() {
  ui.paletteOpen = true
}
export function openSidebar() {
  ui.sidebarOpen = true
}
export function closeSidebar() {
  ui.sidebarOpen = false
}
export function toggleSidebar() {
  ui.sidebarOpen = !ui.sidebarOpen
}
export function closePalette() {
  ui.paletteOpen = false
}
export function openCard(name) {
  ui.paletteOpen = false
  ui._openCard && ui._openCard(name)
}
export function triggerNewTask() {
  ui.paletteOpen = false
  ui._newTask && ui._newTask()
}
export function triggerRefresh() {
  ui._refresh && ui._refresh()
}

// ---- theme: appearance (light / dark / auto) --------------------------
// Appearance follows the OS by default (prefers-color-scheme); the user can
// pin Light/Dark. Persists to localStorage, applied as data-theme on <html>.
const THEME_KEY = 'sprint.theme'
export const theme = reactive({ appearance: 'light' })

const darkQuery =
  typeof window !== 'undefined' && window.matchMedia
    ? window.matchMedia('(prefers-color-scheme: dark)')
    : { matches: false, addEventListener() {} }

export function resolvedDark() {
  if (theme.appearance === 'glass') return true // Glass is a dark-based skin
  if (theme.appearance === 'dark') return true
  if (theme.appearance === 'light') return false
  return darkQuery.matches
}

export function applyTheme() {
  const el = document.documentElement
  el.dataset.theme = resolvedDark() ? 'dark' : 'light'
  // Glass is an additive translucent skin over the dark base, toggled by its
  // own attribute so the light/dark token machinery stays untouched.
  if (theme.appearance === 'glass') el.setAttribute('data-glass', 'on')
  else el.removeAttribute('data-glass')
}

function persistTheme() {
  try {
    localStorage.setItem(THEME_KEY, JSON.stringify({ appearance: theme.appearance }))
  } catch { /* private mode / disabled storage */ }
}

export function setAppearance(mode) {
  theme.appearance = mode
  persistTheme()
  applyTheme()
}

export function initTheme() {
  try {
    const saved = JSON.parse(localStorage.getItem(THEME_KEY) || '{}')
    if (['light', 'dark', 'glass'].includes(saved.appearance)) theme.appearance = saved.appearance
  } catch { /* ignore */ }
  applyTheme()
  // keep Auto in sync with the OS while the app is open
  darkQuery.addEventListener('change', () => {
    if (theme.appearance === 'auto') applyTheme()
  })
}

// ---- global confirm dialog (are-you-sure, + password re-auth) ----------
// confirmDelete() returns a promise that resolves true only once the user
// confirms (and, when requirePassword, their password is verified in-dialog).
export const confirm = reactive({
  open: false,
  title: 'Are you sure?',
  message: '',
  confirmLabel: 'Delete',
  requirePassword: false,
})
let confirmResolve = null
export function confirmDelete(opts = {}) {
  confirm.title = opts.title || 'Are you sure?'
  confirm.message = opts.message || ''
  confirm.confirmLabel = opts.confirmLabel || 'Delete'
  confirm.requirePassword = !!opts.requirePassword
  confirm.open = true
  return new Promise((resolve) => {
    confirmResolve = resolve
  })
}
export function resolveConfirm(ok) {
  confirm.open = false
  confirmResolve?.(ok)
  confirmResolve = null
}

// ---- realtime ----------------------------------------------------------
let socket = null
export function setSocket(s) {
  socket = s
  // notifications (mention / assignment / ticket alert): backend targets this
  // user's room; the payload's subject is the toast text
  s?.on?.('sprint_notification', (d) => {
    const fallback = `💬 ${d?.from_name || 'Someone'} mentioned you${d?.title ? ` in “${d.title}”` : ''}`
    pushToast(d?.subject || fallback, 'success', 8000)
    inbox.unread += 1
  })
}

// ---- inbox (Home page unread badge) -------------------------------------
export const inbox = reactive({ unread: 0 })
export function setUnread(n) {
  inbox.unread = Math.max(0, Number(n) || 0)
}

// Subscribe to Frappe's `list_update` for a doctype. Ignores self-authored
// events (so optimistic UI isn't disturbed) and debounces the callback.
// Returns an unsubscribe function.
export function subscribeDoctype(doctype, cb, delay = 300) {
  if (!socket || !doctype) return () => {}
  const me = window.user
  let timer = null
  const handler = (data) => {
    if (data?.doctype !== doctype) return
    if (me && data.user === me) return
    clearTimeout(timer)
    timer = setTimeout(cb, delay)
  }
  socket.emit('doctype_subscribe', doctype)
  socket.on('list_update', handler)
  return () => {
    clearTimeout(timer)
    socket.off('list_update', handler)
    socket.emit('doctype_unsubscribe', doctype)
  }
}
