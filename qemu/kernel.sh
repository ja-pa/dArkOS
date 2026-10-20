#!/usr/bin/env bash
source "$(dirname "$0")/lib.sh"
export SOURCE_REPO=${SOURCE_REPO:-https://github.com/ja-pa/kernel_5_10_226.git}
exec bash "$QEMU_DIR/scripts/build-kernel.sh"
