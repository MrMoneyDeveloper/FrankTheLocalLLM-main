import { $, el } from './utils.js'

export function initSettings() {
  const btn = document.getElementById('openSettings')
  if (btn) btn.onclick = async ()=>{
    const r = await window.api.settings.get()
    if (!r.ok) { window.setStatus('Failed to fetch settings: ' + (r.error || r.status), true); return }
    const s = r.data
    const keys = ['CHAT_MODEL','EMBED_MODEL','CHUNK_SIZE','CHUNK_OVERLAP','REINDEX_DEBOUNCE_MS','SEARCH_THROTTLE_MS','MAX_CHUNKS_PER_QUERY']
    for (const k of keys) {
      const inp = document.getElementById('set_' + k)
      if (inp) inp.value = s[k]
    }
    const sm = document.getElementById('set_SIMPLE_MODE'); if (sm) sm.checked = !!s.SIMPLE_MODE
    const modal = new bootstrap.Modal(document.getElementById('settingsModal'))
    modal.show()
  }

  const save = document.getElementById('saveSettings')
  if (save) save.onclick = async ()=>{
    const partial = {}
    function val(k) { const el = document.getElementById('set_' + k); if (!el) return undefined; const v = el.value; const n = Number(v); return isNaN(n) ? v : n }
    for (const k of ['CHAT_MODEL','EMBED_MODEL','CHUNK_SIZE','CHUNK_OVERLAP','REINDEX_DEBOUNCE_MS','SEARCH_THROTTLE_MS','MAX_CHUNKS_PER_QUERY']) {
      partial[k] = val(k)
    }
    const smEl = document.getElementById('set_SIMPLE_MODE'); if (smEl) partial.SIMPLE_MODE = smEl.checked
    const r = await window.api.settings.update(partial)
    if (!r.ok) { window.setStatus('Settings save failed: ' + (r.error || r.status), true); return }
    window.setStatus('Settings applied')
    const modalEl = document.getElementById('settingsModal')
    const modal = bootstrap.Modal.getInstance(modalEl)
    if (modal) modal.hide()
    // Apply Simple Mode instantly
    if (partial.SIMPLE_MODE !== undefined) {
      document.body.classList.toggle('simple-mode', !!partial.SIMPLE_MODE)
    }
  }

  // Reindex All button
  const reall = document.getElementById('reindexAll')
  if (reall) reall.onclick = async ()=>{
    try {
      const list = await window.api.notes.list()
      if (!list.ok) { window.setStatus('Failed to list notes: ' + (list.error || list.status), true); return }
      const notes = list.data.notes || []
      for (const n of notes) {
        await window.api.notes.update(n.id, { reindex: true, reindex_now: true })
      }
      window.setStatus('Reindex All queued/completed')
    } catch (e) {
      window.setStatus('Reindex All error: ' + (e && e.message), true)
    }
  }
}
