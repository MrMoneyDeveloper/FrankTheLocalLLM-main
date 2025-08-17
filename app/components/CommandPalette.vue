<template>
  <div v-if="open" class="fixed inset-0 bg-black/40 flex items-start justify-center pt-20">
    <div class="bg-white w-96 p-2 rounded">
      <input v-model="query" class="border w-full mb-2" placeholder="Search..." />
      <ul>
        <li v-for="t in filtered" :key="t" class="p-1 hover:bg-gray-200 cursor-pointer" @click="select(t)">{{ t }}</li>
      </ul>
    </div>
  </div>
</template>
<script setup>
import { ref, computed } from 'vue'

const props = defineProps({ open: Boolean, titles: Array })
const emits = defineEmits(['select', 'close'])
const query = ref('')
const filtered = computed(() => props.titles.filter(t => t.toLowerCase().includes(query.value.toLowerCase())))

function select (t) {
  emits('select', t)
  emits('close')
}
</script>
