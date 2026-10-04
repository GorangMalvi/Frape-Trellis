import { computed, toValue } from 'vue'

// The SP Space registry pointers that tell the generic UI which field plays
// which role. One source of truth for the defaults — previously copy-pasted
// into Board, TaskDrawer and TicketIntake.
// `cfgSource` is a ref/computed/getter of the get_space payload.
export function useSpacePointers(cfgSource) {
  const space = () => toValue(cfgSource)?.space || {}
  const isTicket = computed(() => (space().space_type || 'Task') === 'Ticket')
  return {
    titleField: computed(() => space().title_field || 'title'),
    bucketField: computed(() => space().bucket_field || 'bucket'),
    assigneeField: computed(() => space().assignee_field),
    bodyField: computed(() => space().body_field),
    badgeField: computed(() => space().badge_field || 'sprint_points'),
    dueField: computed(() => space().due_field),
    chipFields: computed(() => space().chip_fields || []),
    chipOptions: computed(() => space().chip_options || {}),
    parentField: computed(() => space().parent_field || 'parent_task'),
    isTicket,
    noun: computed(() => (isTicket.value ? 'ticket' : 'task')),
    nounLabel: computed(() => (isTicket.value ? 'Ticket' : 'Task')),
  }
}
