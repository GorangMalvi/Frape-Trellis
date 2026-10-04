// Configurable dashboard: widget model + a generic aggregation engine that
// runs client-side off the same get_cards payload the board uses. Pure except
// for userLabel (imported from the User cache, no circular dep).

import { BUCKET_PALETTE, bucketColorFor, colorFor } from '@/lib/board'
import { userLabel } from '@/lib/users'

const NUMERIC_TYPES = ['Int', 'Float', 'Currency', 'Percent', 'Duration']
const GROUP_TYPES = ['Select', 'Link', 'Check']

let _seq = 0
export function widgetKey() {
  return `w${Date.now().toString(36)}${(_seq++).toString(36)}`
}

// ---- which fields can be charted -------------------------------------------
// build the ctx once per dashboard render and thread it through everything
export function buildCtx(cfg) {
  const space = cfg?.space || {}
  const fields = cfg?.fields || []
  const buckets = cfg?.buckets || []
  const chipFields = space.chip_fields || []
  return {
    fields,
    buckets,
    bucketMap: Object.fromEntries(buckets.map((b) => [b.name, b])),
    bucketField: space.bucket_field || 'bucket',
    assigneeField: space.assignee_field,
    badgeField: space.badge_field || 'sprint_points',
    dueField: space.due_field,
    chipFields,
    closed: new Set(buckets.filter((b) => b.is_closed).map((b) => b.name)),
  }
}

function fieldDef(ctx, fn) {
  return ctx.fields.find((f) => f.fieldname === fn)
}
export function isChipField(ctx, fn) {
  return ctx.chipFields.includes(fn)
}
export function isUserField(ctx, fn) {
  const f = fieldDef(ctx, fn)
  return f?.fieldtype === 'Link' && f?.options === 'User'
}

// fields you can GROUP BY: bucket (synthetic) + Select/Link/Check + chip fields
export function groupableFields(ctx) {
  const out = [{ fieldname: ctx.bucketField, label: 'Bucket' }]
  for (const f of ctx.fields) {
    if (f.fieldname === ctx.bucketField) continue
    if (GROUP_TYPES.includes(f.fieldtype) || isChipField(ctx, f.fieldname)) {
      out.push({ fieldname: f.fieldname, label: f.label })
    }
  }
  return out
}

// fields you can SUM: numeric types, plus numeric-valued Selects (sprint_points)
export function numericFields(ctx) {
  return ctx.fields.filter((f) =>
    NUMERIC_TYPES.includes(f.fieldtype) ||
    (f.fieldtype === 'Select' && (f.options || '').split('\n').filter(Boolean).every((o) => o === '' || !Number.isNaN(Number(o)))),
  )
}

// ---- label + colour resolution for a group value ---------------------------
function groupLabel(ctx, fn, key) {
  if (key === '__none__') {
    if (fn === ctx.assigneeField || isUserField(ctx, fn)) return 'Unassigned'
    if (fn === ctx.bucketField) return 'Unsorted'
    return '—'
  }
  if (fn === ctx.bucketField) return ctx.bucketMap[key]?.bucket_name || key
  if (isUserField(ctx, fn)) return userLabel(key)
  const f = fieldDef(ctx, fn)
  if (f?.fieldtype === 'Check') return key === '1' || key === 1 ? 'Yes' : 'No'
  return String(key)
}

function groupColor(ctx, fn, key, index) {
  if (key === '__none__') return 'var(--sp-fill-strong)'
  if (fn === ctx.bucketField) return ctx.bucketMap[key]?.color || bucketColorFor(ctx.bucketMap[key]?.bucket_name)
  if (fn === ctx.badgeField) return colorFor(key)
  return BUCKET_PALETTE[index % BUCKET_PALETTE.length]
}

// a card's group key(s) for a field — chip fields yield MANY keys (one per tag)
function keysForCard(ctx, card, fn) {
  const raw = card[fn]
  if (isChipField(ctx, fn)) {
    const parts = String(raw || '').split(',').map((s) => s.trim()).filter(Boolean)
    return parts.length ? parts : ['__none__']
  }
  if (raw === null || raw === undefined || raw === '') return ['__none__']
  return [String(raw)]
}

// ---- scope + measure -------------------------------------------------------
function scopedCards(cards, ctx, scope) {
  if (scope === 'open') return cards.filter((c) => !ctx.closed.has(c[ctx.bucketField]))
  return cards
}
function measureValue(card, widget) {
  if (widget.measure === 'sum' && widget.measure_field) return Number(card[widget.measure_field]) || 0
  return 1
}

// ---- the engine: aggregate(cards, widget, ctx) -----------------------------
// stat  -> { value, tone }
// chart -> { rows: [{key, label, value, color, user?}] }
export function aggregate(cards, widget, ctx) {
  if (widget.type === 'stat') return { value: statValue(cards, widget, ctx) }

  const scope = widget.scope || 'all'
  const rows = scopedCards(cards, ctx, scope)
  const fn = widget.group_by || ctx.bucketField
  const sums = {}
  for (const c of rows) {
    const val = measureValue(c, widget)
    for (const k of keysForCard(ctx, c, fn)) sums[k] = (sums[k] || 0) + val
  }

  // order: buckets by their sort order; otherwise value desc
  let entries = Object.entries(sums)
  if (fn === ctx.bucketField) {
    const order = Object.fromEntries(ctx.buckets.map((b, i) => [b.name, i]))
    entries.sort((a, b) => (order[a[0]] ?? 999) - (order[b[0]] ?? 999))
  } else {
    entries.sort((a, b) => b[1] - a[1])
  }

  const out = entries.map(([key, value], i) => ({
    key,
    label: groupLabel(ctx, fn, key),
    value,
    color: groupColor(ctx, fn, key, i),
    user: isUserField(ctx, fn) && key !== '__none__' ? key : null,
  }))
  return { rows: out }
}

function statValue(cards, widget, ctx) {
  const open = () => cards.filter((c) => !ctx.closed.has(c[ctx.bucketField]))
  switch (widget.metric) {
    case 'total': return cards.length
    case 'open': return open().length
    case 'overdue': {
      if (!ctx.dueField) return 0
      const today = new Date(new Date().toDateString())
      return open().filter((c) => c[ctx.dueField] && new Date(c[ctx.dueField]) < today).length
    }
    case 'done_week': {
      const weekAgo = Date.now() - 7 * 86400e3
      return cards.filter((c) => ctx.closed.has(c[ctx.bucketField]) && new Date(c.modified) >= weekAgo).length
    }
    case 'sum': {
      const set = (widget.scope || 'open') === 'open' ? open() : cards
      return set.reduce((s, c) => s + (Number(c[widget.field]) || 0), 0)
    }
    default: return 0
  }
}

// ---- widget factories + auto defaults --------------------------------------
export function emptyWidget(type = 'chart', ctx = null) {
  const base = { id: widgetKey(), type, title: '' }
  if (type === 'stat') return { ...base, metric: 'open', field: '', scope: 'open' }
  return { ...base, chart: 'bar', group_by: ctx?.bucketField || 'bucket', measure: 'count', measure_field: '', scope: 'all' }
}

// sensible dashboard when a space has no saved config — old fixed dashboard
// plus one bar per extra groupable field, so it adapts to the space's shape.
export function defaultWidgets(ctx) {
  const w = []
  const badge = fieldDef(ctx, ctx.badgeField)
  const badgeNumeric = badge && numericFields(ctx).some((f) => f.fieldname === ctx.badgeField)
  const badgeLabel = badge?.label || 'points'

  w.push({ id: widgetKey(), type: 'stat', metric: 'open', title: 'Open', scope: 'open' })
  if (ctx.dueField) w.push({ id: widgetKey(), type: 'stat', metric: 'overdue', title: 'Overdue', tone: 'warning' })
  w.push({ id: widgetKey(), type: 'stat', metric: 'done_week', title: 'Done this week' })
  if (badgeNumeric) w.push({ id: widgetKey(), type: 'stat', metric: 'sum', field: ctx.badgeField, scope: 'open', title: `Open ${badgeLabel}` })

  w.push({ id: widgetKey(), type: 'chart', chart: 'bar', group_by: ctx.bucketField, measure: 'count', scope: 'all', title: 'Cards per bucket' })
  if (ctx.assigneeField) {
    w.push({ id: widgetKey(), type: 'chart', chart: 'bar', group_by: ctx.assigneeField, measure: 'count', scope: 'open', title: 'Cards per assignee' })
  }
  // one extra chart per remaining groupable field (Select/chip), capped
  const used = new Set([ctx.bucketField, ctx.assigneeField])
  let extra = 0
  for (const g of groupableFields(ctx)) {
    if (used.has(g.fieldname) || extra >= 2) continue
    const f = fieldDef(ctx, g.fieldname)
    if (f && (f.fieldtype === 'Select' || isChipField(ctx, g.fieldname))) {
      w.push({ id: widgetKey(), type: 'chart', chart: 'donut', group_by: g.fieldname, measure: 'count', scope: 'all', title: `By ${g.label}` })
      extra++
    }
  }
  return w
}

// human title fallback when the user leaves a widget's title blank
export function autoTitle(widget, ctx) {
  if (widget.title) return widget.title
  if (widget.type === 'stat') {
    const m = { total: 'Total cards', open: 'Open cards', overdue: 'Overdue', done_week: 'Done this week' }
    if (widget.metric === 'sum') return `Sum of ${fieldDef(ctx, widget.field)?.label || widget.field || 'field'}`
    return m[widget.metric] || 'Metric'
  }
  const g = groupableFields(ctx).find((x) => x.fieldname === widget.group_by)
  const measure = widget.measure === 'sum' ? (fieldDef(ctx, widget.measure_field)?.label || 'sum') : 'Cards'
  return `${measure} by ${g?.label || widget.group_by}`
}
