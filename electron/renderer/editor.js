import { state, pushSnapshot } from './state.js'
import { $, el } from './utils.js'

let saveTimer = null
let editCount = 0
const SNAPSHOT_EVERY = 50

export function renderEditor(note) {
  const wrap = $('#editor')
  wrap.innerHTML = ''
  const title = el('input', { id: 'titleInput', className: 'form-control', value: note.title || '' })
  title.style.marginBottom = '8px'
  const area = el('textarea', { className: 'note form-control' })
  area.style.minHeight = 'calc(100% - 40px)'
  // recovery check
  try {
    const raw = localStorage.getItem('snapshots:' + note.id)
    if (raw) {
      const snaps = JSON.parse(raw) || []
      const latest = snaps[snaps.length - 1]
      if (latest && latest.value !== note.content && latest.ts > (note.updated_at || 0)) {
        if (confirm('Unsaved snapshot found. Restore?')) {
          note.content = latest.value
        }
      }
    }
  } catch {}
  area.value = note.content || ''
  wrap.append(title, area)

  // title debounce
  let titleTimer = null
  title.addEventListener('input', ()=>{
    clearTimeout(titleTimer)
    titleTimer = setTimeout(async ()=> { await doSave(note.id, { title: title.value, content: null }); try { window.keywordIndexUpdateFromSave(note.id, title.value, null, Date.now()) } catch {} }, 400)
  })

  area.addEventListener('input', () => {
    clearTimeout(saveTimer)
    editCount += 1
    if (editCount % SNAPSHOT_EVERY === 0) pushSnapshot(note.id, area.value)
    saveTimer = setTimeout(async () => {
      pushSnapshot(note.id, area.value)
      const res = await window.api.notes.update(note.id, { content: area.value })
      if (!res.ok) { window.setStatus('Autosave failed: ' + (res.error || res.status), true); return }
      window.updateTabTitle(note.id, res.data.title)
      try { window.keywordIndexUpdateFromSave(note.id, null, area.value, Date.now()) } catch {}
      const st = document.getElementById('indexStatus'); if (st) { st.textContent = 'Reindex scheduled…' }
    }, 500)
  })

  // Ctrl/Cmd+S
  window.addEventListener('keydown', (e)=>{
    if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 's') {
      e.preventDefault()
      doSave(note.id, { title: title.value, content: area.value })
    }
  })

  // minihub buttons wire-up
  const run = document.getElementById('runLlm')
  if (run) run.onclick = async ()=> {
    const scope = document.getElementById('llmScope').value
    const ds = document.getElementById('dateStart').value
    const de = document.getElementById('dateEnd').value
    let noteIds = []
    let groupIds = []
    if (scope === 'note') noteIds = [note.id]
    if (scope === 'groups') groupIds = Array.from(document.getElementById('moveToGroup').options).map(o => o.value)
    const res = await window.api.llm.ask({ prompt: document.getElementById('llmQuery').value, noteIds, groupIds, dateStart: ds ? new Date(ds).getTime() : null, dateEnd: de ? new Date(de).getTime() : null, k: 8 })
    if (!res.ok) { window.setStatus('LLM search error: ' + (res.error || res.status), true); return }
    const data = res.data
    const div = document.getElementById('llmResults')
    div.innerHTML = ''
    const ans = document.createElement('div')
    ans.textContent = data.answer || ''
    div.append(ans)
    if (Array.isArray(data.citations)) {
      const ul = document.createElement('ul')
      for (const c of data.citations) {
        const li = document.createElement('li')
        li.textContent = `${c.title || c.note_id} (note ${c.note_id})`
        ul.append(li)
      }
      div.append(ul)
    }
  }

  const reindexNow = document.getElementById('reindexNow')
  if (reindexNow) reindexNow.onclick = async ()=>{
    const res = await window.api.notes.update(note.id, { title: null, content: null, reindex: true, reindex_now: true })
    if (!res.ok) { window.setStatus('Reindex failed: ' + (res.error || res.status), true); return }
    const st = document.getElementById('indexStatus'); if (st) { st.textContent = 'Reindexed at ' + new Date().toLocaleTimeString() }
  }

  // in-note search
  const q = document.getElementById('noteSearchQuery')
  const prev = document.getElementById('noteSearchPrev')
  const next = document.getElementById('noteSearchNext')
  let lastIdx = -1
  function find(dir) {
    const hay = area.value
    const needle = (q.value || '').toLowerCase()
    if (!needle) return
    let start = area.selectionStart
    if (dir < 0) start = Math.max(0, start - 1)
    const idx = dir > 0 ? hay.toLowerCase().indexOf(needle, start) : hay.toLowerCase().lastIndexOf(needle, start)
    if (idx >= 0) {
      area.focus()
      area.setSelectionRange(idx, idx + needle.length)
      lastIdx = idx
    }
  }
  if (prev) prev.onclick = ()=> find(-1)
  if (next) next.onclick = ()=> find(+1)
}

async function doSave(id, payload) {
  const res = await window.api.notes.update(id, payload)
  if (!res.ok) { window.setStatus('Save failed: ' + (res.error || res.status), true); return }
  window.updateTabTitle(id, res.data.title)
}
