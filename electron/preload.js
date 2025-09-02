import { contextBridge, ipcRenderer } from 'electron'
const DEBUG = String(process.env.DEBUG || '').toLowerCase() === '1' || String(process.env.DEBUG || '').toLowerCase() === 'true'
function dlog(...args) { if (DEBUG) console.log('[preload]', ...args) }

let _basePromise = null
async function getBase() {
  if (!_basePromise) _basePromise = ipcRenderer.invoke('backend-base')
  try {
    const res = await _basePromise
    if (res && res.ok && res.base) return res.base
  } catch {}
  // fallback
  const host = process.env.APP_HOST || '127.0.0.1'
  const port = parseInt(process.env.APP_PORT || '8001', 10)
  return `http://${host}:${port}`
}

async function http(path, opts = {}) {
  dlog('http', opts.method || 'GET', path)
  try {
    const base = await getBase()
    const res = await fetch(base + path, opts)
    const ct = res.headers.get('content-type') || ''
    let body
    if (ct.includes('application/json')) body = await res.json()
    else body = await res.text()
    if (!res.ok) {
      const msg = (body && body.detail) || (typeof body === 'string' ? body : JSON.stringify(body)) || `HTTP ${res.status}`
      dlog('http-error', res.status, path, msg)
      return { ok: false, status: res.status, error: msg }
    }
    dlog('http-ok', path)
    return { ok: true, data: body }
  } catch (e) {
    dlog('http-ex', path, e && e.message)
    return { ok: false, error: (e && e.message) || 'Network error' }
  }
}

const api = {
  notes: {
    list: () => http('/notes/list'),
    get: (id) => http(`/notes/get?id=${encodeURIComponent(id)}`),
    create: (title, content) => http('/notes/create', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ title, content })
    }),
    update: (id, { title, content, reindex = true } = {}) => http('/notes/update', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ id, title, content, reindex })
    }),
    delete: (id) => http(`/notes/delete?id=${encodeURIComponent(id)}`, { method: 'POST' }),
    open: async (noteId) => ipcRenderer.invoke('notes-open', noteId),
    focus: async (noteId) => ipcRenderer.invoke('notes-focus', noteId),
  },
  groups: {
    list: () => http('/groups/list'),
    create: (name) => http('/groups/create', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ name }) }),
    rename: (id, name) => http('/groups/rename', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ id, name }) }),
    delete: (id) => http(`/groups/delete?id=${encodeURIComponent(id)}`, { method: 'POST' }),
    notes: (groupId) => http(`/groups/notes?group_id=${encodeURIComponent(groupId)}`),
    addNote: (groupId, noteId) => http(`/groups/add_note?group_id=${encodeURIComponent(groupId)}&note_id=${encodeURIComponent(noteId)}`, { method: 'POST' }),
    removeNote: (groupId, noteId) => http(`/groups/remove_note?group_id=${encodeURIComponent(groupId)}&note_id=${encodeURIComponent(noteId)}`, { method: 'POST' }),
    reorder: (orderedIds) => http('/groups/reorder', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ ordered_ids: orderedIds }) }),
    reorderNotes: (groupId, orderedNoteIds) => http('/groups/reorder_notes', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ group_id: groupId, ordered_note_ids: orderedNoteIds }) }),
  },
  tabs: {
    merge: async (_tabIds) => ({ ok: true }), // stub
    unstack: async (_stackId) => ({ ok: true }), // stub
    reorder: async (_sessionId, _tabId, _toPos) => ({ ok: true }), // stub
    saveSession: (sessionId, tabs) => http('/tabs/save_session', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ session_id: sessionId, tabs }) }),
    loadSession: (sessionId) => http(`/tabs/load_session?session_id=${encodeURIComponent(sessionId)}`),
    registerOpen: (noteId, tabId) => { ipcRenderer.send('tabs-register-open', { noteId, tabId }) },
    registerClose: (noteId, tabId) => { ipcRenderer.send('tabs-register-close', { noteId, tabId }) },
  },
  search: {
    keywordAll: (q) => http(`/notes/search?q=${encodeURIComponent(q)}`),
    keywordGroup: async (q, groupId) => {
      const g = await http(`/groups/notes?group_id=${encodeURIComponent(groupId)}`)
      if (!g.ok) return g
      const ids = (g.data.note_ids || []).join(',')
      return http(`/notes/search?q=${encodeURIComponent(q)}&note_ids=${encodeURIComponent(ids)}`)
    },
    keywordNote: (q, noteId) => http(`/notes/search?q=${encodeURIComponent(q)}&note_ids=${encodeURIComponent(noteId)}`),
  },
  llm: {
    ask: (arg) => {
      const payload = typeof arg === 'string' ? { prompt: arg } : {
        prompt: arg.prompt,
        note_ids: (arg.noteIds || []).join(','),
        group_ids: (arg.groupIds || []).join(','),
        date_start: arg.dateStart || null,
        date_end: arg.dateEnd || null,
        k: arg.k || 6,
      }
      return http('/chat', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) })
    },
    search: ({ q, k = 5, noteIds = [], groupIds = [], dateStart = null, dateEnd = null }) => {
      const params = new URLSearchParams()
      params.set('q', q)
      params.set('k', String(k))
      if (noteIds.length) params.set('note_ids', noteIds.join(','))
      if (groupIds.length) params.set('group_ids', groupIds.join(','))
      if (dateStart) params.set('date_start', String(dateStart))
      if (dateEnd) params.set('date_end', String(dateEnd))
      return http('/search?' + params.toString())
    }
  },
  settings: {
    get: () => http('/settings/get'),
    update: (partial) => http('/settings/update', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(partial) })
  },
  events: {
    onFocusNote: (cb) => {
      const listener = (_evt, noteId) => cb(noteId)
      ipcRenderer.on('focus-note', listener)
      return () => ipcRenderer.removeListener('focus-note', listener)
    }
  },
  debug: {
    logsPath: () => ipcRenderer.invoke('logs-path')
  }
}

contextBridge.exposeInMainWorld('api', api)
