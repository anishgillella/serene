import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  envDir: '..', // Read .env from project root
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  server: {
    port: Number(process.env.SERENE_FRONTEND_PORT) || 8101,
    host: '0.0.0.0',
    strictPort: true,
  },
  preview: {
    port: 8102,
    strictPort: true,
  },
})
