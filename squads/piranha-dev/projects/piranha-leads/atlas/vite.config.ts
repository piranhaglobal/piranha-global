import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        // SSE precisa de bypass de buffering
        configure: (proxy) => {
          proxy.on('proxyReq', (_proxyReq, req) => {
            if (req.url?.includes('/stream')) {
              _proxyReq.setHeader('Accept', 'text/event-stream')
            }
          })
        },
      },
    },
    // Ignorar ficheiros Python para não fazer page reload desnecessário
    watch: {
      ignored: ['**/*.py', '**/*.db', '**/*.csv', '**/data/**'],
    },
  },
})
