# Packaging Guide

This document explains how to build distributable packages of the project once development is complete.

## Desktop Bundle with Tauri

The repository contains a [Tauri](https://tauri.app) project under `tauri/` that can generate a cross-platform desktop application.

1. Install Rust and the Tauri CLI:
   ```bash
   cargo install tauri-cli
   ```
2. Build the frontend and copy it into the Tauri crate:
   ```bash
   yarn workspace app build
   mkdir -p tauri/dist
   cp -r app/dist/* tauri/dist/ || true
   ```
3. Build the release bundle:
   ```bash
   cargo tauri build
   ```
   On Windows you can produce an MSI installer with:
   ```bash
   cargo tauri build --target x86_64-pc-windows-msvc --bundles msi
   ```

Generated binaries can be found under `src-tauri/target/release/bundle`.

## Makefile Convenience Target

Running `make all` will install dependencies, build the frontend and compile the Tauri application in one step.

## Docker Compose

For a containerized deployment you can use the provided `docker-compose.yml`. Build the images and start the stack with:

```bash
docker compose up --build
```

This launches Postgres with pgvector, Redis, the FastAPI API, Celery worker, Ollama and the Vue frontend.
