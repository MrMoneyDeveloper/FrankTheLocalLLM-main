import { $, el } from './utils.js'
import { searchAll, searchGroup, searchNote, buildIndex, updateFromSave } from './keyword.js'
import { state } from './state.js'

export function initSearchUI() {
  // Modal elements are in index.html
  document.addEventListener('keydown', (e)=>{
    if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k') {
      e.preventDefault(); openSearch()
    }
  })
  const q = $('#globalSearchInput')
  if (q) q.addEventListener('input', ()=> runSearch())
  const tabs = document.querySelectorAll('#searchTabs button')
  tabs.forEach(btn => btn.addEventListener('click', ()=> {
    tabs.forEach(b=> b.classList.remove('active'))
    btn.classList.add('active')
    runSearch()
  }))
}

export async function buildKeywordIndex() {
  await buildIndex((id)=> window.api.notes.get(id))
}

function openSearch() {
  const modal = new bootstrap.Modal(document.getElementById('searchModal'))
  modal.show()
  const q = $('#globalSearchInput')
  if (q) setTimeout(()=> q.focus(), 100)
}

async function runSearch() {
  const q = $('#globalSearchInput').value || ''
  const active = document.querySelector('#searchTabs .active')
  const resWrap = $('#globalSearchResults')
  resWrap.innerHTML = ''
  if (!q.trim()) return
  let items = []
  if (active && active.dataset.tab === 'all') items = searchAll(q)
  else if (active && active.dataset.tab === 'group') {
    // Use first group if any for demo; you can wire a selector later
    const gid = state.groups[0]?.id
    if (gid) items = await searchGroup(q, gid, (gid)=> window.api.groups.notes(gid))
  } else if (active && active.dataset.tab === 'note') {
    if (state.activeId) items = searchNote(state.activeId, q)
  }
  for (const it of items) {
    const row = el('div', { className: 'result' })
    row.innerHTML = `<div class="title">${it.title}</div><div class="snippet">${it.snippet}</div>`
    row.onclick = ()=> { window.openNote(it.noteId); const modalEl = document.getElementById('searchModal'); const inst = bootstrap.Modal.getInstance(modalEl); if (inst) inst.hide() }
    resWrap.append(row)
  }
}

// Expose update hook for autosave path
export function keywordIndexUpdateFromSave(id, title, content, updated_at) {
  updateFromSave(id, title, content, updated_at)
}

