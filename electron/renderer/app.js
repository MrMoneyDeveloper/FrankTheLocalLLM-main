const state = {
  notes: [],
  groups: [],
  openTabs: [], // [{id, title}]
  activeId: null,
  snapshots: {}, // id -> [contents]
  searchMarks: [],
  searchIndex: -1,
}

const $ = (sel) => document.querySelector(sel)
const el = (tag, attrs = {}, ...children) => {
  const n = document.createElement(tag)
  Object.assign(n, attrs)
  children.forEach((c) => n.append(c))
  return n
}

function msFromDateInput(s) {
  if (!s) return null
  const d = new Date(s)
  if (isNaN(d.getTime())) return null
  return d.getTime()
}

function setStatus(msg, isError = false) {
  const el = document.getElementById('statusbar')
  if (!el) return
  el.textContent = msg
  el.style.color = isError ? '#b00020' : '#666'
}

async function refresh() {
  const [notes, groups, settings] = await Promise.all([
    window.api.notes.list(),
    window.api.groups.list(),
    window.api.settings.get(),
  ])
  if (!notes.ok) { setStatus('Failed to load notes: ' + (notes.error || notes.status), true); state.notes = [] } else { state.notes = notes.data.notes || [] }
  if (!groups.ok) { setStatus('Failed to load groups: ' + (groups.error || groups.status), true); state.groups = [] } else { state.groups = groups.data.groups || [] }
  renderNotesList()
  renderGroups()
  if (!settings.ok) { setStatus('Failed to load settings: ' + (settings.error || settings.status), true) } else { renderSettings(settings.data) }
}

function renderNotesList() {
  const wrap = $('#notesList')
  wrap.innerHTML = ''
  state.notes.forEach((n) => {
    const item = el('div', { className: 'item', draggable: true })
    item.textContent = n.title
    item.addEventListener('click', () => openNote(n.id))
    item.addEventListener('dragstart', (e) => {
      e.dataTransfer.setData('text/plain', `note:${n.id}`)
    })
    wrap.append(item)
  })
}

function renderGroups() {
  const wrap = $('#groups')
  wrap.innerHTML = ''
  state.groups.forEach((g) => {
    const item = el('div', { className: 'group', draggable: false })
    item.textContent = g.name
    // Accept drops to add note
    item.addEventListener('dragover', (e) => e.preventDefault())
    item.addEventListener('drop', async (e) => {
      e.preventDefault()
      const data = e.dataTransfer.getData('text/plain')
      if (data.startsWith('note:')) {
        const id = data.split(':')[1]
        await window.api.groups.addNote(g.id, id)
        await refresh()
      }
    })
    wrap.append(item)
  })
  // fill moveToGroup select
  const sel = $('#moveToGroup')
  sel.innerHTML = ''
  state.groups.forEach((g) => {
    const o = el('option')
    o.value = g.id
    o.textContent = g.name
    sel.append(o)
  })
}

function renderSettings(settings) {
  const wrap = $('#settings')
  wrap.innerHTML = ''
  const rows = [
    ['CHAT_MODEL', settings.CHAT_MODEL],
    ['EMBED_MODEL', settings.EMBED_MODEL],
    ['CHUNK_SIZE', settings.CHUNK_SIZE],
    ['CHUNK_OVERLAP', settings.CHUNK_OVERLAP],
    ['REINDEX_DEBOUNCE_MS', settings.REINDEX_DEBOUNCE_MS],
    ['SEARCH_THROTTLE_MS', settings.SEARCH_THROTTLE_MS],
    ['MAX_CHUNKS_PER_QUERY', settings.MAX_CHUNKS_PER_QUERY],
  ]
  rows.forEach(([k, v]) => {
    const row = el('div', { className: 'row' }, el('label', { textContent: k, style: 'width: 180px' }))
    const inp = el('input', { value: v })
    inp.addEventListener('change', async () => {
      const val = isNaN(Number(inp.value)) ? inp.value : Number(inp.value)
      await window.api.settings.update({ [k]: val })
    })
    row.append(inp)
    wrap.append(row)
  })
}

async function openNote(id) {
  // Ask main to focus existing tab if open anywhere
  try {
    const res = await window.api.notes.open(id)
    if (res && res.focused) { return }
  } catch {}
  // Maintain single-open within this window
  const exists = state.openTabs.find((t) => t.id === id)
  if (exists) {
    state.activeId = id
    renderTabs()
    return
  }
  const note = await window.api.notes.get(id)
  if (!note.ok) { setStatus('Open failed: ' + (note.error || note.status), true); return }
  const rec = note.data
  state.openTabs.push({ id, title: rec.title })
  state.activeId = id
  renderTabs()
  renderEditor(rec)
  // register with main
  window.api.tabs.registerOpen(id, id)
}

function closeTab(id) {
  const idx = state.openTabs.findIndex((t) => t.id === id)
  if (idx >= 0) state.openTabs.splice(idx, 1)
  if (state.activeId === id) state.activeId = state.openTabs[0]?.id || null
  renderTabs()
  if (state.activeId) window.api.notes.get(state.activeId).then((r)=>{ if(r.ok) renderEditor(r.data) })
  else $('#editor').innerHTML = ''
  // unregister
  try { window.api.tabs.registerClose(id, id) } catch {}
}

function renderTabs() {
  const bar = $('#tabbar')
  bar.innerHTML = ''
  state.openTabs.forEach((t) => {
    const btn = el('div', { className: 'tab' + (t.id === state.activeId ? ' active' : '') })
    btn.textContent = t.title
    btn.addEventListener('click', () => { state.activeId = t.id; renderTabs(); window.api.notes.get(t.id).then(renderEditor) })
    btn.addEventListener('auxclick', (e) => { if (e.button === 1) closeTab(t.id) })
    bar.append(btn)
  })
}

function renderEditor(note) {
  const wrap = $('#editor')
  wrap.innerHTML = ''
  const area = el('textarea', { className: 'note' })
  // crash recovery: check local snapshots
  try {
    const raw = localStorage.getItem('snapshots:' + note.id)
    if (raw) {
      const snaps = JSON.parse(raw)
      const latest = snaps[snaps.length - 1]
      if (latest && latest !== note.content && confirm('Unsaved snapshot found. Restore?')) {
        note.content = latest
      }
    }
  } catch {}
  area.value = note.content || ''
  wrap.append(area)
  let saveTimer = null
  const debounce = 500
  area.addEventListener('input', () => {
    clearTimeout(saveTimer)
    saveTimer = setTimeout(async () => {
      // snapshot
      state.snapshots[note.id] = state.snapshots[note.id] || []
      state.snapshots[note.id].push(area.value)
      try { localStorage.setItem('snapshots:' + note.id, JSON.stringify(state.snapshots[note.id])) } catch {}
      // autosave
      const res = await window.api.notes.update(note.id, { content: area.value })
      if (!res.ok) { setStatus('Autosave failed: ' + (res.error || res.status), true); return }
      // update tab title if changed derivation
      const data = res.data
      const tab = state.openTabs.find((t) => t.id === note.id)
      if (tab && tab.title !== data.title) { tab.title = data.title; renderTabs() }
      const st = document.getElementById('indexStatus'); if (st) { st.textContent = 'Indexed at ' + new Date().toLocaleTimeString() }
    }, debounce)
  })
  // in-note search controls
  $('#noteSearchPrev').onclick = () => findInNote(area, $('#noteSearchQuery').value, -1)
  $('#noteSearchNext').onclick = () => findInNote(area, $('#noteSearchQuery').value, +1)
  // minihub actions
  $('#moveToGroupBtn').onclick = async () => {
    const gid = $('#moveToGroup').value
    if (gid) { await window.api.groups.addNote(gid, note.id); await refresh() }
  }
  $('#duplicateNoteBtn').onclick = async () => {
    await window.api.notes.create(note.title + ' (copy)', area.value)
    await refresh()
  }
  $('#openWindowBtn').onclick = () => window.open('', '_blank').document.write(`<pre>${area.value.replace(/</g,'&lt;')}</pre>`)
  // LLM search
  $('#runLlm').onclick = async () => {
    const scope = $('#llmScope').value
    const ds = msFromDateInput($('#dateStart').value)
    const de = msFromDateInput($('#dateEnd').value)
    let noteIds = []
    let groupIds = []
    if (scope === 'note') noteIds = [note.id]
    if (scope === 'groups') groupIds = Array.from($('#moveToGroup').options).map(o => o.value)
    const res = await window.api.llm.ask($('#llmQuery').value)
    if (!res.ok) { setStatus('LLM error: ' + (res.error || res.status), true); return }
    const ans = (res.data && res.data.answer) || ''
    renderLlmResults([{ answer: ans }])
  }

  // Subscribe to main focus events
  try {
    window.api.events.onFocusNote((noteId) => {
      const exists = state.openTabs.find((t) => t.id === noteId)
      if (exists) {
        state.activeId = noteId
        renderTabs()
        window.api.notes.get(noteId).then((r)=>{ if(r.ok) renderEditor(r.data) })
      }
    })
  } catch {}
}

function renderLlmResults(items) {
  const wrap = $('#llmResults')
  wrap.innerHTML = ''
  items.forEach((r) => {
    const div = el('div', { className: 'item' })
    const title = (r.meta && r.meta.title) ? r.meta.title : ''
    div.innerHTML = `<div style="font-weight:600">${title}</div><div>${r.text}</div><div style="color:#999">d=${(r.distance||0).toFixed(3)}</div>`
    wrap.append(div)
  })
}

function findInNote(area, q, dir) {
  const val = area.value
  const start = area.selectionStart
  if (!q) return
  let idx = -1
  if (dir > 0) idx = val.toLowerCase().indexOf(q.toLowerCase(), start + 1)
  else idx = val.toLowerCase().lastIndexOf(q.toLowerCase(), start - 1)
  if (idx >= 0) {
    area.focus()
    area.selectionStart = idx
    area.selectionEnd = idx + q.length
  }
}

// create note / group handlers
$('#createNoteBtn').onclick = async () => {
  const r = await window.api.notes.create('Untitled', '')
  await refresh(); await openNote(r.id)
}
$('#createGroupBtn').onclick = async () => {
  const name = $('#newGroupName').value.trim()
  if (!name) return
  await window.api.groups.create(name)
  $('#newGroupName').value = ''
  await refresh()
}

refresh()
