.PHONY: all deps frontend tauri

all: deps frontend tauri

deps:
yarn install
cd backend && poetry install --no-root

frontend:
yarn workspace app build

test -d tauri/dist || mkdir -p tauri/dist
cp -r app/dist/* tauri/dist/ || true

tauri:
cd tauri && cargo build --release
