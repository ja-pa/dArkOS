#!/usr/bin/env bash
set -euo pipefail
exec bash "$(dirname "$0")/qemu/pipeline.sh" "${1:-all}"
