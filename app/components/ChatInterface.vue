<template>
  <div class="flex flex-col h-full">
    <div ref="container" class="flex-1 overflow-y-auto p-4 space-y-2">
      <div v-for="(m, i) in messages" :key="i" :class="m.role === 'user' ? 'text-right' : 'text-left'">
        <span :class="m.role === 'user' ? 'bg-blue-200' : 'bg-gray-200'" class="inline-block px-2 py-1 rounded">{{ m.content }}</span>
      </div>
    </div>
    <div class="p-2 border-t">
      <input v-model="message" @keyup.enter="send" placeholder="Ask something..." class="border w-full p-2" />
    </div>
  </div>
</template>
<script setup>
import { ref, nextTick } from 'vue'

const message = ref('')
const messages = ref([])
const container = ref(null)
const API_BASE = (import.meta.env?.VITE_API_BASE || '/api').replace(/\/$/, '')


async function send () {
  if (!message.value) return
  const text = message.value
  messages.value.push({ role: 'user', content: text })
  message.value = ''
  await nextTick(() => { container.value.scrollTop = container.value.scrollHeight })
  const resp = await fetch(`${API_BASE}/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message: text })
  })
  const data = await resp.json()
  messages.value.push({ role: 'bot', content: data.response })
  await nextTick(() => { container.value.scrollTop = container.value.scrollHeight })
}
</script>
