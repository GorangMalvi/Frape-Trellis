<template>
  <div>
    <p class="mb-2 flex items-center gap-1.5 text-sm font-medium text-ink-gray-7">
      <LucidePaperclip class="h-4 w-4 text-ink-gray-5" /> Attachments
      <span class="text-ink-gray-4">{{ items.length }}</span>
    </p>

    <!-- list -->
    <div v-if="items.length" class="mb-2 flex flex-col gap-1.5">
      <div
        v-for="f in items"
        :key="f.name"
        class="group flex items-center gap-2.5 rounded-md border sp-hair px-3 py-2 transition hover:border-outline-gray-3 hover:bg-surface-gray-2"
      >
        <component :is="iconFor(f)" class="h-4 w-4 shrink-0" :class="colorFor(f)" />
        <a
          :href="f.file_url"
          target="_blank"
          rel="noopener"
          class="min-w-0 flex-1 truncate text-sm text-ink-gray-8 hover:text-[color:var(--sp-accent)] hover:underline"
          :title="f.file_name"
        >
          {{ f.file_name }}
        </a>
        <span v-if="f.file_size" class="shrink-0 text-xs text-ink-gray-4">{{ fmtSize(f.file_size) }}</span>
        <LucideExternalLink v-if="isLink(f)" class="h-3.5 w-3.5 shrink-0 text-ink-gray-4" />
        <button
          class="sp-reveal shrink-0 rounded p-1 text-ink-gray-4 opacity-0 transition hover:bg-[var(--sp-fill-hover)] hover:text-ink-red-3 group-hover:opacity-100"
          title="Remove"
          aria-label="Remove attachment"
          @click="remove(f)"
        >
          <LucideX class="h-3.5 w-3.5" />
        </button>
      </div>
    </div>

    <!-- add-link row -->
    <div v-if="linking" class="mb-2 flex items-center gap-2">
      <input
        v-model="linkUrl"
        ref="linkEl"
        placeholder="Paste a Google Doc / Sheet URL…"
        class="h-8 flex-1 rounded-md border sp-hair px-2.5 text-sm focus:border-outline-gray-3 focus:outline-none"
        @keyup.enter="saveLink"
      />
      <input
        v-model="linkLabel"
        placeholder="Label (optional)"
        class="h-8 w-32 rounded-md border sp-hair px-2.5 text-sm focus:border-outline-gray-3 focus:outline-none"
        @keyup.enter="saveLink"
      />
      <Button variant="solid" :loading="busy" @click="saveLink">Add</Button>
      <button class="sp-control p-1.5" @click="linking = false"><LucideX class="h-3.5 w-3.5" /></button>
    </div>

    <!-- actions -->
    <div class="flex items-center gap-2">
      <button
        class="flex items-center gap-1.5 rounded-md border sp-hair px-2.5 py-1.5 text-sm sp-ink-2 transition hover:border-outline-gray-3 hover:text-ink-gray-8 disabled:opacity-50"
        :disabled="busy"
        @click="fileEl?.click()"
      >
        <LucideUpload class="h-3.5 w-3.5" /> {{ busy ? 'Uploading…' : 'Upload file' }}
      </button>
      <button
        class="flex items-center gap-1.5 rounded-md border sp-hair px-2.5 py-1.5 text-sm sp-ink-2 transition hover:border-outline-gray-3 hover:text-ink-gray-8"
        @click="openLink"
      >
        <LucideLink class="h-3.5 w-3.5" /> Add link
      </button>
      <input ref="fileEl" type="file" class="hidden" @change="onPick" />
    </div>
  </div>
</template>

<script setup>
import { nextTick, ref, watch } from 'vue'
import { Button, call, createResource } from 'frappe-ui'
import { pushToast, errorMessage, confirmDelete } from '@/store'
import { canManage } from '@/lib/users'

const props = defineProps({ doctype: String, name: String })

const items = ref([])
const attachments = createResource({
  url: 'sprint.api.get_attachments',
  makeParams: () => ({ doctype: props.doctype, name: props.name }),
  onSuccess: (d) => (items.value = d || []),
})
function reload() {
  if (props.doctype && props.name) attachments.fetch()
}
watch(() => props.name, reload, { immediate: true })

const busy = ref(false)
const fileEl = ref(null)
const linking = ref(false)
const linkEl = ref(null)
const linkUrl = ref('')
const linkLabel = ref('')

async function onPick(e) {
  const file = e.target.files?.[0]
  e.target.value = '' // allow re-picking the same file
  if (!file) return
  busy.value = true
  try {
    const fd = new FormData()
    fd.append('file', file, file.name)
    fd.append('doctype', props.doctype)
    fd.append('docname', props.name)
    fd.append('is_private', '0')
    const res = await fetch('/api/method/upload_file', {
      method: 'POST',
      headers: { 'X-Frappe-CSRF-Token': window.csrf_token || '' },
      body: fd,
    })
    if (!res.ok) throw new Error((await res.text()).slice(0, 300))
    reload()
  } catch (err) {
    pushToast(err.message || 'Upload failed')
  } finally {
    busy.value = false
  }
}

function openLink() {
  linking.value = true
  nextTick(() => linkEl.value?.focus())
}
async function saveLink() {
  if (!linkUrl.value.trim()) return
  busy.value = true
  try {
    await call('sprint.api.add_file_link', {
      doctype: props.doctype,
      name: props.name,
      url: linkUrl.value.trim(),
      label: linkLabel.value.trim(),
    })
    linkUrl.value = ''
    linkLabel.value = ''
    linking.value = false
    reload()
  } catch (err) {
    pushToast(errorMessage(err))
  } finally {
    busy.value = false
  }
}
async function remove(f) {
  const ok = await confirmDelete({
    title: 'Remove attachment?',
    message: `“${f.file_name}” will be removed from this task.`,
    confirmLabel: 'Remove',
    requirePassword: canManage(),
  })
  if (!ok) return
  try {
    await call('sprint.api.remove_attachment', { file_name: f.name })
    reload()
  } catch (err) {
    pushToast(errorMessage(err))
  }
}

// ---- display helpers ----
function isLink(f) {
  return /^https?:\/\//.test(f.file_url || '') && !/^https?:\/\/[^/]+\/(private\/)?files\//.test(f.file_url || '')
}
function kind(f) {
  const u = (f.file_url || '').toLowerCase()
  const n = (f.file_name || '').toLowerCase()
  if (u.includes('docs.google.com/spreadsheets')) return 'gsheet'
  if (u.includes('docs.google.com/document')) return 'gdoc'
  if (/\.(xlsx|xls|csv)(\?|$)/.test(u) || /\.(xlsx|xls|csv)$/.test(n)) return 'sheet'
  if (/\.(docx?|odt)(\?|$)/.test(u) || /\.(docx?|odt)$/.test(n)) return 'doc'
  if (/\.pdf(\?|$)/.test(u) || n.endsWith('.pdf')) return 'pdf'
  if (isLink(f)) return 'link'
  return 'file'
}
function iconFor(f) {
  return {
    gsheet: 'LucideSheet', sheet: 'LucideSheet',
    gdoc: 'LucideFileText', doc: 'LucideFileText', pdf: 'LucideFileText',
    link: 'LucideLink', file: 'LucideFile',
  }[kind(f)]
}
function colorFor(f) {
  return {
    gsheet: 'text-ink-green-3', sheet: 'text-ink-green-3',
    gdoc: 'text-ink-blue-3', doc: 'text-ink-blue-3', pdf: 'text-ink-red-3',
    link: 'text-ink-gray-5', file: 'text-ink-gray-5',
  }[kind(f)]
}
function fmtSize(b) {
  if (!b) return ''
  const u = ['B', 'KB', 'MB', 'GB']
  let i = 0
  let n = b
  while (n >= 1024 && i < u.length - 1) {
    n /= 1024
    i++
  }
  return `${n.toFixed(n < 10 && i > 0 ? 1 : 0)} ${u[i]}`
}
</script>
