import { state } from './state.js'
import { $, el } from './utils.js'

let dragGroupId = null

export async function renderGroups() {
  const wrap = $('#groups')
  wrap.innerHTML = ''
  // Fetch counts
  const counts = {}
  await Promise.all((state.groups || []).map(async (g)=>{
    const r = await window.api.groups.notes(g.id)
    counts[g.id] = r.ok ? (r.data.note_ids || []).length : 0
  }))
  state.counts = counts

  for (const g of state.groups) {
    const item = el('div', { className: 'group', draggable: true })
    item.dataset.gid = g.id
    item.textContent = `${g.name} (${counts[g.id] || 0})`
    // Drag reorder
    item.addEventListener('dragstart', (e)=>{ dragGroupId = g.id })
    item.addEventListener('dragover', (e)=> e.preventDefault())
    item.addEventListener('drop', async (e)=>{
      e.preventDefault()
      const from = state.groups.findIndex(x=>x.id===dragGroupId)
      const to = state.groups.findIndex(x=>x.id===g.id)
      if (from>=0 && to>=0 && from!==to) {
        const [it] = state.groups.splice(from,1)
        state.groups.splice(to,0,it)
        await window.api.groups.reorder(state.groups.map(x=>x.id))
        renderGroups()
      }
    })
    // Accept drops of notes
    item.addEventListener('dragover', (e) => e.preventDefault())
    item.addEventListener('drop', async (e) => {
      e.preventDefault()
      const data = e.dataTransfer.getData('text/plain')
      if (data && data.startsWith('note:')) {
        const id = data.split(':')[1]
        await window.api.groups.addNote(g.id, id)
        renderGroups()
      }
    })
    wrap.append(item)
  }
  // Free Notes virtual group
  const allIds = new Set((state.notes||[]).map(n=>n.id))
  for (const gid of Object.keys(state.counts)) {
    // remove grouped ids lazily by querying lists
  }
  // compute grouped set
  try {
    const grouped = new Set()
    for (const g of state.groups) {
      const r = await window.api.groups.notes(g.id)
      if (r.ok) for (const id of (r.data.note_ids||[])) grouped.add(id)
    }
    const free = [...allIds].filter(id => !grouped.has(id))
    const freeItem = el('div', { className: 'group', draggable: false })
    freeItem.textContent = `Free Notes (${free.length})`
    wrap.append(el('div', { className: 'section' }, freeItem))
  } catch {}

  // Add group controls
  const row = el('div', { className: 'row' })
  const inp = el('input', { id: 'newGroupName', placeholder: 'New group name' })
  const btn = el('button', { textContent: 'Add', id: 'createGroupBtn' })
  btn.onclick = async () => {
    const name = inp.value.trim()
    if (!name) return
    await window.api.groups.create(name)
    inp.value = ''
    await window.refresh()
  }
  row.append(inp, btn)
  wrap.append(row)
}

