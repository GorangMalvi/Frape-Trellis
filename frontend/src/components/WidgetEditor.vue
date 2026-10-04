<template>
  <Teleport to="body">
    <transition name="sp-fade" appear>
      <div class="fixed inset-0 z-[70] flex items-center justify-center sp-scrim p-4 backdrop-blur-md" @click.self="$emit('close')">
        <transition name="sp-pop" appear>
          <div ref="panelEl" v-glass="{ scale: -90, chroma: 6, blur: 4, saturate: 1.7, radius: 22 }"role="dialog" aria-modal="true" aria-label="Widget" class="sp-modal max-h-[85vh] w-full max-w-[440px] overflow-y-auto p-5">
            <div class="mb-4 flex items-center justify-between">
              <h2 class="sp-display text-base font-semibold sp-ink-1">{{ isNew ? 'Add widget' : 'Edit widget' }}</h2>
              <button class="sp-control p-1.5" aria-label="Close" @click="$emit('close')"><LucideX class="h-4 w-4" /></button>
            </div>

            <div class="space-y-3.5">
              <!-- type -->
              <div class="sp-chip flex gap-0.5 p-0.5">
                <button class="flex-1 rounded-[7px] py-1 text-sm font-medium transition" :class="w.type === 'stat' ? 'sp-seg-active text-ink-gray-9' : 'sp-ink-3'" @click="setType('stat')">Number</button>
                <button class="flex-1 rounded-[7px] py-1 text-sm font-medium transition" :class="w.type === 'chart' ? 'sp-seg-active text-ink-gray-9' : 'sp-ink-3'" @click="setType('chart')">Chart</button>
              </div>

              <label class="block">
                <span class="mb-1 block text-xs font-medium sp-ink-2">Title <span class="sp-ink-4">(optional)</span></span>
                <input v-model="w.title" :placeholder="autoTitle(w, ctx)" class="sp-field w-full" />
              </label>

              <!-- STAT config -->
              <template v-if="w.type === 'stat'">
                <label class="block">
                  <span class="mb-1 block text-xs font-medium sp-ink-2">Metric</span>
                  <select v-model="w.metric" class="sp-field w-full">
                    <option value="total">Total cards</option>
                    <option value="open">Open cards</option>
                    <option v-if="ctx.dueField" value="overdue">Overdue</option>
                    <option value="done_week">Done this week</option>
                    <option value="sum">Sum of a field…</option>
                  </select>
                </label>
                <label v-if="w.metric === 'sum'" class="block">
                  <span class="mb-1 block text-xs font-medium sp-ink-2">Field to sum</span>
                  <select v-model="w.field" class="sp-field w-full">
                    <option value="">Choose…</option>
                    <option v-for="f in numeric" :key="f.fieldname" :value="f.fieldname">{{ f.label }}</option>
                  </select>
                </label>
                <label v-if="w.metric === 'sum'" class="flex items-center gap-2 text-sm sp-ink-2">
                  <input type="checkbox" :checked="w.scope === 'open'" class="rounded" @change="w.scope = $event.target.checked ? 'open' : 'all'" />
                  open cards only
                </label>
              </template>

              <!-- CHART config -->
              <template v-else>
                <div class="sp-chip flex gap-0.5 p-0.5">
                  <button class="flex-1 rounded-[7px] py-1 text-sm font-medium transition" :class="w.chart === 'bar' ? 'sp-seg-active text-ink-gray-9' : 'sp-ink-3'" @click="w.chart = 'bar'">Bar</button>
                  <button class="flex-1 rounded-[7px] py-1 text-sm font-medium transition" :class="w.chart === 'donut' ? 'sp-seg-active text-ink-gray-9' : 'sp-ink-3'" @click="w.chart = 'donut'">Donut</button>
                </div>
                <label class="block">
                  <span class="mb-1 block text-xs font-medium sp-ink-2">Group by</span>
                  <select v-model="w.group_by" class="sp-field w-full">
                    <option v-for="g in groupable" :key="g.fieldname" :value="g.fieldname">{{ g.label }}</option>
                  </select>
                </label>
                <label class="block">
                  <span class="mb-1 block text-xs font-medium sp-ink-2">Measure</span>
                  <select v-model="w.measure" class="sp-field w-full">
                    <option value="count">Count of cards</option>
                    <option value="sum">Sum of a field…</option>
                  </select>
                </label>
                <label v-if="w.measure === 'sum'" class="block">
                  <span class="mb-1 block text-xs font-medium sp-ink-2">Field to sum</span>
                  <select v-model="w.measure_field" class="sp-field w-full">
                    <option value="">Choose…</option>
                    <option v-for="f in numeric" :key="f.fieldname" :value="f.fieldname">{{ f.label }}</option>
                  </select>
                </label>
                <label class="flex items-center gap-2 text-sm sp-ink-2">
                  <input type="checkbox" :checked="w.scope === 'open'" class="rounded" @change="w.scope = $event.target.checked ? 'open' : 'all'" />
                  open cards only
                </label>
              </template>
            </div>

            <div class="mt-6 flex justify-end gap-2">
              <Button variant="subtle" @click="$emit('close')">Cancel</Button>
              <AccentButton :disabled="!valid" @click="$emit('save', { ...w })">{{ isNew ? 'Add' : 'Save' }}</AccentButton>
            </div>
          </div>
        </transition>
      </div>
    </transition>
  </Teleport>
</template>

<script setup>
import { computed, reactive, ref } from 'vue'
import { Button } from 'frappe-ui'
import AccentButton from '@/components/AccentButton.vue'
import { useOverlay } from '@/composables/useOverlay'
import { groupableFields, numericFields, emptyWidget, autoTitle } from '@/lib/dashboard'

const props = defineProps({
  widget: { type: Object, default: null },
  ctx: { type: Object, required: true },
})
const emit = defineEmits(['close', 'save'])

const panelEl = ref(null)
useOverlay({ close: () => emit('close'), panel: panelEl })

const isNew = !props.widget
const w = reactive(props.widget ? { ...props.widget } : emptyWidget('chart', props.ctx))

const groupable = computed(() => groupableFields(props.ctx))
const numeric = computed(() => numericFields(props.ctx))

const valid = computed(() => {
  if (w.type === 'stat') return w.metric !== 'sum' || !!w.field
  if (!w.group_by) return false
  return w.measure !== 'sum' || !!w.measure_field
})

function setType(t) {
  const fresh = emptyWidget(t, props.ctx)
  fresh.id = w.id
  fresh.title = w.title
  Object.keys(w).forEach((k) => delete w[k])
  Object.assign(w, fresh)
}
</script>
