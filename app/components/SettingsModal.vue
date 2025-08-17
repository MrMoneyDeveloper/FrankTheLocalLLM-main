<template>
  <div v-if="open" class="fixed inset-0 bg-black/50 flex items-center justify-center">
    <div class="bg-white p-4 rounded w-64">
      <h2 class="text-lg mb-2">Settings</h2>
      <div class="mb-2">
        <label>Model</label>
        <input v-model="model" class="border w-full" />
      </div>
      <div class="mb-2">
        <label>Chunk Size</label>
        <input v-model.number="chunk" type="number" class="border w-full" />
      </div>
      <div class="mb-2">
        <label>Retrieval k</label>
        <input v-model.number="k" type="number" class="border w-full" />
      </div>
      <button @click="save" class="bg-blue-500 text-white px-2 py-1 rounded">Save</button>
    </div>
  </div>
</template>
<script setup>
import { ref } from 'vue'

const props = defineProps({ open: Boolean })
const emits = defineEmits(['close'])
const model = ref(localStorage.getItem('model') || 'llama3')
const chunk = ref(Number(localStorage.getItem('chunk')) || 512)
const k = ref(Number(localStorage.getItem('k')) || 8)

function save () {
  localStorage.setItem('model', model.value)
  localStorage.setItem('chunk', chunk.value)
  localStorage.setItem('k', k.value)
  emits('close')
}
</script>
