<template>
  <LucideCircleDot v-if="kind === 'status'" class="h-4 w-4" />
  <LucideUser v-else-if="kind === 'user'" class="h-4 w-4" />
  <LucideCalendar v-else-if="kind === 'date'" class="h-4 w-4" />
  <LucideZap v-else-if="kind === 'points'" class="h-4 w-4" />
  <LucideClock v-else-if="kind === 'duration'" class="h-4 w-4" />
  <LucideTag v-else-if="kind === 'tags'" class="h-4 w-4" />
  <LucideHash v-else-if="kind === 'number'" class="h-4 w-4" />
  <LucideSquareCheck v-else-if="kind === 'check'" class="h-4 w-4" />
  <LucideLink v-else-if="kind === 'link'" class="h-4 w-4" />
  <LucideAlignLeft v-else class="h-4 w-4" />
</template>

<script setup>
// Lucide icons only resolve as template tags (frappe-ui auto-import), so we
// branch by a "kind" string instead of binding a dynamic component.
defineProps({ kind: { type: String, default: 'field' } })
</script>
