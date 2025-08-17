import { describe, it, expect, vi, beforeEach } from 'vitest'
import { useFetch } from '../../composables/useFetch'

vi.useFakeTimers()

describe('useFetch', () => {
  beforeEach(() => {
    vi.clearAllTimers()
    vi.resetAllMocks()
    localStorage.clear()
  })

  it('adds Authorization header from localStorage', async () => {
    localStorage.setItem('token', 'abc')
    const fetchMock = vi.fn(() => Promise.resolve({ ok: true, json: () => Promise.resolve({ ok: true }) }))
    global.fetch = fetchMock

    const { fetchData } = useFetch('/api/test')
    const p = fetchData()
    vi.runAllTimers()
    await p
    expect(fetchMock).toHaveBeenCalled()
    expect(fetchMock.mock.calls[0][1].headers.Authorization).toBe('Bearer abc')
  })
})
