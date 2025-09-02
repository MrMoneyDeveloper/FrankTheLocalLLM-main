import { state } from './state.js'
import { $, el } from './utils.js'
import { renderTabs, registerOpen, mergeSelectedIntoStack, unstackTab } from './tabs.js'
import { renderGroups } from './groups.js'
import { renderEditor } from './editor.js'
import { initMinihub } from './minihub.js'
import { initSettings } from './settings.js'
import { initSearchUI, buildKeywordIndex, keywordIndexUpdateFromSave } from './search_ui.js'

window.renderEditor = renderEditor
window.renderTabs = renderTabs
window.setStatus = setStatus
window.closeTab = closeTab
window.updateTabTitle = updateTabTitle
window.refresh = refresh
window.renderLlmResults = (items)=>{
  const el = document.getElementById('llmResults')
  el.innerHTML = ''
  for (const it of items) {
    const d = document.createElement('div')
    d.textContent = it.answer || JSON.stringify(it)
    el.append(d)
  }
}

function setStatus(msg, isError=false) {
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
  state.notes = notes.ok ? (notes.data.notes || []) : []
  state.groups = groups.ok ? (groups.data.groups || []) : []
  if (settings.ok && settings.data) {
    document.body.classList.toggle('simple-mode', !!settings.data.SIMPLE_MODE)
  }
  renderGroups()
  renderNotesList()
  // Fill moveToGroup select
  const sel = document.getElementById('moveToGroup')
  if (sel) {
    sel.innerHTML = ''
    state.groups.forEach((g)=>{ const o = document.createElement('option'); o.value=g.id; o.textContent=g.name; sel.append(o) })
  }
}

function updateTabTitle(id, title) {
  const t = state.openTabs.find(t=>t.id===id)
  if (t) { t.title = title; renderTabs() }
}

function closeTab(id) {
  const idx = state.openTabs.findIndex(t=>t.id===id)
  if (idx>=0) state.openTabs.splice(idx,1)
  if (state.activeId === id) state.activeId = state.openTabs[0]?.id || null
  renderTabs()
  if (state.activeId) window.api.notes.get(state.activeId).then((r)=>{ if(r.ok) renderEditor(r.data) })
  else {
    const eb = document.getElementById('editorBody')
    if (eb) eb.innerHTML = '' // keep Ask bar visible
  }
  try { window.api.tabs.registerClose(id, id) } catch {}
}

function renderNotesList() {
  const wrap = document.getElementById('notesList')
  if (!wrap) return
  wrap.innerHTML = ''
  for (const n of state.notes) {
    const item = document.createElement('div')
    item.className = 'item'
    item.textContent = n.title
    item.draggable = true
    item.addEventListener('click', ()=> window.openNote(n.id))
    item.addEventListener('dragstart', (e)=>{ e.dataTransfer.setData('text/plain', `note:${n.id}`) })
    wrap.append(item)
  }
}

function attachGlobalShortcuts() {
  document.addEventListener('contextmenu', (e)=>{
    const target = e.target.closest('.tab')
    if (!target) return
    e.preventDefault()
    const id = target.dataset.id
    const menu = document.createElement('div')
    menu.style.position='fixed'; menu.style.background='#fff'; menu.style.border='1px solid #ddd'; menu.style.padding='6px'
    const m1 = document.createElement('div'); m1.textContent = 'Merge tabs'; m1.style.cursor='pointer'
    m1.onclick = ()=>{ mergeSelectedIntoStack(); document.body.removeChild(menu) }
    const m2 = document.createElement('div'); m2.textContent = 'Unstack'; m2.style.cursor='pointer'
    m2.onclick = ()=>{ if(id) unstackTab(id); document.body.removeChild(menu) }
    menu.append(m1, m2)
    document.body.append(menu)
    menu.style.left = e.clientX+'px'; menu.style.top = e.clientY+'px'
    setTimeout(()=>document.addEventListener('click', ()=>{ if(document.body.contains(menu)) document.body.removeChild(menu) }, { once:true }),0)
  })
}

async function start() {
  initMinihub()
  initSettings()
  initSearchUI()
  attachGlobalShortcuts()
  await refresh()
  await buildKeywordIndex()
  // If any note id via hash
  renderTabs()
  try {
    window.api.events.onFocusNote((noteId) => {
      const exists = state.openTabs.find(t=>t.id===noteId)
      if (exists) {
        state.activeId = noteId
        renderTabs()
        window.api.notes.get(noteId).then((r)=>{ if(r.ok) renderEditor(r.data) })
      }
    })
  } catch {}
  const createBtn = document.getElementById('createNoteBtn')
  if (createBtn) createBtn.onclick = async ()=>{
    const r = await window.api.notes.create('Untitled', '')
    if (!r.ok) { setStatus('Create failed: ' + (r.error || r.status), true); return }
    await refresh()
    window.openNote(r.data.id)
  }
  const createGroupBtn = document.getElementById('createGroupBtn')
  const newGroupName = document.getElementById('newGroupName')
  if (createGroupBtn && newGroupName) createGroupBtn.onclick = async ()=>{
    const name = (newGroupName.value || '').trim()
    if (!name) return
    const r = await window.api.groups.create(name)
    if (!r.ok) { setStatus('Create group failed: ' + (r.error || r.status), true); return }
    newGroupName.value = ''
    await refresh()
  }
  const osb = document.getElementById('openSearchBtn')
  if (osb) osb.onclick = ()=>{
    const el = document.getElementById('searchModal')
    const m = new bootstrap.Modal(el)
    m.show()
    setTimeout(()=>{ const inp = document.getElementById('globalSearchInput'); if (inp) inp.focus() }, 100)
  }
  // Projects (groups) collapse toggle
  const ph = document.getElementById('projectsHeader')
  if (ph) {
    const WRAP_ID = 'groups'
    const key = 'ui:projects:collapsed'
    const apply = ()=>{
      const w = document.getElementById(WRAP_ID)
      const v = localStorage.getItem(key) === '1'
      if (w) w.style.display = v ? 'none' : 'block'
    }
    ph.onclick = ()=>{
      const v = localStorage.getItem(key) === '1'
      localStorage.setItem(key, v ? '0' : '1')
      apply()
    }
    apply()
  }

  // Resizable splitters
  initSplitters()
}

function initSplitters() {
  const left = document.getElementById('splitLeft')
  const right = document.getElementById('splitRight')
  const sidebar = document.getElementById('sidebar')
  const minihub = document.getElementById('minihub')
  // restore
  try { const w = parseInt(localStorage.getItem('ui:sidebar:w')||'0',10); if (w) sidebar.style.width = w+'px' } catch{}
  try { const w = parseInt(localStorage.getItem('ui:minihub:w')||'0',10); if (w) minihub.style.width = w+'px' } catch{}
  function drag(el, onMove, onEnd) {
    if (!el) return
    el.addEventListener('mousedown', (e)=>{
      e.preventDefault()
      const move = (ev)=> onMove(ev)
      const up = ()=>{ document.removeEventListener('mousemove', move); document.removeEventListener('mouseup', up); if (onEnd) onEnd() }
      document.addEventListener('mousemove', move)
      document.addEventListener('mouseup', up)
    })
  }
  drag(left, (e)=>{ const x = e.clientX; const min = 180; const max = Math.min(window.innerWidth*0.5, 500); const w = Math.max(min, Math.min(max, x)); sidebar.style.width = w+'px' }, ()=>{ localStorage.setItem('ui:sidebar:w', parseInt(sidebar.style.width,10)) })
  drag(right, (e)=>{ const x = e.clientX; const fromRight = window.innerWidth - x; const min = 220; const max = Math.min(window.innerWidth*0.5, 560); const w = Math.max(min, Math.min(max, fromRight)); minihub.style.width = w+'px' }, ()=>{ localStorage.setItem('ui:minihub:w', parseInt(minihub.style.width,10)) })
}

start()

// Expose openNote for click handlers
window.openNote = async (id) => {
  try {
    const res = await window.api.notes.open(id)
    if (res && res.focused) return
  } catch {}
  const note = await window.api.notes.get(id)
  if (!note.ok) { setStatus('Open failed: ' + (note.error || note.status), true); return }
  registerOpen(id, note.data.title)
  renderEditor(note.data)
  try { window.api.tabs.registerOpen(id, id) } catch {}
}

// Hook for keyword index on save
window.keywordIndexUpdateFromSave = keywordIndexUpdateFromSave
