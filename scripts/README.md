
# MVC-Oriented Scripts (Git Bash on Windows)


## Quick start
```bash
# default ports (8001, 5173), backend first, auto-open browser

bash scripts/controller.sh

```

### Change order / ports
```bash

BACKEND_FIRST=false BACKEND_PORT=8002 FRONTEND_PORT=5174 bash scripts/controller.sh

```

### One-off runs
```bash

bash scripts/model.sh
bash scripts/view.sh
bash scripts/controller.sh rotate-logs

```

## Health checks

Backend: `curl -fsS http://localhost:${BACKEND_PORT}/api/hello`

Frontend: `curl -fsS http://localhost:${FRONTEND_PORT}`

## Notes

These scripts are POSIX and tested with Git Bash on Windows.

If ports are stuck, `free_port` in `common.sh` uses `lsof` when available; otherwise `netstat` + `taskkill`.

Set `VITE_API_BASE` explicitly if your backend runs on a non-default port.
