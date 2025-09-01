import { contextBridge } from 'electron'

const host = process.env.APP_HOST || '127.0.0.1'
const port = parseInt(process.env.APP_PORT || '8001', 10)
const base = `http://${host}:${port}`

async function http(path, opts = {}) {
  const res = await fetch(base + path, opts)
  if (!res.ok) throw new Error(`HTTP ${res.status}`)
  const ct = res.headers.get('content-type') || ''
  if (ct.includes('application/json')) return res.json()
  return res.text()
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
    search: (q, noteIds) => http(`/notes/search?q=${encodeURIComponent(q)}&note_ids=${encodeURIComponent((noteIds||[]).join(','))}`)
  },
  groups: {
    list: () => http('/groups/list'),
    create: (name) => http('/groups/create', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ name }) }),
    delete: (id) => http(`/groups/delete?id=${encodeURIComponent(id)}`, { method: 'POST' }),
    addNote: (groupId, noteId) => http(`/groups/add_note?group_id=${encodeURIComponent(groupId)}&note_id=${encodeURIComponent(noteId)}`, { method: 'POST' }),
    removeNote: (groupId, noteId) => http(`/groups/remove_note?group_id=${encodeURIComponent(groupId)}&note_id=${encodeURIComponent(noteId)}`, { method: 'POST' })
  },
  llm: {
    chat: (prompt) => http('/chat', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ prompt }) }),
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
  }
}

contextBridge.exposeInMainWorld('api', api)

