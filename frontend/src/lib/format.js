// Shared display formatters. Keep these pure — no store or component imports.

export function formatDate(d) {
  if (!d) return ''
  return new Date(d).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
}

// datetime → "Mon D, h:mm AM" (activity timestamps)
export function when(t) {
  const d = new Date((t || '').replace(' ', 'T'))
  return d.toLocaleString('en-US', { month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit' })
}

export function formatDuration(sec) {
  sec = Number(sec) || 0
  const h = Math.floor(sec / 3600)
  const m = Math.floor((sec % 3600) / 60)
  return [h ? `${h}h` : null, m ? `${m}m` : null].filter(Boolean).join(' ') || '0m'
}

// relative time: "just now" / "4m ago" / "2h ago" / "3d ago" / "Mar 4"
export function timeAgo(t) {
  if (!t) return ''
  const d = new Date(String(t).replace(' ', 'T'))
  const secs = Math.floor((Date.now() - d.getTime()) / 1000)
  if (secs < 45) return 'just now'
  if (secs < 3600) return `${Math.floor(secs / 60)}m ago`
  if (secs < 86400) return `${Math.floor(secs / 3600)}h ago`
  if (secs < 7 * 86400) return `${Math.floor(secs / 86400)}d ago`
  return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
}

export function formatNumber(n) {
  return Number.isInteger(n) ? n.toLocaleString() : n.toLocaleString(undefined, { maximumFractionDigits: 2 })
}

export function stripHtml(html) {
  if (!html) return ''
  const tmp = document.createElement('div')
  tmp.innerHTML = html
  return (tmp.textContent || tmp.innerText || '').trim()
}

// comma-string (chip field storage) → trimmed values
export function splitChips(v) {
  return String(v || '').split(',').map((c) => c.trim()).filter(Boolean)
}

// readable text color for an arbitrary hex background
export function contrastText(hex) {
  const h = (hex || '').replace('#', '')
  if (h.length < 6) return '#fff'
  const r = parseInt(h.slice(0, 2), 16)
  const g = parseInt(h.slice(2, 4), 16)
  const b = parseInt(h.slice(4, 6), 16)
  return 0.299 * r + 0.587 * g + 0.114 * b > 168 ? 'rgba(0,0,0,0.8)' : '#fff'
}
