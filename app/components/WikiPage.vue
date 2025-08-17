<template>
  <div class="flex h-screen">
    <div class="w-1/3 border-r overflow-auto">
      <FileTree />
    </div>
    <div class="flex-1 flex flex-col">
      <ChatInterface class="flex-1" />
    </div>
    <CommandPalette :open="palette" :titles="titles" @close="palette=false" @select="jump" />
    <SettingsModal :open="settings" @close="settings=false" />
  </div>
</template>
<script setup>
import { ref, onMounted } from 'vue'
import ChatInterface from './ChatInterface.vue'
import FileTree from './FileTree.vue'
import CommandPalette from './CommandPalette.vue'
import SettingsModal from './SettingsModal.vue'
import { useFetch } from '../composables/useFetch'

const palette = ref(false)
const settings = ref(false)
const titles = ref([])

const { data, fetchData } = useFetch('/api/entries')

onMounted(async () => {
  await fetchData()
  titles.value = (data.value || []).map(e => e.content.split('\n')[0])
})

function jump (title) {
  // placeholder: open note
  console.log('jump to', title)
}

window.addEventListener('keydown', e => {
  if (e.key === 'k' && (e.metaKey || e.ctrlKey)) {
    palette.value = true
  }
})
</script>
