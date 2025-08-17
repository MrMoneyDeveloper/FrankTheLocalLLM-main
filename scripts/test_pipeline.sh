#!/usr/bin/env bash
set -euo pipefail

npm run lint
npm test -- --run
pytest backend/tests

# run migrations in sqlite docker if available
if command -v docker >/dev/null 2>&1; then
  docker run --rm -v $(pwd)/src/Infrastructure/Migrations:/migrations -v $(pwd)/tmp:/data nouchka/sqlite3 sqlite3 /data/test.db < /migrations/0001_initial.sql
else
  echo "Docker not found; skipping migration test"
fi
