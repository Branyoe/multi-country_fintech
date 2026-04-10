import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
import path from 'path'

const usePolling = process.env.VITE_USE_POLLING !== 'false'
const pollingInterval = Number(process.env.VITE_POLLING_INTERVAL ?? 500)

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    host: '0.0.0.0',
    port: 3000,
    hmr: {
      host: 'localhost',
      port: 3000,
      protocol: 'ws',
    },
    watch: {
      usePolling,
      interval: pollingInterval,
    },
    proxy: {
      '/api':    { target: process.env.VITE_PROXY_TARGET ?? 'http://localhost:8000', changeOrigin: true },
      '/admin':  { target: process.env.VITE_PROXY_TARGET ?? 'http://localhost:8000', changeOrigin: true },
      '/static': { target: process.env.VITE_PROXY_TARGET ?? 'http://localhost:8000', changeOrigin: true },
      '/ws':     { target: process.env.VITE_PROXY_TARGET ?? 'http://localhost:8000', changeOrigin: true, ws: true },
    },
  },
  resolve: {
    alias: {
      '~': path.resolve(__dirname, './src'),
    },
  },
})
