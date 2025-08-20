import { createApp, ref } from 'https://unpkg.com/vue@3/dist/vue.esm-browser.js'
import { useFetch } from './composables/useFetch.js'
import WikiPage from './components/WikiPage.vue'

const apiBase = import.meta.env.VITE_API_BASE ?? 'http://localhost:8001/api'

createApp({
  setup() {
    const username = ref('')
    const password = ref('')
    const success = ref(false)

    const { error, loading, fetchData } = useFetch(
      `${apiBase}/auth/login`,
      { method: 'POST', headers: { 'Content-Type': 'application/json' } }
    )

    const submit = async () => {
      error.value = null
      if (!username.value || !password.value) {
        error.value = 'Username and password required'
        return
      }
      const result = await fetchData({
        body: JSON.stringify({ username: username.value, password: password.value })
      })
      if (result) {
        localStorage.setItem('token', result.access_token)
        success.value = true
      } else if (!error.value) {
        error.value = 'Login failed'
      }
    }

    return { username, password, loading, error, success, submit }
  }
}).component('WikiPage', WikiPage).mount('#app')
