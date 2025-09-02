Troubleshooting

Local-only app: Electron + FastAPI backend with optional Ollama. This guide covers common issues for dev, CI, and packaged builds.

Startup / Backend
- Backend not starting: Electron spawns Python from `python`, `python3`, or `.venv/Scripts/python.exe`.
  - Ensure Python 3.10+ is installed and on PATH.
  - Check the log/console for errors. In packaged builds, backend logs are minimal; launch `lite/src/app.py` manually to verify.
- Data location: App data is stored under Electron `userData` (OS‑specific app data dir). In dev, set `DATA_DIR` to override.
- Ollama unavailable: For dev/CI, set `SKIP_OLLAMA=1 FAKE_EMBED=1 FAKE_LLM=1` to skip model pulls and use fake embeddings and replies.

Electron UI
- Blank window on launch: Check `electron/main.js` preload path and `contextIsolation` settings.
- Slow startup: Warm start target is < 2s. Avoid heavy work in `app.whenReady()` and turn off dev logging.

Indexing & Search
- Reindex delay: Controlled by `REINDEX_DEBOUNCE_MS` in settings. “Reindex now” triggers immediate indexing.
- Keyword search missing updates: In‑memory index updates on autosave/title changes. If out of sync, rebuild by reloading the app.

Packaging
- `npm run dist` (electron-builder) produces installers: Windows (NSIS), macOS (DMG), Linux (AppImage).
- Python backend in package: The `lite/` folder is bundled into `resources/`. The app still requires a system Python.
  - Optionally ship a PyInstaller-built backend exe and spawn that instead. Update `electron/main.js` to use the binary.
- User data safety: The app writes only under `userData`. No user files are overwritten on update.

CI
- CI uses fake LLM/embeddings: `SKIP_OLLAMA=1 FAKE_EMBED=1 FAKE_LLM=1`. End‑to‑end tests (Playwright) run headless.
- If Playwright fails to launch Electron on Linux: ensure `npx playwright install --with-deps` ran and use the provided config.

