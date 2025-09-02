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
let mainWindow = null
// noteId -> { windowId, tabId }
const openNotes = new Map()

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
  const mod = app.isPackaged
    ? path.join(process.resourcesPath, 'lite', 'src', 'app.py')
    : path.join(process.cwd(), 'lite', 'src', 'app.py')
  try {
    const userData = app.getPath('userData')
    const dataDir = path.join(userData, 'lite-data')
    const docsDir = path.join(dataDir, 'docs')
    const chromaDir = path.join(dataDir, 'chroma')
    backendProc = spawn(cmd, [mod], {
      env: { 
        ...process.env,
        APP_PORT: String(backend.port),
        DATA_DIR: dataDir,
        DOCS_DIR: docsDir,
        CHROMA_DIR: chromaDir,
      },
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
  mainWindow = new BrowserWindow({
    width: 1200,
    height: 800,
    show: true,
    webPreferences: {
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: true,
      webSecurity: true,
      preload: path.join(__dirname, 'preload.js'),
    }
  })
  mainWindow.loadFile(path.join(__dirname, 'renderer', 'index.html'))
}

// Single instance lock
const gotTheLock = app.requestSingleInstanceLock()
if (!gotTheLock) {
  app.quit()
}

app.whenReady().then(async () => {
  await startBackendIfNeeded()
  createWindow()
  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) createWindow()
  })
})

app.on('second-instance', () => {
  if (mainWindow) {
    if (mainWindow.isMinimized()) mainWindow.restore()
    mainWindow.focus()
  }
})

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') app.quit()
})

// IPC for single-open behavior
ipcMain.handle('notes-open', async (event, noteId) => {
  const existing = openNotes.get(noteId)
  if (existing) {
    const win = BrowserWindow.fromId(existing.windowId)
    if (win) {
      if (win.isMinimized()) win.restore()
      win.focus()
      win.webContents.send('focus-note', noteId)
      return { ok: true, focused: true, windowId: win.id, tabId: existing.tabId || noteId }
    }
    // clean up stale
    openNotes.delete(noteId)
  }
  // not tracked yet
  return { ok: true, focused: false }
})

ipcMain.handle('notes-focus', async (event, noteId) => {
  const info = openNotes.get(noteId)
  if (!info) return { ok: false, error: 'not-open' }
  const win = BrowserWindow.fromId(info.windowId)
  if (!win) return { ok: false, error: 'window-missing' }
  if (win.isMinimized()) win.restore()
  win.focus()
  win.webContents.send('focus-note', noteId)
  return { ok: true }
})

ipcMain.on('tabs-register-open', (event, { noteId, tabId }) => {
  try {
    const win = BrowserWindow.fromWebContents(event.sender)
    if (win && noteId) {
      openNotes.set(noteId, { windowId: win.id, tabId: tabId || noteId })
    }
  } catch {}
})

ipcMain.on('tabs-register-close', (event, { noteId, tabId }) => {
  try {
    const win = BrowserWindow.fromWebContents(event.sender)
    const cur = openNotes.get(noteId)
    if (cur && win && cur.windowId === win.id) {
      openNotes.delete(noteId)
    }
  } catch {}
})
