export const $ = (sel) => document.querySelector(sel)
export const $$ = (sel) => Array.from(document.querySelectorAll(sel))
export function el(tag, attrs = {}, ...children) {
  const n = document.createElement(tag)
  Object.assign(n, attrs)
  for (const c of children) n.append(c)
  return n
}
export function msFromDateInput(s) {
  if (!s) return null
  const d = new Date(s)
  if (isNaN(d.getTime())) return null
  return d.getTime()
}
export function on(elm, ev, fn) { elm.addEventListener(ev, fn); return () => elm.removeEventListener(ev, fn) }

