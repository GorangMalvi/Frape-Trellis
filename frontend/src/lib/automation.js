// Automation registries + the human-sentence generator. One source of truth so
// the rules list, builder preview, dry-run report and run log all speak the
// same language. Pure — no UI/store imports (userLabel is passed via ctx).

export const TRIGGERS = [
  { type: 'card_created', label: 'Card created', icon: 'plus', cardless: false },
  { type: 'moved_to_bucket', label: 'Moves to bucket', icon: 'columns', cardless: false },
  { type: 'field_changed', label: 'Field changes', icon: 'pen', cardless: false },
  { type: 'assignee_changed', label: 'Assignee changes', icon: 'user', cardless: false },
  { type: 'comment_added', label: 'Comment added', icon: 'message', cardless: false },
  { type: 'due_date_arrived', label: 'On the due date', icon: 'calendar', cardless: false },
  { type: 'due_date_approaching', label: 'Before due date', icon: 'calendar', cardless: false },
  { type: 'card_inactive', label: 'Card inactive', icon: 'moon', cardless: false },
  { type: 'scheduled', label: 'On a schedule', icon: 'repeat', cardless: true },
]

export const ACTIONS = [
  { type: 'set_field', label: 'Set a field', icon: 'pen', cardRequired: true },
  { type: 'move_to_bucket', label: 'Move to bucket', icon: 'move', cardRequired: true },
  { type: 'assign', label: 'Assign', icon: 'user', cardRequired: true },
  { type: 'apply_template', label: 'Apply template', icon: 'template', cardRequired: true },
  { type: 'create_card', label: 'Create a card', icon: 'plus', cardRequired: false },
  { type: 'notify', label: 'Notify', icon: 'notify', cardRequired: false },
  { type: 'add_comment', label: 'Post a comment', icon: 'message', cardRequired: false },
  { type: 'webhook', label: 'Call a webhook', icon: 'webhook', cardRequired: false },
]

export const PLACEHOLDERS = ['title', 'assignee', 'bucket', 'due_date', 'space', 'link']
export const WEEKDAYS = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
const CARDLESS_TRIGGERS = new Set(['scheduled'])

export function triggerMeta(type) {
  return TRIGGERS.find((t) => t.type === type) || TRIGGERS[0]
}
export function actionMeta(type) {
  return ACTIONS.find((a) => a.type === type) || ACTIONS[0]
}
export function isCardlessTrigger(type) {
  return CARDLESS_TRIGGERS.has(type)
}

// ---- shape factories -------------------------------------------------------
export function emptyTriggerConfig(type) {
  switch (type) {
    case 'moved_to_bucket': return { bucket: null }
    case 'field_changed': return { field: '', to_value: '' }
    case 'due_date_approaching': return { days_before: 2 }
    case 'card_inactive': return { days: 7 }
    case 'scheduled': return { frequency: 'weekly', weekday: 0, day_of_month: 1, time: '09:00' }
    default: return {}
  }
}
export function emptyAction(type = 'set_field') {
  const base = { type, _key: Math.random().toString(36).slice(2) }
  switch (type) {
    case 'set_field': return { ...base, field: '', value: '' }
    case 'move_to_bucket': return { ...base, bucket: '' }
    case 'assign': return { ...base, mode: 'one', user: '', users: [] }
    case 'apply_template': return { ...base, template: '' }
    case 'create_card': return { ...base, template: '', as_subtask: false }
    case 'notify': return { ...base, recipients: ['assignee'], users: [], message: '' }
    case 'add_comment': return { ...base, message: '' }
    case 'webhook': return { ...base, url: '', secret: '' }
    default: return base
  }
}

// defensively parse rule JSON if the API ever hands back strings, and give
// each action a stable _key for draggable lists
export function normalizeRule(raw) {
  const parse = (v, fb) => {
    if (v == null) return fb
    if (typeof v === 'string') { try { return JSON.parse(v) } catch { return fb } }
    return v
  }
  const actions = parse(raw.actions, []).map((a) => ({ _key: Math.random().toString(36).slice(2), ...a }))
  return {
    name: raw.name || null,
    automation_name: raw.automation_name || '',
    enabled: raw.enabled == null ? 1 : raw.enabled,
    description: raw.description || '',
    trigger_type: raw.trigger_type || 'card_created',
    trigger_config: parse(raw.trigger_config, {}),
    conditions: parse(raw.conditions, []),
    actions,
    has_secret: !!raw.has_secret,
  }
}

export function validateRule(rule) {
  const errs = []
  if (!rule.automation_name || !rule.automation_name.trim()) errs.push({ path: 'name', message: 'Name your automation.' })
  const tc = rule.trigger_config || {}
  if (rule.trigger_type === 'field_changed' && !tc.field) errs.push({ path: 'trigger', message: 'Pick the field to watch.' })
  if (rule.trigger_type === 'scheduled') {
    if (!tc.time) errs.push({ path: 'trigger', message: 'Pick a time of day.' })
  }
  if (!rule.actions || !rule.actions.length) errs.push({ path: 'actions', message: 'Add at least one action.' })
  ;(rule.actions || []).forEach((a, i) => {
    if (a.type === 'set_field' && !a.field) errs.push({ path: `actions.${i}`, message: 'Choose a field to set.' })
    if (a.type === 'move_to_bucket' && !a.bucket) errs.push({ path: `actions.${i}`, message: 'Choose a bucket.' })
    if (a.type === 'assign' && a.mode === 'one' && !a.user) errs.push({ path: `actions.${i}`, message: 'Choose a person.' })
    if (a.type === 'assign' && a.mode === 'round_robin' && !(a.users || []).length) errs.push({ path: `actions.${i}`, message: 'Add people to rotate.' })
    if ((a.type === 'apply_template' || a.type === 'create_card') && !a.template) errs.push({ path: `actions.${i}`, message: 'Choose a template.' })
    if (a.type === 'notify' && !(a.recipients || []).length && !(a.users || []).length) errs.push({ path: `actions.${i}`, message: 'Choose recipients.' })
    if (a.type === 'webhook' && !/^https?:\/\//.test(a.url || '')) errs.push({ path: `actions.${i}`, message: 'Enter an http(s) URL.' })
  })
  // scheduled rules can't touch a card unless they create one first
  if (rule.trigger_type === 'scheduled') {
    let created = false
    for (const a of rule.actions || []) {
      if (a.type === 'create_card') created = true
      if (['set_field', 'move_to_bucket', 'assign', 'apply_template'].includes(a.type) && !created) {
        errs.push({ path: 'actions', message: 'A scheduled rule must create a card before editing one.' })
        break
      }
    }
  }
  return errs
}

// prepare a rule for save_automation (strip client-only _key)
export function serializeActions(actions) {
  return (actions || []).map(({ _key, ...rest }) => rest)
}

// ---- sentence generator ----------------------------------------------------
// ctx = { fields, buckets, templates, userLabel }
function bucketName(ctx, id) {
  if (!id) return 'any bucket'
  return (ctx.buckets || []).find((b) => b.name === id)?.bucket_name || id
}
function fieldLabel(ctx, fn) {
  return (ctx.fields || []).find((f) => f.fieldname === fn)?.label || fn
}
function templateName(ctx, id) {
  return (ctx.templates || []).find((t) => t.name === id)?.template_name || id
}
function userName(ctx, u) {
  return ctx.userLabel ? ctx.userLabel(u) : u
}

export function triggerSentence(rule, ctx) {
  const tc = rule.trigger_config || {}
  switch (rule.trigger_type) {
    case 'card_created': return 'When a card is created'
    case 'moved_to_bucket': return `When a card moves to ${bucketName(ctx, tc.bucket)}`
    case 'field_changed':
      return tc.to_value
        ? `When ${fieldLabel(ctx, tc.field)} changes to ${tc.to_value}`
        : `When ${fieldLabel(ctx, tc.field)} changes`
    case 'assignee_changed': return 'When the assignee changes'
    case 'comment_added': return 'When a comment is added'
    case 'due_date_arrived': return 'On the due date'
    case 'due_date_approaching': return `${tc.days_before || 0} days before the due date`
    case 'card_inactive': return `When a card is inactive for ${tc.days || 0} days`
    case 'scheduled': {
      const t = tc.time || '09:00'
      if (tc.frequency === 'daily') return `Every day at ${t}`
      if (tc.frequency === 'weekly') return `Every ${WEEKDAYS[tc.weekday || 0]} at ${t}`
      if (tc.frequency === 'monthly') return `Monthly on day ${tc.day_of_month || 1} at ${t}`
      return 'On a schedule'
    }
    default: return 'When something happens'
  }
}

export function actionSentence(a, ctx) {
  switch (a.type) {
    case 'set_field': return `set ${fieldLabel(ctx, a.field)} to ${a.value ?? '—'}`
    case 'move_to_bucket': return `move to ${bucketName(ctx, a.bucket)}`
    case 'assign':
      return a.mode === 'round_robin'
        ? `rotate assignment among ${(a.users || []).length} people`
        : `assign ${userName(ctx, a.user)}`
    case 'apply_template': return `apply template ${templateName(ctx, a.template)}`
    case 'create_card': return `create a card from ${templateName(ctx, a.template)}${a.as_subtask ? ' (subtask)' : ''}`
    case 'notify': {
      const parts = [...(a.recipients || []), ...((a.users || []).map((u) => userName(ctx, u)))]
      return `notify ${parts.join(' + ') || 'nobody'}`
    }
    case 'add_comment': return 'post a comment'
    case 'webhook': { let host = a.url; try { host = new URL(a.url).hostname } catch { /* keep */ } return `call webhook ${host || ''}` }
    default: return a.type
  }
}

export function sentenceText(rule, ctx) {
  const when = triggerSentence(rule, ctx)
  const n = (rule.conditions || []).filter((c) => c.field && c.operator).length
  const cond = n ? ` · if ${n} condition${n === 1 ? '' : 's'} match` : ''
  const then = (rule.actions || []).map((a) => actionSentence(a, ctx)).join(' · ')
  return `${when}${cond} → ${then || '…'}`
}
