<template>
  <transition name="sp-pop" appear>
    <div
      v-if="count"
      v-glass="{ scale: -110, chroma: 7, blur: 3, saturate: 1.8, radius: 16 }"
      class="sp-pop sp-glass fixed bottom-6 left-1/2 z-30 flex -translate-x-1/2 items-center gap-2 px-3 py-2"
    >
      <span class="flex items-center gap-2 pr-1 text-sm">
        <span class="flex h-6 min-w-6 items-center justify-center rounded-md bg-[color:var(--sp-accent)] px-1.5 text-xs font-semibold text-white sp-tnum">
          {{ count }}
        </span>
        selected
      </span>

      <span class="mx-1 h-5 w-px bg-[var(--sp-line)]" />

      <label class="sp-control flex items-center gap-1.5 px-2 py-1.5 text-sm">
        Bucket
        <select class="bg-transparent focus:outline-none" @change="onBucket($event)">
          <option value="">—</option>
          <option v-for="b in buckets" :key="b.name" :value="b.name">{{ b.bucket_name }}</option>
        </select>
      </label>

      <label v-if="badgeOptions.length" class="sp-control flex items-center gap-1.5 px-2 py-1.5 text-sm">
        {{ badgeLabel }}
        <select class="bg-transparent focus:outline-none" @change="onBadge($event)">
          <option value="">—</option>
          <option v-for="p in badgeOptions" :key="p" :value="p">{{ p }}</option>
        </select>
      </label>

      <label v-if="assigneeField" class="sp-control flex items-center gap-1.5 px-2 py-1.5 text-sm">
        Assignee
        <select class="bg-transparent focus:outline-none" @change="onAssignee($event)">
          <option value="">—</option>
          <option v-for="u in userOpts" :key="u.value" :value="u.value">{{ u.label }}</option>
        </select>
      </label>

      <button class="sp-control px-2 py-1.5 text-sm text-ink-red-3" @click="$emit('delete')">
        Delete
      </button>

      <span class="mx-1 h-5 w-px bg-[var(--sp-line)]" />
      <button class="sp-control flex items-center px-1.5 py-1.5" @click="$emit('clear')">
        <LucideX class="h-4 w-4" />
      </button>
    </div>
  </transition>
</template>

<script setup>
import { computed, onMounted } from 'vue'
import { ensureUsers, userOptions } from '@/lib/users'

const props = defineProps({
  count: Number,
  buckets: { type: Array, default: () => [] },
  fields: { type: Array, default: () => [] },
  assigneeField: String,
  badgeField: String,
})
const emit = defineEmits(['set', 'delete', 'clear'])

onMounted(ensureUsers)

const badgeFieldDef = computed(() => props.fields.find((x) => x.fieldname === props.badgeField))
const badgeLabel = computed(() => badgeFieldDef.value?.label || 'Points')
const badgeOptions = computed(() =>
  badgeFieldDef.value ? (badgeFieldDef.value.options || '').split('\n').filter(Boolean) : [],
)
const userOpts = computed(() => userOptions())

function reset(e) {
  e.target.value = ''
}
function onBucket(e) {
  const v = e.target.value
  if (v) emit('set', { bucket: v })
  reset(e)
}
function onBadge(e) {
  const v = e.target.value
  if (v && props.badgeField) emit('set', { [props.badgeField]: v })
  reset(e)
}
function onAssignee(e) {
  const v = e.target.value
  if (v) emit('set', { [props.assigneeField]: v })
  reset(e)
}
</script>
