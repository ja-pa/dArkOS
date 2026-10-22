# Example ports

SDLPoP is the first bundled example of a PortMaster game shared between the
QEMU development environment and a physical dArkOS handheld. Like the console
validation ROMs, its upstream download is pinned by version and SHA-256; the
ZIP and game binary are generated/downloaded artifacts, not committed here.

## Prepare the example

From the repository root:

```bash
export WORK_DIR="$HOME/darkos-g350-qemu"
bash qemu/scripts/portmaster.sh prepare
```

The resulting archive is `$WORK_DIR/artifacts/portmaster/portable/sdlpop.zip`.
`manifest.json` and `SHA256SUMS` in its parent directory record the input pins
and generated archive hash. Pins live in [portmaster.lock.json](../locks/portmaster.lock.json).
The archive retains the upstream game binary, data, metadata and handheld
launcher; [SDLPoP.sh](SDLPoP.sh) selects the appropriate launch path.

## Try it

- **QEMU:** `make qemu-image` prepares the example and queues it for PortMaster
  autoinstall. Open **Ports -> PortMaster** once, then quit and restart ES to
  refresh the game list. Launch **Ports -> SDLPoP**.
- **Physical dArkOS:** back up an existing installation and saves, copy the same
  `sdlpop.zip` into PortMaster's `autoinstall/` directory and open PortMaster.
  Launch SDLPoP from Ports. Keep the ZIP basename unchanged.

For an already prepared QEMU image, upgrade steps and keyboard controls are in
[the PortMaster guide](../docs/PORTMASTER.md). SDLPoP is a playable example;
the console test suites remain separate under `tests/fixtures/`.

## Validation and sources

On 2026-10-22, the user reported successful gameplay, sound and controls with
the QEMU-produced ZIP on a physical dArkOS handheld using a similar base image
to the one used for QEMU. Save/load was not tested; return to the frontend was
not explicitly reported. The device was described as R36xx; the exact model is
not the focus of this example. The result demonstrates the reported portability
across these related dArkOS environments, not universal hardware compatibility.
The exact firmware version and tested archive hash were not supplied.

See [hardware report](../docs/evidence/portmaster/hardware.json) and
[QEMU validation notes](../docs/PORTMASTER.md#local-validation-2026-10-22).
Upstream sources and component license notices are retained with the package:

- SDLPoP: https://github.com/NagyD/SDLPoP
- Port package: https://github.com/PortsMaster/PortMaster-New
- PortMaster: https://github.com/PortsMaster/PortMaster-GUI
