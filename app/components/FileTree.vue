<template>
  <div class="p-2 space-y-4">
    <div>
      <input v-model="search" placeholder="Search notes" class="border w-full mb-2" />
      <select v-model="selectedGroup" class="border w-full mb-2">
        <option value="">All Groups</option>
        <option v-for="g in groups" :key="g" :value="g">{{ g }}</option>
      </select>
      <button @click="load" class="px-2 py-1 bg-gray-200">Search</button>
    </div>
    <div>
      <div v-for="(items, grp) in grouped" :key="grp" class="mb-4">
        <h3 class="font-bold">{{ grp || 'Ungrouped' }}</h3>
        <ul class="ml-2 list-disc">
          <li v-for="n in items" :key="n.id">{{ n.title }}</li>
        </ul>
      </div>
    </div>
    <div class="mt-4">
      <h3 class="font-bold mb-1">New Note</h3>
      <input v-model="newTitle" placeholder="Title" class="border w-full mb-1" />
      <input v-model="newGroup" placeholder="Group" class="border w-full mb-1" />
      <textarea v-model="newContent" placeholder="Content" class="border w-full mb-1"></textarea>
      <button @click="create" class="bg-blue-500 text-white px-2 py-1">Add</button>
    </div>
    <div class="mt-4 h-40 border">Graph</div>
  </div>
</template>
<script setup>
import { ref, computed, onMounted } from 'vue'

const search = ref('')
const selectedGroup = ref('')
const entries = ref([])
const newTitle = ref('')
const newGroup = ref('')
const newContent = ref('')
const API_BASE = (import.meta.env?.VITE_API_BASE || '/api').replace(/\/$/, '')


const groups = computed(() => {
  return [...new Set(entries.value.map(e => e.group).filter(Boolean))]
})

const grouped = computed(() => {
  const map = {}
  for (const e of entries.value) {
    const g = e.group || ''
    if (!map[g]) map[g] = []
    map[g].push(e)
  }
  return map
})

async function load () {
  const params = new URLSearchParams()
  if (search.value) params.append('q', search.value)
  if (selectedGroup.value) params.append('group', selectedGroup.value)
  const resp = await fetch(`${API_BASE}/entries?${params.toString()}`)

  entries.value = await resp.json()
}

async function create () {
  await fetch(`${API_BASE}/entries`, {

    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ title: newTitle.value, group: newGroup.value, content: newContent.value })
  })
  newTitle.value = ''
  newGroup.value = ''
  newContent.value = ''
  await load()
}

onMounted(load)
</script>
