import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
// @ts-check

export default defineConfig({
  plugins: [vue()],
  build: {
    outDir: 'html',
    emptyOutDir: true,
  },
  server: {
    host: '127.0.0.1',
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8011',
        changeOrigin: true,
      },
    },
  },
})
