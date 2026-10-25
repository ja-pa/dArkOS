#!/usr/bin/env bash
# Retain PICO-8 user data; other systems retain the existing clean-release policy.
set -euo pipefail
[[ -d $ROOT/roms ]]
find "$ROOT/roms" -type f ! -path "$ROOT/roms/pico-8/*" \( -iname '*.srm' -o -iname '*.sav' -o -name '*.state' -o -name '*.state[0-9]*' \) -delete
