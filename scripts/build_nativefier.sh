#!/bin/bash
set -e
URL=${1:-"https://smartpad.app"}
OUT_DIR=${2:-nativefier-build}
npx nativefier "$URL" "$OUT_DIR" -n SmartPad
