# SDK and development bundles

[Documentation index](../README.md)

Use the SDK to cross-build ARM64 applications on the host against the prepared
runtime's libraries. It is derived offline from the ARM64 build environment and
bound to a runtime fingerprint. Frontend and 351Files builds use the ARM64 chroot
by default; this SDK is for application development.

Run these commands from the repository root with the same `WORK_DIR` used by
[the build](BUILD.md):

```bash
export WORK_DIR="$HOME/darkos-g350-qemu-v08272026"
make qemu-sdk
bash qemu/sdk.sh check
bash qemu/app.sh build qemu/demos/sdk-app
bash qemu/vm.sh start gtk-gl
bash qemu/app.sh deploy "$WORK_DIR/apps/sdk-app/sdl-demo"
```

The example binary is installed under `/opt/darkos-apps/sdl-demo/sdl-demo`.
Quit ES and other graphical applications before running the demo through the
guest graphics wrapper:

```bash
bash qemu/vm.sh ssh 'sudo -n bash /opt/darkos-qemu/env.sh /opt/darkos-apps/sdl-demo/sdl-demo'
```

`app.sh deploy` checks the ELF architecture, verifies the VM and compares runtime
identity before copying. It deploys one binary, not a complete PortMaster package.
For game packaging, see [PortMaster](PORTMASTER.md).

## Use the toolchain directly

```bash
source "$WORK_DIR/sdk/environment.sh"
cmake -S /path/to/application -B /path/to/build -G Ninja \
  -DCMAKE_TOOLCHAIN_FILE="$DARKOS_TOOLCHAIN"
cmake --build /path/to/build
```

The environment selects host GCC/G++ 12 ARM64 cross-compilers and the SDK
sysroot/pkg-config paths. It clears `PKG_CONFIG_PATH` and prioritizes private
SDL/Mesa dependencies over vendor libraries. Start a fresh shell for unrelated
build work. `qemu/sdk.sh prepare` can refresh launchers/toolchain metadata while
retaining a valid sysroot. Rebuild or import a matching SDK if runtime identity
or sysroot verification fails.

## Export and import for development

These bundles preserve a development environment, including SSH support. For
an end-user package with automatic ES startup, use [release packaging](RELEASE.md).
Stop the VM and choose destination directories that do not exist:

```bash
bash qemu/vm.sh stop
bash qemu/vm.sh export "$HOME/darkos-g350-runtime-export"
bash qemu/sdk.sh export "$HOME/darkos-g350-sdk-export"
```

Runtime export produces an independent QCOW2, kernel, image profile, checksums
and provenance. Sanitization applies to the exported copy. An export is a snapshot;
later changes to the working VM do not update it.

On a host prepared according to [Build](BUILD.md#host-requirements), clone the
same source revision and import into a fresh work directory:

```bash
export WORK_DIR="$HOME/darkos-g350-qemu-imported"
bash qemu/setup.sh import /path/to/darkos-g350-runtime-export
bash qemu/sdk.sh import /path/to/darkos-g350-sdk-export
bash qemu/sdk.sh check
bash qemu/vm.sh es
```

Imports verify content and SDK/runtime identity. Runtime import creates a fresh
SSH host identity. The original bundles and working disks are preserved; these
commands do not publish anything. Source `environment.sh` from the imported SDK
location when using its toolchain directly.
