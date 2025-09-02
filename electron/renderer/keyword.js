import { state } from './state.js'

const idx = {
  notes: new Map(), // id -> { title, updated_at, tokens: Map<token, count>, text: string }
}

function tokenize(text) {
  return (text.toLowerCase().match(/[a-z0-9_]+/g) || [])
}

export async function buildIndex(fetchNoteFn) {
  idx.notes.clear()
  for (const n of state.notes) {
    const r = await fetchNoteFn(n.id)
    if (!r.ok) continue
    addOrUpdate(n.id, r.data.title || n.title || 'Untitled', r.data.content || '', r.data.updated_at || Date.now())
  }
}

export function addOrUpdate(id, title, content, updated_at) {
  const tokens = new Map()
  for (const t of tokenize(title + ' ' + content)) {
    tokens.set(t, (tokens.get(t) || 0) + 1)
  }
  idx.notes.set(id, { title, updated_at: updated_at || Date.now(), tokens, text: content })
}

export function updateFromSave(id, titleOrNull, contentOrNull, updated_at) {
  const cur = idx.notes.get(id) || { title: '', updated_at: 0, tokens: new Map(), text: '' }
  const title = titleOrNull == null ? cur.title : titleOrNull
  const text = contentOrNull == null ? cur.text : contentOrNull
  addOrUpdate(id, title, text, updated_at || Date.now())
}

function scoreNote(meta, qTokens) {
  // term frequency + recency boost
  let tf = 0
  for (const t of qTokens) tf += meta.tokens.get(t) || 0
  const ageMs = Math.max(0, Date.now() - (meta.updated_at || 0))
  const recency = 1 - Math.min(1, ageMs / (14 * 24 * 3600 * 1000)) // within 14 days gets up to +1 boost
  return tf + 0.25 * recency
}

function makeSnippet(text, q) {
  const lower = text.toLowerCase()
  const idx = lower.indexOf(q.toLowerCase())
  if (idx < 0) return (text.slice(0, 120) + (text.length > 120 ? '…' : ''))
  const start = Math.max(0, idx - 40)
  const end = Math.min(text.length, idx + q.length + 80)
  const before = text.slice(start, idx)
  const match = text.slice(idx, idx + q.length)
  const after = text.slice(idx + q.length, end)
  return (start > 0 ? '…' : '') + before + '<mark>' + match + '</mark>' + after + (end < text.length ? '…' : '')
}

function searchIds(ids, q) {
  const qTokens = tokenize(q)
  if (qTokens.length === 0) return []
  const qFirst = qTokens[0]
  const out = []
  for (const id of ids) {
    const meta = idx.notes.get(id)
    if (!meta) continue
    const sc = scoreNote(meta, qTokens)
    if (sc <= 0) continue
    out.push({ noteId: id, title: meta.title, snippet: makeSnippet(meta.text || '', qFirst), score: sc })
  }
  out.sort((a,b)=> b.score - a.score)
  return out
}

export function searchAll(q) {
  return searchIds(Array.from(idx.notes.keys()), q)
}

export function searchNote(noteId, q) {
  return searchIds([noteId], q)
}

export async function searchGroup(q, groupId, fetchGroupNotes) {
  const r = await fetchGroupNotes(groupId)
  if (!r.ok) return []
  const ids = r.data.note_ids || []
  return searchIds(ids, q)
}

