import { ref } from 'vue'

/**
 * Generic fetch composable with debouncing and
 * exponential backoff retries.
 * @param {string} url - request URL
 * @param {object} options - fetch options
 * @param {object} config - { debounce: number, retries: number }
 */
export function useFetch (url, options = {}, config = {}) {
  const { debounce = 0, retries = 3 } = config

  const data = ref(null)
  const error = ref(null)
  const loading = ref(false)

  let timeoutId

  const perform = async (override = {}, resolve) => {
    loading.value = true
    error.value = null

    const opts = { ...options, ...override }
    opts.headers = { ...(options.headers || {}), ...(override.headers || {}) }

    let attempt = 0
    while (attempt <= retries) {
      try {
        const base = (import.meta.env?.VITE_API_BASE || 'http://localhost:8001')
          .replace(/\/$/, '')
        const path = url.startsWith('/') ? url : `/${url}`
        const target = url.startsWith('http')
          ? url
          : `${base}${path.startsWith('/api') ? path : '/api' + path}`
        const resp = await fetch(target, opts)
        if (!resp.ok) throw new Error(resp.statusText)
        data.value = await resp.json()
        loading.value = false
        resolve(data.value)
        return
      } catch (err) {
        attempt += 1
        if (attempt > retries) {
          error.value = err
          loading.value = false
          resolve(null)
          return
        }
        const delay = 2 ** attempt * 100
        await new Promise(r => setTimeout(r, delay))
      }
    }
  }

  const fetchData = async (override = {}) => {
    if (timeoutId) clearTimeout(timeoutId)
    return new Promise(resolve => {
      if (debounce > 0) {
        timeoutId = setTimeout(() => perform(override, resolve), debounce)
      } else {
        perform(override, resolve)
      }
    })
  }

  return { data, error, loading, fetchData }
}
