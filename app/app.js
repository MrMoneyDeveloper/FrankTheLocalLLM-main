import { createApp, ref } from 'https://unpkg.com/vue@3/dist/vue.esm-browser.js'
import { useFetch } from './composables/useFetch.js'
import WikiPage from './components/WikiPage.vue'

createApp({
  setup() {
    const username = ref('')
    const password = ref('')
    const success = ref(false)

    const { data, error, loading, fetchData } = useFetch(
      '/api/auth/login',
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
