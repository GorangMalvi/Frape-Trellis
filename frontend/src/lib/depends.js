export function evaluateDependsOn(expression, doc = {}, parent = null) {
  if (expression == null || expression === '') return true
  if (typeof expression === 'boolean') return expression
  const text = String(expression).trim()
  if (!text) return true

  if (text.startsWith('eval:')) {
    try {
      return !!Function('doc', 'parent', `"use strict"; return (${text.slice(5)});`)(doc, parent || doc)
    } catch {
      return false
    }
  }

  if (text.startsWith('fn:')) return false

  const value = doc[text]
  return Array.isArray(value) ? value.length > 0 : !!value
}

export function fieldIsVisible(field, doc, parent) {
  return evaluateDependsOn(field?.depends_on, doc, parent)
}

export function fieldIsMandatory(field, doc, parent) {
  return !!field?.reqd || (!!field?.mandatory_depends_on && evaluateDependsOn(field.mandatory_depends_on, doc, parent))
}

export function fieldIsReadOnly(field, doc, parent) {
  return !!field?.read_only || (!!field?.read_only_depends_on && evaluateDependsOn(field.read_only_depends_on, doc, parent))
}
