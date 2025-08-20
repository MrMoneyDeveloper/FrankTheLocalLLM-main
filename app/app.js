import { createApp, ref } from 'vue'
import './styles.css'
import { useFetch } from './composables/useFetch.js'
import WikiPage from './components/WikiPage.vue'

createApp({
  setup() {
    // Default test credentials so the login form is pre-filled during demos.
    // Replace or remove for production deployments.
    const username = ref('testuser')
    const password = ref('testpass')
    const success = ref(false)

    const { error, loading, fetchData } = useFetch(

      '/auth/login',
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
