<template>
  <!-- Lucide icons only resolve as template tags, so branch by key -->
  <LucidePlus v-if="kind === 'plus'" />
  <LucideColumns3 v-else-if="kind === 'columns'" />
  <LucidePencil v-else-if="kind === 'pen'" />
  <LucideUser v-else-if="kind === 'user'" />
  <LucideMessageSquare v-else-if="kind === 'message'" />
  <LucideCalendar v-else-if="kind === 'calendar'" />
  <LucideMoon v-else-if="kind === 'moon'" />
  <LucideRepeat v-else-if="kind === 'repeat'" />
  <LucideArrowRightLeft v-else-if="kind === 'move'" />
  <LucideFileText v-else-if="kind === 'template'" />
  <LucideBell v-else-if="kind === 'notify'" />
  <LucideWebhook v-else-if="kind === 'webhook'" />
  <LucideSparkles v-else-if="kind === 'sparkles'" />
  <LucideZap v-else />
</template>

<script setup>
defineProps({ kind: { type: String, default: 'zap' } })
</script>
