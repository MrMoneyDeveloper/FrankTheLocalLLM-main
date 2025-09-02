import { state } from './state.js'
import { $, el } from './utils.js'

export function initMinihub() {
  const moveBtn = $('#moveToGroupBtn')
  if (moveBtn) moveBtn.onclick = async ()=>{
    const active = state.activeId
    const gid = $('#moveToGroup').value
    if (active && gid) { await window.api.groups.addNote(gid, active); await window.refresh() }
  }
  const dup = $('#duplicateNoteBtn')
  if (dup) dup.onclick = async ()=>{
    const active = state.activeId
    if (!active) return
    const note = await window.api.notes.get(active)
    if (note.ok) { await window.api.notes.create(note.data.title + ' (copy)', note.data.content || '') ; await window.refresh() }
  }
  const openWin = $('#openWindowBtn')
  if (openWin) openWin.onclick = async ()=>{
    const active = state.activeId
    if (!active) return
    const note = await window.api.notes.get(active)
    if (note.ok) {
      const w = window.open('', '_blank')
      if (w && w.document) w.document.write(`<pre style="white-space:pre-wrap">${(note.data.content||'').replace(/</g,'&lt;')}</pre>`) 
    }
  }
}

