import { state, pushSnapshot } from './state.js'
import { $, el } from './utils.js'

let saveTimer = null
let editCount = 0
const SNAPSHOT_EVERY = 50

export function renderEditor(note) {
  const wrap = $('#editor')
  const body = $('#editorBody') || wrap
  wrap && (wrap.scrollTop = 0)
  if (body) body.innerHTML = ''
  const title = $('#titleInput') || el('input', { id: 'titleInput' })
  title.value = note.title || ''
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
  body.append(area)

  // title debounce
  let titleTimer = null
  title.oninput = ()=>{
    clearTimeout(titleTimer)
    titleTimer = setTimeout(async ()=> { await doSave(note.id, { title: title.value, content: null }); try { window.keywordIndexUpdateFromSave(note.id, title.value, null, Date.now()) } catch {} }, 400)
  }

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
  // Ask bar
  const askInput = document.getElementById('askInput')
  const askMode = document.getElementById('askMode')
  const askWrap = document.getElementById('askBarWrap')
  const askRun = document.getElementById('askRun')
  const askScope = document.getElementById('askScope')
  const askDateStart = document.getElementById('askDateStart')
  const askDateEnd = document.getElementById('askDateEnd')
  if (askWrap && askInput) {
    askInput.onfocus = ()=> askWrap.classList.add('askbar-expanded')
    askInput.onblur = ()=> { if (!askInput.value) askWrap.classList.remove('askbar-expanded') }
    async function runAsk() {
      const statusEl = document.getElementById('askStatus')
      if (statusEl) statusEl.textContent = 'Thinking…'
      if (askRun) askRun.disabled = true
      const scope = askScope ? askScope.value : 'all'
      const ds = askDateStart && askDateStart.value ? new Date(askDateStart.value).getTime() : null
      const de = askDateEnd && askDateEnd.value ? new Date(askDateEnd.value).getTime() : null
      let noteIds = []
      let groupIds = []
      if (scope === 'note') noteIds = [note.id]
      if (scope === 'groups') groupIds = Array.from(document.getElementById('moveToGroup').options).map(o => o.value)
      const div = document.getElementById('llmResults')
      if (div) div.innerHTML = ''
      if (askMode && askMode.value === 'keyword') {
        let ids = []
        if (scope === 'note') ids = [note.id]
        if (scope === 'groups') {
          try {
            const opts = Array.from(document.getElementById('moveToGroup').options).map(o => o.value)
            ids = opts
          } catch {}
        }
        const res = await window.api.notes.search(askInput.value, ids)
        if (!res.ok) { window.setStatus('Search error: ' + (res.error || res.status), true); if (statusEl) statusEl.textContent=''; if (askRun) askRun.disabled=false; return }
        const div = document.getElementById('llmResults')
        if (div) {
          div.innerHTML = ''
          const results = res.data.results || []
          for (const r of results) {
            const item = document.createElement('div')
            item.innerHTML = `<div class="title">${r.title||r.noteId}</div><div class="snippet">${(r.snippet||'').toString()}</div>`
            div.append(item)
          }
        }
      } else {
        const res = await window.api.llm.ask({ prompt: askInput.value, noteIds, groupIds, dateStart: ds, dateEnd: de, k: 8 })
        if (!res.ok) { window.setStatus('LLM error: ' + (res.error || res.status), true); if (statusEl) statusEl.textContent=''; if (askRun) askRun.disabled=false; return }
        const data = res.data
        const div = document.getElementById('llmResults')
        if (div) {
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
      }
      if (statusEl) statusEl.textContent = ''
      if (askRun) askRun.disabled = false
    }
    askInput.addEventListener('keydown', (e)=>{ if (e.key === 'Enter') { e.preventDefault(); runAsk() } })
    if (askRun) askRun.onclick = runAsk
  }

  // Quick actions dropdown
  const qaBtn = document.getElementById('quickActions')
  const menu = document.getElementById('quickMenu')
  if (qaBtn && menu) {
    qaBtn.onclick = (e)=>{ e.stopPropagation(); menu.style.display = menu.style.display === 'none' || !menu.style.display ? 'block' : 'none' }
    document.addEventListener('click', ()=>{ if (menu.style.display === 'block') menu.style.display = 'none' })
    const moveBtn = document.getElementById('qaMove')
    const dupBtn = document.getElementById('qaDuplicate')
    const openBtn = document.getElementById('qaOpenWindow')
    const reindexBtn = document.getElementById('qaReindex')
    const toggleAdv = document.getElementById('qaToggleAdvanced')
    if (moveBtn) moveBtn.onclick = async ()=>{ const gid = document.getElementById('moveToGroup').value; if (gid) { await window.api.groups.addNote(gid, note.id); await window.refresh() } }
    if (dupBtn) dupBtn.onclick = async ()=>{ await window.api.notes.create((title.value||'Untitled') + ' (copy)', area.value); await window.refresh() }
    if (openBtn) openBtn.onclick = ()=>{ const w = window.open('', '_blank'); if (w && w.document) w.document.write(`<pre style="white-space:pre-wrap">${(area.value||'').replace(/</g,'&lt;')}</pre>`) }
    if (reindexBtn) reindexBtn.onclick = async ()=>{ const res = await window.api.notes.update(note.id, { title: null, content: null, reindex: true, reindex_now: true }); if (!res.ok) { window.setStatus('Reindex failed: ' + (res.error || res.status), true) } }
    if (toggleAdv) toggleAdv.onclick = ()=>{ const m = document.getElementById('minihub'); if (m) m.style.display = (m.style.display==='none'?'block':'none') }
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
