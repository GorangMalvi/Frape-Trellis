<template>
  <span
    class="inline-flex shrink-0 select-none items-center justify-center overflow-hidden rounded-full font-semibold leading-none"
    :style="style"
    :title="label"
  >
    <img v-if="img" :src="img" :alt="label" class="h-full w-full object-cover" />
    <template v-else>{{ initials }}</template>
  </span>
</template>

<script setup>
// A user's circular avatar. Shows their photo if set, otherwise initials on a
// colour deterministically derived from their id — except the viewing user,
// who always appears orange (so you can spot yourself at a glance).
import { computed } from 'vue'
import { userLabel, userImage, currentUser } from '@/lib/users'
import { contrastText } from '@/lib/format'

const props = defineProps({
  user: { type: String, default: '' },
  size: { type: String, default: 'sm' },
})

const SIZES = { xs: 16, sm: 20, md: 26, lg: 36, xl: 48 }
const FONTS = { xs: 8, sm: 9, md: 11, lg: 14, xl: 18 }

// orange reserved for "me"; the rest spread across the hue wheel (no orange)
const PALETTE = [
  '#ef4444', '#ec4899', '#f43f5e', '#d946ef', '#a855f7', '#8b5cf6',
  '#6366f1', '#3b82f6', '#0ea5e9', '#06b6d4', '#14b8a6', '#10b981',
  '#22c55e', '#84cc16', '#eab308',
]
const SELF = '#ff9500'

function hash(s) {
  let h = 0
  for (let i = 0; i < s.length; i++) h = (h * 31 + s.charCodeAt(i)) | 0
  return Math.abs(h)
}
const label = computed(() => userLabel(props.user))
const img = computed(() => userImage(props.user))

const bg = computed(() => {
  const u = props.user || ''
  if (!u) return '#9ca3af'
  if (u === currentUser()) return SELF
  return PALETTE[hash(u) % PALETTE.length]
})
const fg = computed(() => contrastText(bg.value))

const initials = computed(() => {
  const parts = String(label.value || '').trim().split(/\s+/).filter(Boolean)
  if (!parts.length) return '?'
  if (parts.length === 1) return parts[0].slice(0, 1).toUpperCase()
  return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase()
})

const style = computed(() => {
  const px = SIZES[props.size] || SIZES.sm
  return {
    width: px + 'px',
    height: px + 'px',
    fontSize: (FONTS[props.size] || FONTS.sm) + 'px',
    background: img.value ? 'transparent' : bg.value,
    color: fg.value,
  }
})
</script>
