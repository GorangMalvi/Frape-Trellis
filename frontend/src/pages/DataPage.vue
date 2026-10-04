<template>
  <div class="h-full overflow-auto sp-ground">
    <div class="mx-auto max-w-3xl px-4 py-6 sm:px-8">
      <!-- header -->
      <div class="mb-6 flex items-center gap-2 text-sm">
        <button class="flex items-center gap-1 sp-ink-3 transition hover:text-ink-gray-8" @click="back">
          <LucideChevronLeft class="h-4 w-4" /> {{ cfg?.space?.label || space }}
        </button>
        <span class="sp-ink-4">/</span>
        <span class="font-medium text-ink-gray-8">Import &amp; Export</span>
      </div>

      <h1 class="text-xl font-semibold text-ink-gray-9">Import / Export</h1>
      <p class="mt-1 text-sm sp-ink-3">Move data in and out of <b>{{ cfg?.space?.label || space }}</b> as Excel (.xlsx).</p>

      <!-- export -->
      <section class="mt-6 rounded-xl border sp-hair p-4 sm:p-5">
        <div class="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h2 class="text-sm font-semibold text-ink-gray-9">Export</h2>
            <p class="mt-0.5 text-sm sp-ink-3">Every card, with <code>Ref</code> / <code>Parent Ref</code> columns so subtasks round-trip.</p>
          </div>
          <Button variant="solid" @click="exportXlsx">
            <template #prefix><LucideDownload class="h-4 w-4" /></template>
            Export to Excel
          </Button>
        </div>
      </section>

      <!-- import -->
      <section class="mt-5 rounded-xl border sp-hair p-4 sm:p-5">
        <div class="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h2 class="text-sm font-semibold text-ink-gray-9">Import</h2>
            <p class="mt-0.5 text-sm sp-ink-3">Upload a sheet, map its columns, then insert or update cards.</p>
          </div>
          <!-- step indicator -->
          <div class="flex items-center gap-1.5 text-xs">
            <span v-for="(s, i) in steps" :key="s.key" class="flex items-center gap-1.5">
              <span
                class="flex h-5 w-5 items-center justify-center rounded-full text-[11px] font-medium"
                :class="stepIndex >= i ? 'bg-[color:var(--sp-accent)] text-white' : 'bg-surface-gray-3 text-ink-gray-5'"
              >{{ i + 1 }}</span>
              <span class="max-sm:hidden" :class="stepIndex >= i ? 'text-ink-gray-8' : 'sp-ink-4'">{{ s.label }}</span>
              <LucideChevronRight v-if="i < steps.length - 1" class="h-3 w-3 text-ink-gray-3" />
            </span>
          </div>
        </div>

        <!-- step 1: choose file -->
        <div v-if="step === 'idle'" class="mt-4">
          <button
            class="flex w-full flex-col items-center justify-center gap-2 rounded-lg border border-dashed sp-hair py-10 text-sm sp-ink-2 transition hover:border-outline-gray-3 hover:text-ink-gray-8"
            :disabled="busy"
            @click="fileEl?.click()"
          >
            <LucideUpload class="h-6 w-6" />
            {{ busy ? 'Reading…' : 'Choose an .xlsx file' }}
            <span class="text-xs sp-ink-4">or export above, edit, and re-import</span>
          </button>
          <input ref="fileEl" type="file" accept=".xlsx" class="hidden" @change="onPick" />
          <p v-if="error" class="mt-2 text-sm text-ink-red-3">{{ error }}</p>
        </div>

        <!-- step 2: mapping -->
        <div v-else-if="step === 'mapping'" class="mt-4">
          <p class="mb-3 text-sm sp-ink-2">
            <b class="text-ink-gray-8">{{ preview.rows }}</b> row(s) found. Map each column to a field:
          </p>
          <div class="overflow-hidden rounded-lg border sp-hair">
            <div class="grid grid-cols-[1fr,auto,1.2fr] items-center gap-2 border-b sp-hair bg-surface-gray-2 px-3 py-2 sm:gap-3 sm:px-4 text-xs font-medium uppercase tracking-wide text-ink-gray-5">
              <div>Column</div><div></div><div>Maps to</div>
            </div>
            <div
              v-for="h in preview.headers"
              :key="h"
              class="grid grid-cols-[1fr,auto,1.2fr] items-center gap-2 border-b sp-hair px-3 py-2.5 last:border-0 sm:gap-3 sm:px-4"
            >
              <div class="min-w-0">
                <p class="truncate text-sm font-medium text-ink-gray-8" :title="h">{{ h || '(blank)' }}</p>
                <p v-if="sampleFor(h)" class="truncate text-xs sp-ink-4" :title="sampleFor(h)">e.g. {{ sampleFor(h) }}</p>
              </div>
              <LucideArrowRight class="h-3.5 w-3.5 text-ink-gray-4" />
              <select v-model="map[h]" class="min-w-0 rounded-md border sp-hair bg-surface-white px-2 py-1.5 text-sm focus:outline-none">
                <option value="">— Ignore —</option>
                <option value="__ref__">Ref (row id, for subtasks)</option>
                <option value="__parent_ref__">Parent Ref (subtask → parent)</option>
                <optgroup label="Fields">
                  <option v-for="f in fields" :key="f.fieldname" :value="f.fieldname">{{ f.label }}</option>
                </optgroup>
              </select>
            </div>
          </div>

          <label class="mt-4 flex flex-wrap items-center gap-2 text-sm text-ink-gray-7">
            <input type="checkbox" v-model="doUpdate" class="rounded" />
            Update existing rows, matched by
            <select v-model="updateKey" :disabled="!doUpdate" class="rounded-md border sp-hair bg-surface-white px-2 py-1 text-sm focus:outline-none disabled:opacity-50">
              <option v-for="f in fields" :key="f.fieldname" :value="f.fieldname">{{ f.label }}</option>
            </select>
            <span class="sp-ink-4">(otherwise every row is inserted as new)</span>
          </label>

          <p v-if="error" class="mt-2 text-sm text-ink-red-3">{{ error }}</p>
          <div class="mt-4 flex justify-end gap-2">
            <Button variant="subtle" @click="reset">Cancel</Button>
            <Button variant="solid" :loading="busy" @click="runImport">Import {{ preview.rows }} row(s)</Button>
          </div>
        </div>

        <!-- step 3: result -->
        <div v-else-if="step === 'done'" class="mt-4">
          <div class="rounded-lg border sp-hair p-4 text-sm">
            <p class="font-medium text-ink-gray-8">
              <LucideCircleCheck class="mr-1 inline h-4 w-4 text-ink-green-3" />
              {{ result.created }} created<span v-if="result.updated">, {{ result.updated }} updated</span>.
            </p>
            <div v-if="result.errors?.length" class="mt-3">
              <p class="mb-1 font-medium text-ink-red-3">{{ result.errors.length }} row(s) failed:</p>
              <div class="max-h-56 overflow-auto rounded bg-surface-gray-2 p-2 font-mono text-xs text-ink-gray-7">
                <div v-for="(e, i) in result.errors" :key="i">Row {{ e.row }}: {{ e.error }}</div>
              </div>
            </div>
          </div>
          <div class="mt-4 flex justify-end gap-2">
            <Button variant="subtle" @click="reset">Import another</Button>
            <Button variant="solid" @click="back">Back to board</Button>
          </div>
        </div>
      </section>
    </div>
  </div>
</template>

<script setup>
import { computed, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { Button, call, createResource } from 'frappe-ui'
import { pushToast, errorMessage } from '@/store'

const props = defineProps({ space: String })
const router = useRouter()

const config = createResource({
  url: 'sprint.api.get_space',
  makeParams: () => ({ space: props.space }),
  auto: true,
})
const cfg = computed(() => config.data)
const fields = computed(() => cfg.value?.fields || [])

const steps = [
  { key: 'idle', label: 'File' },
  { key: 'mapping', label: 'Map columns' },
  { key: 'done', label: 'Result' },
]
const step = ref('idle')
const stepIndex = computed(() => steps.findIndex((s) => s.key === step.value))

const busy = ref(false)
const error = ref('')
const fileEl = ref(null)
const fileUrl = ref('')
const preview = ref({ headers: [], sample: [], rows: 0 })
const map = reactive({})
const doUpdate = ref(false)
const updateKey = ref('')
const result = ref({ created: 0, updated: 0, errors: [] })

function back() {
  router.push({ name: 'Board', params: { space: props.space } })
}
function exportXlsx() {
  window.open(`/api/method/sprint.api.export_space?space=${encodeURIComponent(props.space)}`, '_blank')
}
function sampleFor(h) {
  const i = preview.value.headers.indexOf(h)
  const row = preview.value.sample?.[0]
  return i >= 0 && row ? row[i] : ''
}

async function onPick(e) {
  const file = e.target.files?.[0]
  e.target.value = ''
  if (!file) return
  error.value = ''
  busy.value = true
  try {
    const fd = new FormData()
    fd.append('file', file, file.name)
    fd.append('is_private', '1')
    const res = await fetch('/api/method/upload_file', {
      method: 'POST',
      headers: { 'X-Frappe-CSRF-Token': window.csrf_token || '' },
      body: fd,
    })
    if (!res.ok) throw new Error((await res.text()).slice(0, 200))
    fileUrl.value = (await res.json()).message.file_url

    const pv = await call('sprint.api.import_preview', { space: props.space, file_url: fileUrl.value })
    preview.value = pv
    for (const h of pv.headers) map[h] = pv.suggested[h] || ''
    const titleField = cfg.value?.space?.title_field || 'title'
    updateKey.value = fields.value.find((f) => f.fieldname === titleField)?.fieldname || fields.value[0]?.fieldname || ''
    step.value = 'mapping'
  } catch (err) {
    error.value = err.message || 'Could not read the file.'
  } finally {
    busy.value = false
  }
}

async function runImport() {
  error.value = ''
  busy.value = true
  try {
    result.value = await call('sprint.api.import_commit', {
      space: props.space,
      file_url: fileUrl.value,
      mapping: JSON.stringify(map),
      update_key: doUpdate.value ? updateKey.value : '',
    })
    step.value = 'done'
    pushToast(`Imported ${result.value.created + (result.value.updated || 0)} row(s)`, 'success')
  } catch (err) {
    error.value = errorMessage(err)
  } finally {
    busy.value = false
  }
}

function reset() {
  step.value = 'idle'
  error.value = ''
  fileUrl.value = ''
  preview.value = { headers: [], sample: [], rows: 0 }
  Object.keys(map).forEach((k) => delete map[k])
}
</script>
