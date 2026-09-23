import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
import path from 'path'
import { execFile } from 'child_process'
import { promisify } from 'util'

const execFileAsync = promisify(execFile)
const CLI_PATH = path.resolve(__dirname, '../bin/paragravity')

export default defineConfig({
  plugins: [
    react(),
    tailwindcss(),
    {
      name: 'paragravity-api',
      configureServer(server) {
        server.middlewares.use(async (req, res, next) => {
          if (!req.url?.startsWith('/api/')) {
            return next()
          }

          res.setHeader('Content-Type', 'application/json')
          const url = new URL(req.url, 'http://localhost')
          const pathname = url.pathname

          try {
            // GET /api/profiles
            if (req.method === 'GET' && pathname === '/api/profiles') {
              const { stdout } = await execFileAsync('python3', [CLI_PATH, 'list', '--json'])
              return res.end(stdout.trim() || '[]')
            }

            // POST /api/profiles (Create profile)
            if (req.method === 'POST' && pathname === '/api/profiles') {
              let body = ''
              req.on('data', chunk => { body += chunk })
              req.on('end', async () => {
                try {
                  const data = JSON.parse(body || '{}')
                  const name = (data.name || '').trim()
                  if (!name) {
                    res.statusCode = 400
                    return res.end(JSON.stringify({ error: 'Profile name is required' }))
                  }
                  const args = [CLI_PATH, 'create', name]
                  if (data.description) args.push('-d', data.description)
                  if (data.launch) args.push('-l')

                  const { stdout, stderr } = await execFileAsync('python3', args)
                  return res.end(JSON.stringify({ success: true, message: stdout || stderr }))
                } catch (err: any) {
                  res.statusCode = 500
                  return res.end(JSON.stringify({ error: err.message || 'Failed to create profile' }))
                }
              })
              return
            }

            // POST /api/profiles/:name/launch
            const launchMatch = pathname.match(/^\/api\/profiles\/([^/]+)\/launch$/)
            if (req.method === 'POST' && launchMatch) {
              const name = decodeURIComponent(launchMatch[1])
              const { stdout, stderr } = await execFileAsync('python3', [CLI_PATH, 'launch', name])
              return res.end(JSON.stringify({ success: true, message: stdout || stderr }))
            }

            // POST /api/profiles/:name/stop
            const stopMatch = pathname.match(/^\/api\/profiles\/([^/]+)\/stop$/)
            if (req.method === 'POST' && stopMatch) {
              const name = decodeURIComponent(stopMatch[1])
              const { stdout, stderr } = await execFileAsync('python3', [CLI_PATH, 'stop', name, '--force'])
              return res.end(JSON.stringify({ success: true, message: stdout || stderr }))
            }

            // DELETE /api/profiles/:name
            const deleteMatch = pathname.match(/^\/api\/profiles\/([^/]+)$/)
            if (req.method === 'DELETE' && deleteMatch) {
              const name = decodeURIComponent(deleteMatch[1])
              const { stdout, stderr } = await execFileAsync('python3', [CLI_PATH, 'delete', name, '-f'])
              return res.end(JSON.stringify({ success: true, message: stdout || stderr }))
            }

            // GET /api/system
            if (req.method === 'GET' && pathname === '/api/system') {
              return res.end(JSON.stringify({
                version: '1.0.0',
                theme: 'dawn-iris',
                themeName: '晨曦紫霞白 (Dawn Iris & Violet)',
                platform: process.platform,
              }))
            }

            res.statusCode = 404
            res.end(JSON.stringify({ error: 'Endpoint not found' }))
          } catch (err: any) {
            res.statusCode = 500
            res.end(JSON.stringify({ error: err.message || 'Internal server error' }))
          }
        })
      }
    }
  ],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
})
