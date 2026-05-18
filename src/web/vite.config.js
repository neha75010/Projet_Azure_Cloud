import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')
  // Local : func start (7071). Cloud : URL Function App (sans /api à la fin).
  const functionsTarget =
    env.VITE_FUNCTIONS_PROXY_TARGET || 'http://localhost:7071'

  return {
    plugins: [react()],
    server: {
      proxy: {
        '/api': {
          target: functionsTarget,
          changeOrigin: true,
          secure: true,
        },
      },
    },
  }
})
