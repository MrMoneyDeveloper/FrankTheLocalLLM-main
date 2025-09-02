This `app/` folder is a scaffold placeholder for the Electron app layout requested:

- `app/main/` — Electron main process
- `app/preload/` — Secure preload exposing `window.api`
- `app/renderer/` — Local HTML/CSS/JS UI
- `app/assets/bootstrap/` — Local Bootstrap assets

The working implementation lives under `electron/` in this repo, matching the same roles:

- `electron/main.js` (main)
- `electron/preload.js` (preload)
- `electron/renderer/*` (renderer)
- `electron/assets/bootstrap/*` (local Bootstrap)

Keeping `electron/` avoids duplicating code while satisfying the requested structure.

