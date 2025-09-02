import { state, setActive, findTab, persistTabs } from './state.js'
import { $, el } from './utils.js'

let dragTabId = null

export function renderTabs() {
  const bar = $('#tabbar')
  bar.innerHTML = ''
  const stacks = new Map()
  for (const t of state.openTabs) {
    const sid = t.stackId || null
    if (!stacks.has(sid)) stacks.set(sid, [])
    stacks.get(sid).push(t)
  }
  for (const [sid, tabs] of stacks.entries()) {
    if (sid === null && tabs.length === 1) {
      bar.append(renderTab(tabs[0]))
    } else {
      // stack representation: show active or first with chevron
      const activeInStack = tabs.find(t => t.id === state.activeId) || tabs[0]
      const container = el('div', { className: 'tab' + (activeInStack.id === state.activeId ? ' active' : '') , draggable: true })
      container.dataset.stackId = sid || ''
      container.dataset.id = activeInStack.id
      const title = el('span', { textContent: activeInStack.title })
      const chevron = el('span', { textContent: ' ▾', style: 'margin-left:6px;cursor:pointer' })
      const close = el('span', { textContent: ' ×', style: 'margin-left:6px;cursor:pointer' })
      chevron.onclick = (e)=>{
        e.stopPropagation()
        const menu = el('div', { className: 'menu' })
        menu.style.position = 'fixed'
        menu.style.background = '#fff'
        menu.style.border = '1px solid #ddd'
        menu.style.padding = '4px'
        for (const tt of tabs) {
          const item = el('div', { textContent: tt.title, style: 'padding:2px 6px;cursor:pointer' })
          item.onclick = ()=>{ setActive(tt.id); renderTabs(); window.api.notes.get(tt.id).then((r)=>{ if(r.ok) window.renderEditor(r.data) }) ; document.body.removeChild(menu) }
          menu.append(item)
        }
        document.body.append(menu)
        menu.style.left = e.clientX + 'px'
        menu.style.top = e.clientY + 'px'
        const handler = ()=>{ if(document.body.contains(menu)) document.body.removeChild(menu) }
        setTimeout(()=>document.addEventListener('click', handler, { once: true }), 0)
      }
      close.onclick = (e)=>{ e.stopPropagation(); for (const tt of [...tabs]) window.closeTab(tt.id) }
      container.onclick = (e)=>{
        if (e.ctrlKey || e.metaKey) {
          toggleSelect(activeInStack.id, container)
          return
        }
        setActive(activeInStack.id); renderTabs(); window.api.notes.get(activeInStack.id).then((r)=>{ if(r.ok) window.renderEditor(r.data) })
      }
      enableDrag(container, activeInStack.id)
      container.append(title, chevron, close)
      bar.append(container)
    }
  }
}

function renderTab(t) {
  const btn = el('div', { className: 'tab' + (t.id === state.activeId ? ' active' : '') + (state.selectedTabIds.has(t.id) ? ' selected' : ''), draggable: true })
  btn.dataset.id = t.id
  btn.textContent = t.title
  const close = el('span', { textContent: ' ×', style: 'margin-left:6px;cursor:pointer' })
  close.onclick = (e)=>{ e.stopPropagation(); window.closeTab(t.id) }
  btn.onclick = (e)=>{
    if (e.ctrlKey || e.metaKey) { toggleSelect(t.id, btn); return }
    setActive(t.id); renderTabs(); window.api.notes.get(t.id).then((r)=>{ if(r.ok) window.renderEditor(r.data) })
  }
  enableDrag(btn, t.id)
  btn.append(close)
  return btn
}

function enableDrag(elm, id) {
  elm.addEventListener('dragstart', (e)=>{ dragTabId = id; e.dataTransfer.setData('text/plain', id) })
  elm.addEventListener('dragover', (e)=> e.preventDefault())
  elm.addEventListener('drop', (e)=>{
    e.preventDefault()
    const dragged = dragTabId
    dragTabId = null
    if (!dragged || dragged === id) return
    const from = state.openTabs.findIndex(t => t.id === dragged)
    const to = state.openTabs.findIndex(t => t.id === id)
    if (from < 0 || to < 0) return
    const [item] = state.openTabs.splice(from, 1)
    state.openTabs.splice(to, 0, item)
    persistTabs()
    renderTabs()
  })
}

export function mergeSelectedIntoStack() {
  const ids = Array.from(state.selectedTabIds)
  if (ids.length < 2) return
  const stackId = 's:' + Date.now()
  for (const t of state.openTabs) {
    if (ids.includes(t.id)) t.stackId = stackId
  }
  state.selectedTabIds.clear()
  persistTabs()
  renderTabs()
}

export function unstackTab(id) {
  const t = findTab(id)
  if (!t) return
  t.stackId = null
  persistTabs(); renderTabs()
}

export function registerOpen(id, title) {
  if (!findTab(id)) {
    state.openTabs.push({ id, title, stackId: null })
    setActive(id)
    persistTabs()
  }
  renderTabs()
}

function toggleSelect(id, elm) {
  if (state.selectedTabIds.has(id)) state.selectedTabIds.delete(id)
  else state.selectedTabIds.add(id)
  if (elm) elm.classList.toggle('selected')
}
