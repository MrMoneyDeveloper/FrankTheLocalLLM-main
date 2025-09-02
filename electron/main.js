import { app, BrowserWindow, ipcMain, shell, dialog } from 'electron'
import path from 'path'
import fs from 'fs'
import net from 'net'
import { fileURLToPath } from 'url'
import { spawn } from 'child_process'

const __filename = fileURLToPath(import.meta.url)
const __dirname = path.dirname(__filename)
const DEBUG = String(process.env.DEBUG || '').toLowerCase() === '1' || String(process.env.DEBUG || '').toLowerCase() === 'true'

let logFile = null
function initLogger() {
  try {
    const logsDir = path.join(app.getPath('userData'), 'logs')
    fs.mkdirSync(logsDir, { recursive: true })
    logFile = path.join(logsDir, 'app.log')
  } catch {}
}

function log(...args) {
  const line = `[${new Date().toISOString()}] ` + args.map(a => (typeof a === 'string' ? a : JSON.stringify(a))).join(' ')
  if (DEBUG) {
    // eslint-disable-next-line no-console
    console.log(line)
  }
  try {
    if (!logFile) return
    fs.appendFileSync(logFile, line + '\n')
  } catch {}
}

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
    const ok = res.ok
    if (!ok) log('health check not ok', res.status)
    return ok
  } catch {
    return false
  }
}

async function ensureOllamaUp() {
  if (String(process.env.SKIP_OLLAMA || '0') === '1') return true
  try {
    const ctl = new AbortController()
    const id = setTimeout(() => ctl.abort(), 2000)
    const r = await fetch('http://127.0.0.1:11434/api/tags', { signal: ctl.signal })
    clearTimeout(id)
    return r.ok
  } catch {
    return false
  }
}

function findFreePort(start = 8001, attempts = 20) {
  return new Promise((resolve) => {
    let p = start
    const tryNext = () => {
      const server = net.createServer()
      server.unref()
      server.on('error', () => {
        p += 1
        if (attempts-- > 0) tryNext()
        else resolve(start)
      })
      server.listen(p, '127.0.0.1', () => {
        server.close(() => resolve(p))
      })
    }
    tryNext()
  })
}

async function startBackendIfNeeded() {
  // If already up, we're good
  if (await isBackendUp()) return true
  // In development, do not spawn the backend. Wait for external API (npm:api).
  if (!app.isPackaged) {
    log('dev mode: waiting for external API to come up')
    for (let i = 0; i < 60; i++) { // ~30s
      if (await isBackendUp()) return true
      await wait(500)
    }
    return false
  }
  // Try to spawn python backend using module path
  const pythonCandidates = [
    process.env.PYTHON || 'python',
    'python3',
    path.join(process.cwd(), '.venv', 'Scripts', 'python.exe')
  ]
  const cmd = pythonCandidates.find(Boolean)
  const useModule = ['-m', 'lite.src.app']
  try {
    const userData = app.getPath('userData')
    const dataDir = path.join(userData, 'lite-data')
    const docsDir = path.join(dataDir, 'docs')
    const chromaDir = path.join(dataDir, 'chroma')
    const projectRoot = path.resolve(__dirname, '..')
    const cwd = app.isPackaged ? process.resourcesPath : projectRoot
    // try to pick a free port to avoid auto-increment surprises
    backend.port = await findFreePort(backend.port)
    backendProc = spawn(cmd, useModule, {
      cwd,
      env: { 
        ...process.env,
        APP_PORT: String(backend.port),
        DATA_DIR: dataDir,
        DOCS_DIR: docsDir,
        CHROMA_DIR: chromaDir,
      },
      stdio: DEBUG ? 'pipe' : 'ignore',
      detached: true,
    })
    if (DEBUG && backendProc.stdout && backendProc.stderr) {
      backendProc.stdout.on('data', (d) => log('[api stdout]', String(d).trim()))
      backendProc.stderr.on('data', (d) => log('[api stderr]', String(d).trim()))
    }
    backendProc.unref()
    log('spawned backend', { port: backend.port, cwd })
  } catch (e) {
    log('Failed to spawn backend:', e && e.message ? e.message : String(e))
  }
  // wait for it to come up
  for (let i = 0; i < 40; i++) {
    if (await isBackendUp()) return true
    await wait(500)
  }
  return false
}

function wireWindowLogging(win) {
  try {
    win.webContents.on('console-message', (_e, level, message, line, sourceId) => {
      log('[renderer]', level, message, sourceId + ':' + line)
    })
    win.webContents.on('did-fail-load', (_e, ec, desc, _url, isMainFrame) => {
      log('did-fail-load', ec, desc, 'isMainFrame=', isMainFrame)
    })
    win.webContents.on('render-process-gone', (_e, details) => {
      log('render-process-gone', details && details.reason)
    })
  } catch {}
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
      preload: path.join(__dirname, 'preload.cjs'),
    }
  })
  mainWindow.loadFile(path.join(__dirname, 'renderer', 'index.html'))
  wireWindowLogging(mainWindow)
}

// Single instance lock
const gotTheLock = app.requestSingleInstanceLock()
if (!gotTheLock) {
  app.quit()
}

app.whenReady().then(async () => {
  initLogger()
  log('app ready')
  const ollamaOk = await ensureOllamaUp()
  if (!ollamaOk) {
    const msg = 'Ollama is not reachable on 127.0.0.1:11434. Start it first (`ollama serve`) or set SKIP_OLLAMA=1 for development.'
    log(msg)
    try { await dialog.showMessageBox({ type: 'error', title: 'Ollama Required', message: msg }) } catch {}
    app.quit()
    return
  }
  const ok = await startBackendIfNeeded()
  if (!ok) {
    const msg = 'Backend failed to start. Ensure Python is installed and Ollama is running (or set SKIP_OLLAMA=1). See logs for details.'
    log(msg)
    try {
      await dialog.showMessageBox({ type: 'error', title: 'Startup Error', message: msg })
    } catch {}
    app.quit()
    return
  }
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
  log('notes-open', noteId)
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
  log('notes-focus', noteId)
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
  log('tabs-register-open', noteId, tabId)
  try {
    const win = BrowserWindow.fromWebContents(event.sender)
    if (win && noteId) {
      openNotes.set(noteId, { windowId: win.id, tabId: tabId || noteId })
    }
  } catch {}
})

ipcMain.on('tabs-register-close', (event, { noteId, tabId }) => {
  log('tabs-register-close', noteId, tabId)
  try {
    const win = BrowserWindow.fromWebContents(event.sender)
    const cur = openNotes.get(noteId)
    if (cur && win && cur.windowId === win.id) {
      openNotes.delete(noteId)
    }
  } catch {}
})

ipcMain.handle('logs-path', async () => {
  try {
    const logsDir = path.join(app.getPath('userData'), 'logs')
    return { ok: true, path: logsDir }
  } catch (e) {
    return { ok: false, error: e && e.message ? e.message : String(e) }
  }
})

ipcMain.handle('backend-base', async () => {
  try {
    return { ok: true, base: `http://${backend.host}:${backend.port}` }
  } catch (e) {
    return { ok: false, error: e && e.message ? e.message : String(e) }
  }
})
