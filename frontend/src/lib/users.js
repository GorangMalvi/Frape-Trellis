import { reactive } from 'vue'
import { call } from 'frappe-ui'

// Process-wide cache of enabled users so avatars + names render everywhere
// without each component refetching.
export const users = reactive({ map: {}, loaded: false })
let inflight = null

// Who is viewing — drives the "me is always orange" avatar rule and structural
// gating. Seeded from the Frappe boot vars; Board refreshes from get_space.
export const session = reactive({
  user: (typeof window !== 'undefined' && window.user) || '',
  canManage: !!(typeof window !== 'undefined' && window.can_manage),
})
export function setCurrentUser(u) {
  if (u) session.user = u
}
export function setCanManage(v) {
  session.canManage = !!v
}
export function currentUser() {
  return session.user || (typeof window !== 'undefined' && window.user) || ''
}
// true for Administrator-only structural rights
export function canManage() {
  return !!session.canManage
}

export function ensureUsers() {
  if (users.loaded) return Promise.resolve()
  if (inflight) return inflight
  inflight = call('frappe.client.get_list', {
    doctype: 'User',
    fields: ['name', 'full_name', 'user_image'],
    filters: { enabled: 1 },
    limit_page_length: 0,
    order_by: 'full_name asc',
  })
    .then((rows) => {
      for (const r of rows) users.map[r.name] = r
      users.loaded = true
    })
    .finally(() => (inflight = null))
  return inflight
}

export function userLabel(id) {
  return users.map[id]?.full_name || id || ''
}
export function userImage(id) {
  return users.map[id]?.user_image || ''
}
export function userOptions() {
  return Object.values(users.map).map((u) => ({
    label: u.full_name || u.name,
    value: u.name,
    image: u.user_image,
  }))
}
