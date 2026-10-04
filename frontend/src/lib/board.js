// Pure client-side engine for filtering / grouping / sorting cards.

// Colour for a badge/group value. Numeric scales (e.g. Sprint Points 1-10)
// shade low→high; legacy priority words fall back to their palette.
export function colorFor(value) {
  const n = Number(value)
  if (value != null && value !== '' && !Number.isNaN(n)) {
    if (n >= 9) return '#ef4444'
    if (n >= 7) return '#f59e0b'
    if (n >= 4) return '#6366f1'
    return '#9ca3af'
  }
  return { Urgent: '#ef4444', High: '#f59e0b', Normal: '#3b82f6', Low: '#9ca3af' }[value] || '#9ca3af'
}

// Suggest a bucket colour from its name (so columns are colour-coded by
// meaning), falling back to a rotating palette for unrecognised names.
const BUCKET_KEYWORDS = [
  [/backlog/, '#ef4444'],
  [/icebox|someday|parking/, '#94a3b8'],
  [/blocked|on.?hold|stuck|waiting|paused/, '#f43f5e'],
  [/review|qa|testing|verify/, '#a855f7'],
  [/progress|doing|wip|active|ongoing|started|build|dev\b/, '#f59e0b'],
  [/to.?do|todo|open|new|not.?started|up.?next|ready|queue/, '#3b82f6'],
  [/done|complete|closed|resolved|shipped|live|deployed|finished/, '#22c55e'],
  [/cancel|archiv|wont|won.?t|dropped|rejected/, '#9ca3af'],
  [/plan|scheduled|triage|design|discovery/, '#8b5cf6'],
]
// a full, hue-ordered swatch set for bucket colours (reds → … → neutrals)
export const BUCKET_PALETTE = [
  '#ef4444', '#f43f5e', '#ec4899', '#d946ef', '#a855f7', '#8b5cf6',
  '#6366f1', '#3b82f6', '#0ea5e9', '#06b6d4', '#14b8a6', '#10b981',
  '#22c55e', '#84cc16', '#eab308', '#f59e0b', '#f97316', '#fb7185',
  '#78716c', '#64748b', '#94a3b8', '#9ca3af',
]
export function bucketColorFor(name, index = 0) {
  const n = String(name || '').toLowerCase()
  for (const [re, c] of BUCKET_KEYWORDS) if (re.test(n)) return c
  return BUCKET_PALETTE[index % BUCKET_PALETTE.length]
}

// fractional rank between two neighbours so a drop only writes one row
export function midpoint(prev, next) {
  if (prev == null && next == null) return 1
  if (prev == null) return next - 1
  if (next == null) return prev + 1
  return (prev + next) / 2
}

export function matchFilter(card, f) {
  const v = card[f.field]
  switch (f.operator) {
    case 'is':
      return String(v ?? '') === String(f.value ?? '')
    case 'is not':
      return String(v ?? '') !== String(f.value ?? '')
    case 'is any of': {
      // OR within one field: match if the card's value is any of the picked ones
      const arr = (Array.isArray(f.value) ? f.value : []).map(String)
      if (!arr.length) return true // nothing picked yet → no constraint
      return arr.includes(String(v ?? ''))
    }
    case 'is none of': {
      const arr = (Array.isArray(f.value) ? f.value : []).map(String)
      if (!arr.length) return true
      return !arr.includes(String(v ?? ''))
    }
    case 'contains':
      return String(v ?? '').toLowerCase().includes(String(f.value ?? '').toLowerCase())
    case 'is empty':
      return v == null || v === ''
    case 'is set':
      return v != null && v !== ''
    default:
      return true
  }
}

export function applyFilters(cards, { filters, meMode, assigneeField, currentUser, search, titleField }) {
  let out = cards
  if (meMode && assigneeField) {
    out = out.filter((c) => c[assigneeField] === currentUser)
  }
  for (const f of filters || []) {
    if (!f.field || !f.operator) continue
    out = out.filter((c) => matchFilter(c, f))
  }
  if (search) {
    const q = search.toLowerCase()
    out = out.filter((c) => String(c[titleField] ?? '').toLowerCase().includes(q))
  }
  return out
}

export function sortCards(cards, field, dir = 'asc') {
  if (!field) return cards
  const sorted = [...cards].sort((a, b) => {
    const x = a[field]
    const y = b[field]
    if (x === y) return 0
    if (x == null || x === '') return 1
    if (y == null || y === '') return -1
    return x > y ? 1 : -1
  })
  return dir === 'desc' ? sorted.reverse() : sorted
}

export function buildGroups(cards, { groupByField, bucketField, buckets, fields }) {
  const groups = []
  const byKey = {}
  const ensure = (key, label, color, wip) => {
    if (!byKey[key]) {
      byKey[key] = { key, label, color, wip, cards: [] }
      groups.push(byKey[key])
    }
    return byKey[key]
  }

  // seed known groups (bucket order, or Select options) so empty ones still show
  if (groupByField === bucketField) {
    for (const b of buckets || []) ensure(b.name, b.bucket_name, b.color, b.wip_limit)
  } else {
    const field = (fields || []).find((f) => f.fieldname === groupByField)
    if (field?.fieldtype === 'Select') {
      for (const o of (field.options || '').split('\n').filter(Boolean)) {
        ensure(o, o, colorFor(o))
      }
    }
  }

  const none = { key: '__none__', label: '(empty)', color: '#cbd5e1', cards: [] }
  for (const c of cards) {
    const k = c[groupByField]
    if (k == null || k === '') none.cards.push(c)
    else ensure(k, String(k), colorFor(k)).cards.push(c)
  }
  if (none.cards.length) groups.push(none)
  return groups
}
