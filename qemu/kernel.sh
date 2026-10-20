#!/usr/bin/env bash
source "$(dirname "$0")/lib.sh"
exec bash "$QEMU_DIR/scripts/build-kernel.sh"
