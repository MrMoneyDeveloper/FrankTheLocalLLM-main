<template>
  <div>
    <h1>Dashboard</h1>
    <ul>
      <li v-for="item in items" :key="item.id">{{ item.content }}</li>
    </ul>
  </div>
</template>
<script setup>
defineOptions({ name: 'AppDashboard' })
import { onMounted } from 'vue'
import { useFetch } from '../composables/useFetch'

const { data: items, fetchData } = useFetch('/api/entries')

onMounted(() => {
  fetchData()
})
</script>
