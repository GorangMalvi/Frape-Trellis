import { computed, reactive, ref, watch } from 'vue'

// The Board's "which view am I looking at" state: the active builtin/saved
// view, the current group/sort/filter/me-mode config, dirty tracking against
// the saved view, and per-space persistence to sessionStorage so a reload
// keeps you exactly where you were. Extracted from Board.vue; the `views`
// resource and all mutations stay with the Board.
//
//   space       — getter for the current space name (route param)
//   views       — the createResource for sprint.api.get_views
//   bucketField — computed pointer (default group-by)
//   dueField    — computed pointer; the Calendar builtin only exists with one
//   search, subtaskMode — Board-owned refs, persisted alongside the view
export function useViewState({ space, views, bucketField, dueField, search, subtaskMode }) {
  function builtinView(type) {
    return {
      view_type: type,
      group_by: bucketField.value,
      sort_field: '',
      sort_dir: 'asc',
      me_mode: false,
      filters: [],
    }
  }
  const view = reactive(builtinView('board'))
  const activeKey = ref('board')

  const builtins = computed(() => {
    const out = [
      { key: 'board', view_name: 'Board', view_type: 'board', _builtin: true },
      { key: 'list', view_name: 'List', view_type: 'list', _builtin: true },
    ]
    if (dueField?.value) {
      out.push({ key: 'calendar', view_name: 'Calendar', view_type: 'calendar', _builtin: true })
    }
    return out
  })
  const savedViews = computed(() =>
    (views.data || []).map((v) => ({ ...v, key: v.name, view_type: (v.view_type || 'List').toLowerCase() })),
  )
  const allViews = computed(() => [...builtins.value, ...savedViews.value])

  function applyViewConfig(v) {
    view.view_type = (v.view_type || 'board').toLowerCase()
    view.group_by = v.group_by || bucketField.value
    view.sort_field = v.sort_field || ''
    view.sort_dir = v.sort_dir || 'asc'
    view.me_mode = !!v.me_mode
    view.filters = JSON.parse(JSON.stringify(v.filters || []))
  }

  function selectView(key) {
    activeKey.value = key
    const v = allViews.value.find((x) => x.key === key)
    if (!v) return
    if (v._builtin) applyViewConfig(builtinView(v.view_type))
    else applyViewConfig(v)
  }

  function patchView(patch) {
    Object.assign(view, patch)
  }

  // dirty = active saved view differs from current state
  const dirty = computed(() => {
    const v = savedViews.value.find((x) => x.key === activeKey.value)
    if (!v) return false
    return JSON.stringify(snapshot()) !== JSON.stringify(snapshotOf(v))
  })
  function snapshot() {
    return {
      view_type: view.view_type,
      group_by: view.group_by,
      sort_field: view.sort_field || '',
      sort_dir: view.sort_dir,
      me_mode: !!view.me_mode,
      filters: view.filters || [],
    }
  }
  function snapshotOf(v) {
    return {
      view_type: (v.view_type || 'board').toLowerCase(),
      group_by: v.group_by || bucketField.value,
      sort_field: v.sort_field || '',
      sort_dir: v.sort_dir || 'asc',
      me_mode: !!v.me_mode,
      filters: v.filters || [],
    }
  }

  // ---- persist across reloads (per space) ---------------------------------
  let restoring = false
  function setRestoring(v) {
    restoring = v
  }
  function stateKey() {
    return `sprint.view.${space()}`
  }
  function persistViewState() {
    if (restoring || !space()) return
    try {
      sessionStorage.setItem(
        stateKey(),
        JSON.stringify({
          activeKey: activeKey.value,
          view: snapshot(),
          search: search.value,
          subtaskMode: subtaskMode.value,
        }),
      )
    } catch { /* storage unavailable */ }
  }
  function restoreViewState() {
    let raw = null
    try {
      raw = sessionStorage.getItem(stateKey())
    } catch { /* ignore */ }
    if (!raw) return false
    try {
      const s = JSON.parse(raw)
      if (s.view) applyViewConfig(s.view)
      activeKey.value = s.activeKey || 'board'
      search.value = typeof s.search === 'string' ? s.search : ''
      subtaskMode.value = s.subtaskMode || 'separate'
      return true
    } catch {
      return false
    }
  }
  watch([activeKey, search, subtaskMode], persistViewState)
  watch(view, persistViewState, { deep: true })

  return {
    view,
    activeKey,
    savedViews,
    allViews,
    selectView,
    patchView,
    dirty,
    restoreViewState,
    setRestoring,
  }
}
