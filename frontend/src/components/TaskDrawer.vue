<template>
  <Teleport to="body">
    <transition name="sp-fade" appear>
      <div class="fixed inset-0 z-40 flex items-center justify-center sp-scrim p-0 md:p-8 md:backdrop-blur-md" @click.self="$emit('close')">
        <transition name="sp-pop" appear>
          <div
            ref="panelEl"
            v-glass="{ scale: -80, chroma: 6, blur: 4, saturate: 1.7, radius: 22 }"
            role="dialog"
            aria-modal="true"
            :aria-label="creating ? `New ${noun}` : form[titleField] || nounLabel"
            class="sp-modal sp-modal-sheet flex h-[88vh] w-full max-w-[1080px] overflow-hidden max-md:flex-col"
          >
            <!-- mobile: Details | Activity tabs + close -->
            <div class="flex shrink-0 items-center gap-2 border-b sp-hair px-3 py-2 md:hidden">
              <div class="sp-chip flex flex-1 gap-0.5 p-0.5">
                <button
                  class="flex-1 rounded-[7px] py-1.5 text-sm font-medium transition"
                  :class="mobileTab === 'details' ? 'sp-seg-active text-ink-gray-9' : 'sp-ink-3'"
                  @click="mobileTab = 'details'"
                >
                  Details
                </button>
                <button
                  class="flex-1 rounded-[7px] py-1.5 text-sm font-medium transition"
                  :class="mobileTab === 'activity' ? 'sp-seg-active text-ink-gray-9' : 'sp-ink-3'"
                  @click="mobileTab = 'activity'"
                >
                  Activity<template v-if="activity.length"> · {{ activity.length }}</template>
                </button>
              </div>
              <button aria-label="Close" class="rounded-md p-2 text-ink-gray-5 hover:bg-[var(--sp-fill)] hover:text-ink-gray-8" @click="$emit('close')">
                <LucideX class="h-5 w-5" />
              </button>
            </div>

            <div class="flex min-h-0 min-w-0 flex-1">
            <!-- ================= MAIN ================= -->
            <div v-show="!breakpoint.isMobile || mobileTab === 'details'" class="flex min-w-0 flex-1 flex-col">
              <div class="flex items-center gap-1.5 border-b sp-hair px-4 py-3 text-xs text-ink-gray-5 md:px-8">
                <span>{{ config?.space?.icon }}</span>
                <span>{{ config?.space?.label }}</span>
                <template v-if="!creating && form[parentField]">
                  <span class="text-ink-gray-3">/</span>
                  <button class="max-w-[120px] truncate text-ink-gray-6 hover:text-ink-gray-9 hover:underline md:max-w-[220px]" @click="$emit('open-task', form[parentField])">
                    {{ parentTitle || form[parentField] }}
                  </button>
                </template>
                <span class="text-ink-gray-3">/</span>
                <span class="font-mono">{{ creating ? `New ${noun}` : shortId }}</span>
                <button
                  v-if="!creating && !isTicket && canManageSession"
                  class="ml-auto flex items-center gap-1 rounded-md px-1.5 py-1 text-xs text-ink-gray-5 transition hover:bg-[var(--sp-fill)] hover:text-ink-gray-8"
                  title="Save this card's field values as a reusable template"
                  @click="savingTemplate = true"
                >
                  <LucideCopyPlus class="h-3.5 w-3.5" /> Save as template
                </button>
              </div>

              <div v-if="loading" class="space-y-4 px-4 py-6 md:px-8">
                <div class="sp-skeleton h-10 w-2/3 rounded" />
                <div class="sp-skeleton h-9 w-full rounded" />
                <div class="sp-skeleton h-40 w-full rounded" />
              </div>

              <div v-else class="sp-scroll flex-1 overflow-y-auto px-4 py-5 md:px-8 md:py-6">
                <!-- start from a template (create mode) -->
                <div v-if="creating && templates.length" class="mb-4 flex flex-wrap items-center gap-1.5">
                  <span class="text-xs sp-ink-3">Start from:</span>
                  <button
                    v-for="t in templates"
                    :key="t.name"
                    class="rounded-md px-2 py-1 text-xs font-medium transition"
                    :class="appliedTemplate === t.name
                      ? 'bg-[var(--sp-accent-tint)] text-[color:var(--sp-accent)]'
                      : 'bg-[var(--sp-fill)] text-ink-gray-6 hover:bg-[var(--sp-fill-hover)]'"
                    @click="applyTemplate(t)"
                  >
                    {{ t.template_name }}
                  </button>
                </div>

                <input
                  ref="titleEl"
                  v-model="form[titleField]"
                  class="sp-display w-full border-0 bg-transparent text-[26px] font-semibold text-ink-gray-9 focus:outline-none focus:ring-0"
                  :placeholder="`${nounLabel} title…`"
                  @blur="save"
                  @keyup.enter="creating && create()"
                />

                <!-- properties -->
                <div class="mt-6 grid grid-cols-1 gap-x-10 gap-y-0.5 sm:grid-cols-2">
                  <!-- Status as a solid colour pill (the bucket's colour) -->
                  <div class="flex items-center gap-3 py-1.5">
                    <span class="flex w-28 shrink-0 items-center gap-2 text-[13px] sp-ink-3">
                      <FieldIcon kind="status" class="sp-ink-4" /> Status
                    </span>
                    <div class="min-w-0 flex-1">
                      <div class="relative inline-flex max-w-full">
                        <select
                          v-model="form[bucketField]"
                          class="sp-status-pill max-w-full cursor-pointer truncate"
                          :style="statusPillStyle"
                          @change="save"
                        >
                          <option v-for="b in config.buckets" :key="b.name" :value="b.name">{{ b.bucket_name }}</option>
                        </select>
                        <LucideChevronDown
                          class="pointer-events-none absolute right-1.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 opacity-80"
                          :style="{ color: statusPillStyle.color }"
                        />
                      </div>
                    </div>
                  </div>

                  <div v-for="f in metaFields" :key="f.fieldname" class="flex items-start gap-3 py-1.5">
                    <span
                      class="flex w-28 shrink-0 items-center gap-2 pt-1 text-[13px]"
                      :class="fieldInvalid(f) ? 'text-ink-red-3' : 'sp-ink-3'"
                    >
                      <FieldIcon :kind="iconKind(f)" class="sp-ink-4" /> {{ fieldRequired(f) ? f.label + ' *' : f.label }}
                    </span>
                    <div class="min-w-0 flex-1">
                      <div class="rounded-lg border transition" :class="fieldInvalid(f) ? 'border-ink-red-3 bg-surface-red-1/40' : 'border-transparent'">
                        <ChipField
                          v-if="chipFields.includes(f.fieldname)"
                          :model-value="form[f.fieldname] || ''"
                          :options="chipOptions[f.fieldname] || []"
                          :disabled="fieldReadOnly(f)"
                          @update:model-value="(v) => { form[f.fieldname] = v; clearInvalid(f.fieldname); save() }"
                        />
                        <select
                          v-else-if="f.fieldtype === 'Select'"
                          v-model="form[f.fieldname]"
                          class="sp-prop"
                          :disabled="fieldReadOnly(f)"
                          @change="() => { clearInvalid(f.fieldname); save() }"
                        >
                          <option value="">—</option>
                          <option v-for="o in (f.options || '').split('\n').filter(Boolean)" :key="o" :value="o">{{ o }}</option>
                        </select>
                        <input
                          v-else-if="f.fieldtype === 'Date'"
                          v-model="form[f.fieldname]"
                          type="date"
                          class="sp-prop"
                          :disabled="fieldReadOnly(f)"
                          @change="() => { clearInvalid(f.fieldname); save() }"
                        />
                        <LinkField
                          v-else-if="isTicket && f.fieldname === assigneeField"
                          :model-value="form[f.fieldname]"
                          :options="ticketMemberOptions"
                          :disabled="fieldReadOnly(f)"
                          @update:model-value="(v) => { form[f.fieldname] = v; clearInvalid(f.fieldname); save() }"
                        />
                        <LinkField
                          v-else-if="f.fieldtype === 'Link'"
                          :doctype="f.options"
                          :model-value="form[f.fieldname]"
                          :disabled="fieldReadOnly(f)"
                          @update:model-value="(v) => { form[f.fieldname] = v; clearInvalid(f.fieldname); save() }"
                        />
                        <DurationField
                          v-else-if="f.fieldtype === 'Duration'"
                          :model-value="form[f.fieldname] || 0"
                          :disabled="fieldReadOnly(f)"
                          @update:model-value="(v) => { form[f.fieldname] = v; clearInvalid(f.fieldname) }"
                          @commit="save"
                        />
                        <input
                          v-else
                          v-model="form[f.fieldname]"
                          class="sp-prop"
                          :disabled="fieldReadOnly(f)"
                          @input="clearInvalid(f.fieldname)"
                          @blur="save"
                        />
                      </div>
                      <p v-if="fieldInvalid(f)" class="mt-1 text-xs text-ink-red-3">Required for the current status.</p>
                    </div>
                  </div>
                </div>

                <!-- body — borderless, Notion-style canvas: format via the
                     selection bubble; block options appear on an empty line -->
                <div v-if="bodyField" class="mt-7">
                  <p class="mb-1 text-sm font-medium text-ink-gray-7">{{ bodyLabel }}</p>
                  <div class="sp-body-editor -mx-3 rounded-xl px-3 py-1 transition">
                    <TextEditor
                      :content="form[bodyField] || ''"
                      :editable="true"
                      :bubbleMenu="bodyBubble"
                      :floatingMenu="true"
                      placeholder="Write something… select text to format, block options appear on an empty line"
                      editor-class="prose-sm max-w-none min-h-[200px] py-2 focus:outline-none"
                      @change="(html) => { form[bodyField] = html; save() }"
                    />
                  </div>
                </div>

                <!-- attachments (files + external links) -->
                <CardAttachments v-if="!creating" :doctype="doctype" :name="name" class="mt-7" />

                <!-- subtasks -->
                <div v-if="!isTicket" class="mt-7">
                  <p class="mb-2 flex items-center gap-1.5 text-sm font-medium text-ink-gray-7">
                    <LucideListChecks class="h-4 w-4 text-ink-gray-5" /> Subtasks
                    <span class="text-ink-gray-4">{{ subtasks.length }}</span>
                  </p>
                  <div class="flex flex-col gap-1.5">
                    <button
                      v-for="st in subtasks"
                      :key="st.name"
                      class="group flex w-full items-center gap-2 rounded-md border sp-hair px-3 py-1.5 text-left text-sm transition hover:border-outline-gray-3 hover:bg-surface-gray-2"
                      @click="$emit('open-task', st.name)"
                    >
                      <span v-if="badgeField && st[badgeField]" class="h-2 w-2 shrink-0 rounded-full" :style="{ background: colorFor(st[badgeField]) }" />
                      <span v-else class="h-1.5 w-1.5 shrink-0 rounded-full bg-ink-gray-4" />
                      <span class="truncate text-ink-gray-8">{{ st[titleField] }}</span>
                      <LucideArrowUpRight class="sp-reveal h-3.5 w-3.5 shrink-0 text-ink-gray-4 opacity-0 transition group-hover:opacity-100" />
                      <span class="ml-auto flex shrink-0 items-center gap-2">
                        <span v-if="assigneeField && st[assigneeField]" class="text-xs text-ink-gray-5">
                          <UserAvatar :user="st[assigneeField]" size="sm" />
                        </span>
                        <span v-if="st.due_date" class="text-xs text-ink-gray-5">{{ formatDue(st.due_date) }}</span>
                        <span v-if="badgeField && st[badgeField]" class="text-xs text-ink-gray-6">{{ st[badgeField] }}</span>
                      </span>
                    </button>
                  </div>
                  <input
                    v-if="!creating"
                    v-model="newSubtask"
                    placeholder="+ Add subtask"
                    class="mt-2 w-full rounded-md border sp-hair px-3 py-1.5 text-sm focus:border-outline-gray-3 focus:outline-none"
                    @keyup.enter="addSubtask"
                  />
                  <p v-else class="mt-2 text-xs sp-ink-4">Create the task first to add subtasks.</p>
                </div>
              </div>

              <div v-if="creating" class="flex items-center justify-end gap-2 border-t sp-hair px-4 py-3 md:px-8">
                <Button variant="subtle" @click="$emit('close')">Cancel</Button>
                <AccentButton :loading="busy" @click="create">Create {{ noun }}</AccentButton>
              </div>
            </div>

            <!-- ================= ACTIVITY ================= -->
            <aside
              v-show="!breakpoint.isMobile || mobileTab === 'activity'"
              class="flex w-[360px] shrink-0 flex-col border-l sp-hair bg-surface-gray-1 max-md:w-full max-md:border-l-0"
            >
              <div class="flex items-center justify-between border-b sp-hair px-4 py-3">
                <span class="text-sm font-semibold text-ink-gray-8">Activity</span>
                <div class="flex items-center gap-1">
                  <button
                    v-if="!creating"
                    class="flex items-center gap-1 rounded-md px-1.5 py-1 text-xs transition"
                    :class="watching
                      ? 'bg-[var(--sp-accent-tint)] font-medium text-[color:var(--sp-accent)]'
                      : 'text-ink-gray-5 hover:bg-surface-gray-3 hover:text-ink-gray-8'"
                    :title="watching ? 'Stop watching this card' : 'Get notified when this card changes'"
                    :aria-pressed="watching"
                    @click="toggleWatch"
                  >
                    <LucideBellRing v-if="watching" class="h-3.5 w-3.5" />
                    <LucideBell v-else class="h-3.5 w-3.5" />
                    {{ watching ? 'Watching' : 'Watch' }}
                    <span v-if="watchers.length" class="sp-tnum">· {{ watchers.length }}</span>
                  </button>
                  <button aria-label="Close" class="rounded p-1 text-ink-gray-5 hover:bg-surface-gray-3 hover:text-ink-gray-8 max-md:hidden" @click="$emit('close')">
                    <LucideX class="h-4 w-4" />
                  </button>
                </div>
              </div>

              <div class="sp-scroll flex-1 space-y-4 overflow-y-auto px-4 py-4">
                <div v-for="(a, i) in activity" :key="i" class="flex gap-2.5 text-sm">
                  <UserAvatar :user="a.user" size="md" class="mt-0.5 shrink-0" />
                  <div class="min-w-0 flex-1">
                    <template v-if="a.type === 'comment'">
                      <p class="text-ink-gray-7">
                        <span class="font-medium text-ink-gray-8">{{ userLabel(a.user) }}</span>
                        <span class="ml-1.5 text-xs text-ink-gray-4">{{ when(a.time) }}</span>
                      </p>
                      <div class="mt-1 whitespace-pre-wrap rounded-lg rounded-tl-none bg-surface-white px-3 py-2 text-ink-gray-8 ring-1 ring-outline-gray-1"><template v-for="(p, pi) in commentParts(a.content)" :key="pi"><span v-if="p.t === 'mention'" class="rounded bg-[var(--sp-accent-tint)] px-1 font-medium text-[color:var(--sp-accent)]">@{{ p.v }}</span><template v-else>{{ p.v }}</template></template></div>
                    </template>
                    <template v-else-if="a.type === 'change'">
                      <p class="leading-snug text-ink-gray-6">
                        <span class="font-medium text-ink-gray-8">{{ userLabel(a.user) }}</span>
                        {{ a.old ? 'changed' : 'set' }}
                        <span class="font-medium text-ink-gray-7">{{ a.field }}</span>
                        <template v-if="a.old"> from <span class="text-ink-gray-7">{{ a.old }}</span></template>
                        to <span class="text-ink-gray-7">{{ a.new ?? '—' }}</span>
                      </p>
                      <p class="text-xs text-ink-gray-4">{{ when(a.time) }}</p>
                    </template>
                    <template v-else>
                      <p class="text-ink-gray-6">
                        <span class="font-medium text-ink-gray-8">{{ userLabel(a.user) }}</span> created this {{ noun }}
                      </p>
                      <p class="text-xs text-ink-gray-4">{{ when(a.time) }}</p>
                    </template>
                  </div>
                </div>
                <p v-if="creating" class="text-sm text-ink-gray-4">Activity & comments appear once the task is created.</p>
                <p v-else-if="!activity.length && !loading" class="text-sm text-ink-gray-4">No activity yet.</p>
              </div>

              <div class="relative border-t sp-hair p-3">
                <!-- @mention suggestions -->
                <div
                  v-if="mentionOpen && mentionMatches.length"
                  class="sp-pop absolute bottom-[64px] left-3 right-3 z-20 max-h-44 overflow-auto p-1"
                >
                  <button
                    v-for="(u, i) in mentionMatches"
                    :key="u.value"
                    class="flex w-full items-center gap-2 rounded-md px-2 py-1.5 text-left text-sm transition"
                    :class="i === mentionActive ? 'bg-[var(--sp-accent-tint)]' : 'hover:bg-[var(--sp-fill)]'"
                    @mousedown.prevent="pickMention(u)"
                  >
                    <UserAvatar :user="u.value" size="sm" />
                    <span class="truncate text-ink-gray-8">{{ u.label }}</span>
                  </button>
                </div>

                <textarea
                  ref="commentEl"
                  v-model="newComment"
                  rows="2"
                  :disabled="creating"
                  placeholder="Write a comment…  use @ to mention"
                  class="w-full resize-none rounded-lg border sp-hair px-3 py-2 text-sm focus:outline-none disabled:opacity-50"
                  @input="onCommentInput"
                  @keydown="onCommentKeydown"
                  @focus="onCommentFocus"
                />
                <div class="mt-2 flex justify-end">
                  <AccentButton :disabled="creating || !newComment.trim()" :loading="commenting" @click="postComment">
                    Comment
                  </AccentButton>
                </div>
              </div>
            </aside>
            </div>

            <NameDialog
              v-if="savingTemplate"
              title="Save as template"
              message="New cards can start from this card's current field values."
              placeholder="Template name…"
              confirm-label="Save template"
              :loading="templateBusy"
              @close="savingTemplate = false"
              @submit="saveAsTemplate"
            />
          </div>
        </transition>
      </div>
    </transition>
  </Teleport>
</template>

<script setup>
import { computed, nextTick, reactive, ref, watch } from 'vue'
import { Button, TextEditor, call } from 'frappe-ui'
import LinkField from '@/components/LinkField.vue'
import UserAvatar from '@/components/UserAvatar.vue'
import FieldIcon from '@/components/FieldIcon.vue'
import AccentButton from '@/components/AccentButton.vue'
import ChipField from '@/components/ChipField.vue'
import DurationField from '@/components/DurationField.vue'
import CardAttachments from '@/components/CardAttachments.vue'
import NameDialog from '@/components/NameDialog.vue'
import { ensureUsers, userLabel, userOptions, canManage } from '@/lib/users'
import { colorFor } from '@/lib/board'
import { fieldIsMandatory, fieldIsReadOnly, fieldIsVisible } from '@/lib/depends'
import { formatDate, when, stripHtml, contrastText } from '@/lib/format'
import { useSpacePointers } from '@/composables/useSpacePointers'
import { useOverlay } from '@/composables/useOverlay'
import { breakpoint } from '@/composables/useBreakpoint'
import { pushToast, errorMessage } from '@/store'

const props = defineProps({
  doctype: String,
  name: String,
  config: Object,
  creating: Boolean,
  presetField: String,
  presetValue: { type: null, default: null },
})
const emit = defineEmits(['close', 'saved', 'created', 'open-task'])

const busy = ref(false)
const titleEl = ref(null)
const panelEl = ref(null)
const parentTitle = ref('')

// phones show one pane at a time (Details | Activity); reset per card
const mobileTab = ref('details')
watch(() => props.name, () => (mobileTab.value = 'details'))

// Esc: dismiss the @mention popup first, then close the drawer
useOverlay({
  close: () => {
    if (mentionOpen.value) mentionOpen.value = false
    else emit('close')
  },
  panel: panelEl,
})

const {
  titleField, bucketField, bodyField, assigneeField, badgeField,
  chipFields, chipOptions, parentField, isTicket, noun, nounLabel,
} = useSpacePointers(() => props.config)
const shortId = computed(() => String(props.name).slice(0, 8))
const ticketMemberOptions = computed(() =>
  (props.config?.space?.ticket_members || []).map((u) => ({ label: userLabel(u), value: u })),
)

const formatDue = formatDate
const bodyLabel = computed(() => {
  const f = (props.config?.fields || []).find((x) => x.fieldname === bodyField.value)
  return f?.label || 'Description'
})
const metaFields = computed(() =>
  (props.config?.fields || []).filter(
    (f) =>
      ![titleField.value, bodyField.value, bucketField.value, parentField.value].includes(f.fieldname) &&
      !(isTicket.value && (f.fieldname === 'requester' || f.read_only)) &&
      fieldVisible(f),
  ),
)
function fieldVisible(f) {
  return fieldIsVisible(f, form)
}
function fieldRequired(f) {
  return fieldIsMandatory(f, form)
}
function fieldReadOnly(f) {
  return fieldIsReadOnly(f, form)
}

// ---- ClickUp-style property presentation ----------------------------------
// pick a leading icon per field by its role / type
function iconKind(f) {
  if (f.fieldname === assigneeField.value || (f.fieldtype === 'Link' && f.options === 'User')) return 'user'
  if (f.fieldname === badgeField.value) return 'points'
  if (f.fieldtype === 'Date') return 'date'
  if (f.fieldtype === 'Duration') return 'duration'
  if (chipFields.value.includes(f.fieldname)) return 'tags'
  if (['Int', 'Float', 'Currency', 'Percent'].includes(f.fieldtype)) return 'number'
  if (f.fieldtype === 'Check') return 'check'
  if (f.fieldtype === 'Link') return 'link'
  if (f.fieldtype === 'Select') return 'status'
  return 'field'
}
// Status shows as a solid pill in the bucket's colour, with readable text.
function bucketColorOf(name) {
  return (props.config?.buckets || []).find((b) => b.name === name)?.color || '#8e8e93'
}
const statusPillStyle = computed(() => {
  const c = bucketColorOf(form[bucketField.value])
  return { background: c, color: contrastText(c), backgroundImage: 'none' }
})

// no fixed toolbar — everything lives in the selection bubble (plus the
// floating block menu on empty lines). FontColor covers colour + highlight.
// Phones get the essentials only, so the bubble fits the screen and doesn't
// fight the native selection callout.
const bodyBubble = computed(() =>
  breakpoint.isMobile
    ? ['Bold', 'Italic', 'Underline', 'Separator', 'Bullet List', 'Numbered List', 'Link']
    : [
        'Paragraph', 'Heading 2', 'Heading 3', 'Separator',
        'Bold', 'Italic', 'Underline', 'Strikethrough', 'FontColor', 'Separator',
        'Bullet List', 'Numbered List', 'Task List', 'Separator',
        'Blockquote', 'Code', 'Link',
      ],
)

const canManageSession = computed(() => canManage())

// ---- watchers (follow this card) -------------------------------------------
const watching = ref(false)
const watchers = ref([])
async function loadWatch() {
  try {
    const w = await call('sprint.api.get_watch', { doctype: props.doctype, name: props.name })
    watching.value = !!w.watching
    watchers.value = w.watchers || []
  } catch { /* watching is best-effort */ }
}
async function toggleWatch() {
  try {
    const w = await call('sprint.api.toggle_watch', { doctype: props.doctype, name: props.name })
    watching.value = !!w.watching
    watchers.value = w.watchers || []
  } catch (e) {
    pushToast(errorMessage(e))
  }
}

// ---- card templates ---------------------------------------------------------
const templates = ref([])
const appliedTemplate = ref(null)
const savingTemplate = ref(false)
const templateBusy = ref(false)
async function loadTemplates() {
  try {
    templates.value = await call('sprint.api.get_templates', { space: props.config?.space?.name })
  } catch {
    templates.value = []
  }
}
function applyTemplate(t) {
  for (const [k, v] of Object.entries(t.values || {})) form[k] = v
  appliedTemplate.value = t.name
  refreshInvalidFields()
}
async function saveAsTemplate(templateName) {
  templateBusy.value = true
  try {
    const values = {}
    for (const f of [titleField.value, bucketField.value, bodyField.value, ...metaFields.value.map((x) => x.fieldname)]) {
      if (f && form[f] != null && form[f] !== '') values[f] = form[f]
    }
    await call('sprint.api.save_template', {
      space: props.config?.space?.name,
      template_name: templateName,
      values: JSON.stringify(values),
    })
    savingTemplate.value = false
    pushToast(`Template “${templateName}” saved`, 'success')
  } catch (e) {
    pushToast(errorMessage(e))
  } finally {
    templateBusy.value = false
  }
}

// ---- @mention highlighting in the activity feed -----------------------------
// splits a comment into text/mention parts by matching @<known full name>
function commentParts(content) {
  const text = stripHtml(content)
  const labels = userOptions()
    .map((u) => u.label)
    .filter(Boolean)
    .sort((a, b) => b.length - a.length)
  const parts = []
  let rest = text
  while (rest.length) {
    const at = rest.indexOf('@')
    if (at < 0) {
      parts.push({ t: 'text', v: rest })
      break
    }
    const hit = labels.find((l) => rest.startsWith('@' + l, at))
    if (!hit) {
      parts.push({ t: 'text', v: rest.slice(0, at + 1) })
      rest = rest.slice(at + 1)
      continue
    }
    if (at) parts.push({ t: 'text', v: rest.slice(0, at) })
    parts.push({ t: 'mention', v: hit })
    rest = rest.slice(at + 1 + hit.length)
  }
  return parts
}

const form = reactive({})
const invalidFields = reactive({})
const loading = ref(true)
const subtasks = ref([])
const newSubtask = ref('')
const activity = ref([])
const newComment = ref('')
const commenting = ref(false)
let saveTimer = null

// ---- @mentions in the comment composer ------------------------------------
const commentEl = ref(null)
const mentionOpen = ref(false)
const mentionQuery = ref('')
const mentionActive = ref(0)
const mentioned = ref([]) // user ids the author picked

const mentionMatches = computed(() => {
  const q = mentionQuery.value.toLowerCase()
  return userOptions()
    .filter((u) => !q || u.label.toLowerCase().includes(q) || String(u.value).toLowerCase().includes(q))
    .slice(0, 6)
})
// iOS doesn't shrink the layout viewport for the keyboard — nudge the
// composer into view once the keyboard has animated in.
function onCommentFocus(e) {
  if (!breakpoint.isTouch) return
  const el = e.target
  setTimeout(() => el.scrollIntoView({ block: 'center', behavior: 'smooth' }), 300)
}

function onCommentInput(e) {
  const caret = e.target.selectionStart
  const m = newComment.value.slice(0, caret).match(/(^|\s)@([\w.\-@]*)$/)
  if (m) {
    mentionQuery.value = m[2]
    mentionActive.value = 0
    mentionOpen.value = true
  } else {
    mentionOpen.value = false
  }
}
function onCommentKeydown(e) {
  if (mentionOpen.value && mentionMatches.value.length) {
    if (e.key === 'ArrowDown') { e.preventDefault(); mentionActive.value = (mentionActive.value + 1) % mentionMatches.value.length; return }
    if (e.key === 'ArrowUp') { e.preventDefault(); mentionActive.value = (mentionActive.value - 1 + mentionMatches.value.length) % mentionMatches.value.length; return }
    if (e.key === 'Enter' || e.key === 'Tab') { e.preventDefault(); pickMention(mentionMatches.value[mentionActive.value]); return }
    // Escape is handled by the overlay stack (dismisses the popup first)
  }
  if ((e.metaKey || e.ctrlKey) && e.key === 'Enter') { e.preventDefault(); postComment() }
}
function pickMention(u) {
  if (!u) return
  const el = commentEl.value
  const caret = el ? el.selectionStart : newComment.value.length
  const before = newComment.value.slice(0, caret).replace(/(^|\s)@([\w.\-@]*)$/, (full, pre) => `${pre}@${u.label} `)
  const after = newComment.value.slice(caret)
  newComment.value = before + after
  if (!mentioned.value.includes(u.value)) mentioned.value.push(u.value)
  mentionOpen.value = false
  nextTick(() => {
    el?.focus()
    el?.setSelectionRange(before.length, before.length)
  })
}

ensureUsers()

async function loadDoc() {
  Object.keys(form).forEach((k) => delete form[k])
  if (props.creating) {
    // blank draft — nothing is written until "Create task"
    form[titleField.value] = ''
    if (props.presetField && props.presetValue != null) form[props.presetField] = props.presetValue
    subtasks.value = []
    activity.value = []
    appliedTemplate.value = null
    if (!isTicket.value) loadTemplates()
    loading.value = false
    // don't pop the on-screen keyboard over a fresh sheet on touch devices
    if (!breakpoint.isTouch) nextTick(() => titleEl.value?.focus())
    return
  }
  loading.value = true
  parentTitle.value = ''
  watching.value = false
  watchers.value = []
  const doc = isTicket.value
    ? await call('sprint.api.get_ticket', { doctype: props.doctype, name: props.name })
    : await call('frappe.client.get', { doctype: props.doctype, name: props.name })
  Object.assign(form, doc)
  await Promise.all([
    isTicket.value ? Promise.resolve() : loadSubtasks(),
    loadActivity(),
    loadParentTitle(),
    loadWatch(),
  ])
  loading.value = false
}

async function loadParentTitle() {
  const parent = form[parentField.value]
  if (!parent) return
  const r = await call('frappe.client.get_value', {
    doctype: props.doctype,
    filters: { name: parent },
    fieldname: titleField.value,
  })
  parentTitle.value = r?.[titleField.value] || ''
}
async function loadSubtasks() {
  const fields = ['name', titleField.value]
  if (badgeField.value) fields.push(badgeField.value)
  if (assigneeField.value) fields.push(assigneeField.value)
  if ((props.config?.fields || []).some((f) => f.fieldname === 'due_date')) fields.push('due_date')
  subtasks.value = await call('frappe.client.get_list', {
    doctype: props.doctype,
    filters: { [parentField.value]: props.name },
    fields: [...new Set(fields)],
    limit_page_length: 0,
  })
}
async function loadActivity() {
  activity.value = await call('sprint.api.get_activity', { doctype: props.doctype, name: props.name })
}

function save() {
  if (props.creating) return // no record yet — saved on Create
  refreshInvalidFields()
  // debounce: collect rapid field edits, persist, then refresh the audit feed
  clearTimeout(saveTimer)
  saveTimer = setTimeout(doSave, 400)
}

async function create() {
  // client-side required check so Create never silently no-ops
  const reqd = [titleField.value, ...metaFields.value.filter((f) => fieldRequired(f)).map((f) => f.fieldname)]
  const missing = reqd.filter((fn) => fn && (form[fn] == null || String(form[fn]).trim() === ''))
  if (missing.length) {
    const labels = missing.map((fn) => fieldLabel(fn))
    pushToast(`Please fill: ${labels.join(', ')}`)
    titleEl.value?.focus()
    return
  }
  busy.value = true
  try {
    const payload = { doctype: props.doctype }
    for (const f of [titleField.value, bucketField.value, bodyField.value, ...metaFields.value.map((x) => x.fieldname)]) {
      if (f && form[f] != null && form[f] !== '') payload[f] = form[f]
    }
    const res = isTicket.value
      ? await call('sprint.api.create_ticket', {
          space: props.config?.space?.name,
          title: payload[titleField.value],
          description: bodyField.value ? payload[bodyField.value] : '',
          assignee: assigneeField.value ? payload[assigneeField.value] : '',
          priority: badgeField.value ? payload[badgeField.value] : '',
          bucket: payload[bucketField.value],
          values: JSON.stringify(payload),
        })
      : await call('sprint.api.create_card', {
          space: props.config?.space?.name,
          values: JSON.stringify(payload),
        })
    emit('created', res.name)
  } catch (e) {
    pushToast(errorMessage(e))
  } finally {
    busy.value = false
  }
}
async function doSave() {
  const missing = refreshInvalidFields()
  if (missing.length) {
    pushToast(`Please fill: ${missing.join(', ')}`)
    return
  }
  const payload = {}
  for (const f of [bucketField.value, titleField.value, bodyField.value, ...metaFields.value.map((x) => x.fieldname)]) {
    if (f && f in form) payload[f] = form[f]
  }
  try {
    if (isTicket.value) {
      await call('sprint.api.update_ticket', {
        doctype: props.doctype,
        name: props.name,
        values: JSON.stringify(payload),
      })
    } else {
      await call('sprint.api.update_card', {
        doctype: props.doctype,
        name: props.name,
        values: JSON.stringify(payload),
      })
    }
    emit('saved')
    Object.keys(invalidFields).forEach((k) => delete invalidFields[k])
    loadActivity()
  } catch (e) {
    // autosave failed (e.g. a required field is blank) — surface it; the
    // field is right here in the drawer for the user to fix, then it retries.
    pushToast(errorMessage(e))
  }
}
function fieldLabel(fn) {
  if (fn === titleField.value) return 'Title'
  return (props.config?.fields || []).find((f) => f.fieldname === fn)?.label || fn
}
function missingMandatoryFields() {
  return [titleField.value, ...metaFields.value.filter((f) => fieldRequired(f)).map((f) => f.fieldname)]
    .filter((fn) => fn && (form[fn] == null || String(form[fn]).trim() === ''))
    .map((fn) => fieldLabel(fn))
}
function refreshInvalidFields() {
  Object.keys(invalidFields).forEach((k) => delete invalidFields[k])
  for (const f of metaFields.value.filter((field) => fieldRequired(field))) {
    if (form[f.fieldname] == null || String(form[f.fieldname]).trim() === '') {
      invalidFields[f.fieldname] = true
    }
  }
  return missingMandatoryFields()
}
function fieldInvalid(f) {
  return !!invalidFields[f.fieldname]
}
function clearInvalid(fieldname) {
  if (form[fieldname] != null && String(form[fieldname]).trim() !== '') delete invalidFields[fieldname]
}

async function addSubtask() {
  const title = newSubtask.value.trim()
  if (!title) return
  newSubtask.value = ''
  await call('frappe.client.insert', {
    doc: {
      doctype: props.doctype,
      [titleField.value]: title,
      [parentField.value]: props.name,
      [bucketField.value]: form[bucketField.value],
    },
  })
  await loadSubtasks()
  emit('saved')
}

async function postComment() {
  const content = newComment.value.trim()
  if (!content) return
  // only notify mentions whose @Name token is still present in the text
  const tagged = mentioned.value.filter((id) => content.includes('@' + userLabel(id)))
  commenting.value = true
  newComment.value = ''
  mentioned.value = []
  mentionOpen.value = false
  try {
    await call('sprint.api.add_comment', {
      doctype: props.doctype,
      name: props.name,
      content,
      mentions: JSON.stringify(tagged),
    })
    await loadActivity()
  } finally {
    commenting.value = false
  }
}

watch(() => props.name, loadDoc, { immediate: true })
</script>

<style scoped>
.sp-prop {
  width: 100%;
  background: transparent;
  border: none;
  appearance: none;
  -webkit-appearance: none;
  border-radius: 8px;
  padding: 0.3rem 0.45rem;
  font-size: 0.875rem;
  letter-spacing: -0.01em;
  color: rgb(var(--sp-ink) / 0.88);
  transition: background 0.12s ease;
}
.sp-prop:hover {
  background: var(--sp-fill);
}
.sp-prop:focus {
  outline: none;
  box-shadow: none;
  background: var(--sp-fill-hover);
}
.sp-status-pill {
  appearance: none;
  -webkit-appearance: none;
  border: 0;
  border-radius: 8px;
  padding: 0.28rem 1.6rem 0.28rem 0.6rem;
  font-size: 0.72rem;
  font-weight: 600;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  line-height: 1.1;
  transition: filter 0.12s ease;
}
.sp-status-pill:hover { filter: brightness(1.06); }
.sp-status-pill:focus { outline: none; box-shadow: none; }
</style>
