import { app, BrowserWindow, ipcMain, shell } from 'electron'
import path from 'path'
import { fileURLToPath } from 'url'
import { spawn } from 'child_process'

const __filename = fileURLToPath(import.meta.url)
const __dirname = path.dirname(__filename)

const DEFAULT_BACKEND = {
  host: process.env.APP_HOST || '127.0.0.1',
  port: parseInt(process.env.APP_PORT || '8001', 10),
}

let backend = { ...DEFAULT_BACKEND }
let backendProc = null

async function wait(ms) { return new Promise(r => setTimeout(r, ms)) }

async function isBackendUp() {
  const url = `http://${backend.host}:${backend.port}/health`
  try {
    const res = await fetch(url, { method: 'GET' })
    return res.ok
  } catch {
    return false
  }
}

async function startBackendIfNeeded() {
  if (await isBackendUp()) return
  // Try to spawn python backend using module path
  const pythonCandidates = [
    process.env.PYTHON || 'python',
    'python3',
    path.join(process.cwd(), '.venv', 'Scripts', 'python.exe')
  ]
  const cmd = pythonCandidates.find(Boolean)
  const mod = path.join(process.cwd(), 'lite', 'src', 'app.py')
  try {
    backendProc = spawn(cmd, [mod], {
      env: { ...process.env, APP_PORT: String(backend.port) },
      stdio: 'ignore',
      detached: true,
    })
    backendProc.unref()
  } catch (e) {
    console.warn('Failed to spawn backend:', e)
  }
  // wait for it to come up
  for (let i = 0; i < 20; i++) {
    if (await isBackendUp()) return
    await wait(500)
  }
}

function createWindow() {
  const win = new BrowserWindow({
    width: 1200,
    height: 800,
    webPreferences: {
      contextIsolation: true,
      preload: path.join(__dirname, 'preload.js'),
    }
  })
  win.loadFile(path.join(__dirname, 'renderer', 'index.html'))
}

app.whenReady().then(async () => {
  await startBackendIfNeeded()
  createWindow()
  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) createWindow()
  })
})

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') app.quit()
})

