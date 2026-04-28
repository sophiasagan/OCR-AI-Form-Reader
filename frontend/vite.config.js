import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  // VITE_BASE_PATH must match the GitHub repo name for project pages,
  // e.g. /cu-form-reader/  — leave unset (or set to /) for a custom domain.
  base: process.env.VITE_BASE_PATH || '/',
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/extract': 'http://localhost:8000',
      '/form-types': 'http://localhost:8000',
      '/health': 'http://localhost:8000',
    },
  },
})
