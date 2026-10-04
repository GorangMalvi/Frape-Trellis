import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import frappeui from 'frappe-ui/vite'
import path from 'path'
import fs from 'fs'

// frappe-ui copies index.html -> sprint/www/sprint.html with fs.copyFileSync, which on a
// Windows bind mount (Docker Desktop) fails with EPERM on its chmod and deletes the target.
// Rewrite it with a plain write once the bundle is closed so /sprint keeps its shell.
function ensureSpaShell() {
  return {
    name: 'sprint-ensure-spa-shell',
    apply: 'build',
    closeBundle() {
      const src = path.resolve(__dirname, '../sprint/public/frontend/index.html')
      const dest = path.resolve(__dirname, '../sprint/www/sprint.html')
      if (fs.existsSync(src)) fs.writeFileSync(dest, fs.readFileSync(src))
    },
  }
}

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [
    frappeui({
      frappeProxy: true,
      lucideIcons: true,
      jinjaBootData: true,
      buildConfig: {
        indexHtmlPath: '../sprint/www/sprint.html',
        emptyOutDir: true,
        sourcemap: true,
      },
    }),
    vue(),
    ensureSpaShell(),
  ],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, 'src'),
    },
  },
  build: {
    outDir: '../sprint/public/frontend',
    emptyOutDir: true,
    target: 'es2015',
  },
  server: {
    fs: {
      allow: [path.resolve(__dirname, '..')],
    },
  },
})
