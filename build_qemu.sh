#!/usr/bin/env bash
set -euo pipefail
exec bash "$(dirname "$0")/qemu/scripts/pipeline.sh" "${1:-all}"
