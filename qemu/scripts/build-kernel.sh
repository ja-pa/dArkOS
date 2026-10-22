#!/usr/bin/env bash
source "$(dirname -- "$0")/common.sh"
RELEASE_LOCK=${RELEASE_LOCK:-$PROJECT_DIR/locks/g350-v01302026.json}
# One source of truth, including direct invocation of this script.
source_info=$(python3 "$PROJECT_DIR/scripts/components.py" --lock "$RELEASE_LOCK" --kernel-source)
readarray -t kernel_source <<< "$source_info"
KERNEL_REPO=${kernel_source[0]}
KERNEL_COMMIT=${kernel_source[1]}
# A local mirror may supply the same pinned commit; it cannot select a revision.
SOURCE_REPO=${SOURCE_REPO:-$KERNEL_REPO}
for tool in git make gcc-12 aarch64-linux-gnu-gcc-12 flex bison bc; do need "$tool"; done
mkdir -p "$WORK_DIR" "$BUILD_DIR" "$WORK_DIR/logs"
if [[ ! -d "$KERNEL_SRC/.git" ]]; then
  [[ ! -e "$KERNEL_SRC" ]] || fail "Source path exists without .git: $KERNEL_SRC"
  git clone --no-hardlinks --no-checkout "$SOURCE_REPO" "$KERNEL_SRC"
  git -C "$KERNEL_SRC" config core.autocrlf false
  git -C "$KERNEL_SRC" config core.symlinks true
  git -C "$KERNEL_SRC" checkout --detach "$KERNEL_COMMIT"
fi
KERNEL_SRC=$(realpath "$KERNEL_SRC")
BUILD_DIR=$(realpath "$BUILD_DIR")
[[ $KERNEL_SRC != "$BUILD_DIR" ]] || fail 'BUILD_DIR must differ from KERNEL_SRC (out-of-tree builds only)'
[[ $(git -C "$KERNEL_SRC" rev-parse HEAD) == "$KERNEL_COMMIT" ]] || fail 'Unexpected kernel commit'
[[ -z $(git -C "$KERNEL_SRC" status --porcelain) ]] || fail 'Kernel source has local changes; preserve and investigate them before building'
case "$(findmnt -n -o FSTYPE -T "$KERNEL_SRC")" in
  9p|drvfs|ntfs*) fail 'Use the native Linux filesystem for KERNEL_SRC';;
esac
case "$(findmnt -n -o FSTYPE -T "$BUILD_DIR")" in
  9p|drvfs|ntfs*) fail 'Use the native Linux filesystem for BUILD_DIR';;
esac
args=(-C "$KERNEL_SRC" O="$BUILD_DIR" ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- CC=aarch64-linux-gnu-gcc-12 HOSTCC=gcc-12)
{
  git -C "$KERNEL_SRC" rev-parse HEAD
  aarch64-linux-gnu-gcc-12 --version | head -1
  gcc-12 --version | head -1
  make "${args[@]}" defconfig
  KCONFIG_CONFIG="$BUILD_DIR/.config" bash "$KERNEL_SRC/scripts/kconfig/merge_config.sh" -m -O "$BUILD_DIR" "$BUILD_DIR/.config" "$PROJECT_DIR/config/kernel/qemu-arm64.fragment"
  make "${args[@]}" olddefconfig
  for option in SERIAL_AMBA_PL011 SERIAL_AMBA_PL011_CONSOLE PCI PCI_HOST_GENERIC VIRTIO_PCI VIRTIO_BLK VIRTIO_NET EFI_PARTITION BTRFS_FS DEVTMPFS DEVTMPFS_MOUNT DRM DRM_VIRTIO_GPU SOUND SND SND_PCM SND_PCI SND_HDA SND_HDA_CORE SND_HDA_INTEL SND_HDA_GENERIC; do
    grep -qx "CONFIG_${option}=y" "$BUILD_DIR/.config" || fail "CONFIG_${option} must be built in"
  done
  make "${args[@]}" -j"${JOBS:-4}" Image
  sha256sum "$BUILD_DIR/arch/arm64/boot/Image" "$BUILD_DIR/.config"
} 2>&1 | tee "$WORK_DIR/logs/build-$(basename "$BUILD_DIR").log"
# Record the actual checkout and bind it to the resulting binary.
mkdir -p "$WORK_DIR/artifacts"
python3 "$PROJECT_DIR/scripts/components.py" --lock "$RELEASE_LOCK" --record-kernel "$KERNEL_SRC" "$BUILD_DIR/arch/arm64/boot/Image" "$WORK_DIR/artifacts/kernel-source.json"
