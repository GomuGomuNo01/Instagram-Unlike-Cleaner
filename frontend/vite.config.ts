import tailwindcss from '@tailwindcss/vite'
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vitest/config'

// Démo en ligne (`npm run build:demo`) : publiée sur GitHub Pages dans le sous-dossier du
// dépôt, compilée à part pour ne jamais remplacer l'interface servie par `iuc serve`.
const DEMO_BASE = '/Instagram-Unlike-Cleaner/'

// En développement (`npm run dev`), les appels /api sont relayés vers l'API lancée par
// `iuc serve`. changeOrigin réécrit l'en-tête Host en 127.0.0.1, seul hôte accepté.
export default defineConfig(({ mode }) => ({
  plugins: [react(), tailwindcss()],
  base: mode === 'demo' ? DEMO_BASE : '/',
  build: mode === 'demo' ? { outDir: 'dist-demo' } : {},
  server: {
    proxy: {
      '/api': { target: 'http://127.0.0.1:8765', changeOrigin: true },
    },
  },
  test: {
    environment: 'jsdom',
    setupFiles: ['./src/test/setup.ts'],
  },
}))
