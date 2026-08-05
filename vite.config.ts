import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  build: {
    rollupOptions: {
      output: {
        manualChunks(id: string) {
          if (id.includes('node_modules/react')) {
            return 'vendor';
          }
        },
      },
    },
  },
  server: {
    allowedHosts: [
      'overtone-hatred-everyone.ngrok-free.dev',
      '.ngrok-free.dev'
    ],
    proxy: {
      '/api': 'http://127.0.0.1:5000',
      '/uploads': 'http://127.0.0.1:5000',
    },
  },
})
