import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  server: {
    open: '/index.html',
    port: 5173,
    strictPort: true,
    hmr: {
      clientPort: 5173
    },
    proxy: {
      '/api': {
        target: 'http://localhost:8001',
        changeOrigin: true,
        rewrite: path => path.replace(/^\/api/, ''),
        ws: true
      },
      '/status': {
        target: 'http://localhost:8001',
        changeOrigin: true
      }
    }
  }
})
