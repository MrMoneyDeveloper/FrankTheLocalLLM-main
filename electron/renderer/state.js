export const state = {
  notes: [],
  groups: [],
  counts: {}, // groupId -> count
  openTabs: [], // [{id, title, stackId}]
  activeId: null,
  selectedTabIds: new Set(),
  snapshots: {}, // id -> [{ts, value}]
}

export function setActive(id) {
  state.activeId = id
}

export function getActive() {
  return state.openTabs.find(t => t.id === state.activeId) || null
}

export function findTab(id) { return state.openTabs.find(t => t.id === id) }

export function persistTabs() {
  const tabs = state.openTabs.map((t, i) => ({ note_id: t.id, stack_id: t.stackId || null, position: i }))
  try { window.api.tabs.saveSession('main', tabs) } catch {}
}

export function loadSnapshots(id) {
  try {
    const raw = localStorage.getItem('snapshots:' + id)
    if (!raw) return []
    return JSON.parse(raw) || []
  } catch { return [] }
}

export function pushSnapshot(id, value) {
  const arr = loadSnapshots(id)
  const ts = Date.now()
  arr.push({ ts, value })
  // keep last 100
  while (arr.length > 100) arr.shift()
  try { localStorage.setItem('snapshots:' + id, JSON.stringify(arr)) } catch {}
}

