import { $, el } from './utils.js'

export function initSettings() {
  const btn = document.getElementById('openSettings')
  if (btn) btn.onclick = async ()=>{
    const r = await window.api.settings.get()
    if (!r.ok) { window.setStatus('Failed to fetch settings: ' + (r.error || r.status), true); return }
    const s = r.data
    for (const k of ['CHAT_MODEL','EMBED_MODEL','CHUNK_SIZE','CHUNK_OVERLAP','REINDEX_DEBOUNCE_MS','SEARCH_THROTTLE_MS','MAX_CHUNKS_PER_QUERY']) {
      const inp = document.getElementById('set_' + k)
      if (inp) inp.value = s[k]
    }
    const modal = new bootstrap.Modal(document.getElementById('settingsModal'))
    modal.show()
  }

  const save = document.getElementById('saveSettings')
  if (save) save.onclick = async ()=>{
    const partial = {}
    function val(k) { const v = document.getElementById('set_' + k).value; const n = Number(v); return isNaN(n) ? v : n }
    for (const k of ['CHAT_MODEL','EMBED_MODEL','CHUNK_SIZE','CHUNK_OVERLAP','REINDEX_DEBOUNCE_MS','SEARCH_THROTTLE_MS','MAX_CHUNKS_PER_QUERY']) {
      partial[k] = val(k)
    }
    const r = await window.api.settings.update(partial)
    if (!r.ok) { window.setStatus('Settings save failed: ' + (r.error || r.status), true); return }
    window.setStatus('Settings applied')
    const modalEl = document.getElementById('settingsModal')
    const modal = bootstrap.Modal.getInstance(modalEl)
    if (modal) modal.hide()
  }
}

