# Sourced by run-qemu.sh after mode and cmd have been initialized.
audio=${QEMU_AUDIO:-auto}
case $audio in
  auto) if [[ $mode == gtk-gl ]]; then audio=pa; else audio=none; fi;;
  pa|none) ;;
  *) fail 'QEMU_AUDIO must be auto, pa or none';;
esac
if [[ $audio == pa ]]; then
  devices=$(qemu-system-aarch64 -device help 2>&1)
  for device in intel-hda hda-output; do
    [[ $devices == *\"$device\"* ]] || fail "QEMU lacks $device; install qemu-system-arm"
  done
  backends=$(qemu-system-aarch64 -audiodev help 2>&1)
  grep -qx 'pa' <<< "$backends" || fail 'QEMU lacks PulseAudio backend (pa); install qemu-system-gui'
  # Connect using libpulse itself: checking the socket alone misses a dead server.
  need python3
  need timeout
  timeout 8s python3 - <<'PY' || fail 'PulseAudio playback did not complete; WSLg audio may be stalled. See README.md (WSLg audio), or use QEMU_AUDIO=none'
import ctypes as c
import ctypes.util
import os
import socket

server = os.environ.get('PULSE_SERVER', '')
if server.startswith('unix:'):
    with socket.socket(socket.AF_UNIX) as sock:
        sock.settimeout(3)
        sock.connect(server[5:])
lib = c.CDLL(ctypes.util.find_library('pulse-simple') or 'libpulse-simple.so.0')
class Spec(c.Structure):
    _fields_ = [('format', c.c_int), ('rate', c.c_uint32), ('channels', c.c_uint8)]
lib.pa_simple_new.restype = c.c_void_p
lib.pa_simple_new.argtypes = [c.c_char_p, c.c_char_p, c.c_int, c.c_char_p,
                             c.c_char_p, c.POINTER(Spec), c.c_void_p, c.c_void_p,
                             c.POINTER(c.c_int)]
lib.pa_simple_free.argtypes = [c.c_void_p]
lib.pa_simple_write.argtypes = [c.c_void_p, c.c_void_p, c.c_size_t, c.POINTER(c.c_int)]
lib.pa_simple_drain.argtypes = [c.c_void_p, c.POINTER(c.c_int)]
error = c.c_int()
# Silent playback only; never opens a microphone. A connection alone does not
# detect a wedged WSLg RDP sink, which can block SDLPoP at its intro sound.
stream = lib.pa_simple_new(server.encode() or None, b'dArkOS audio check', 1,
                          None, b'preflight', c.byref(Spec(3, 44100, 2)),
                          None, None, c.byref(error))
if not stream:
    raise SystemExit(f'libpulse error {error.value}')
try:
    silence = c.create_string_buffer(4410 * 2 * 2)  # 100 ms, 44.1 kHz stereo s16le
    if lib.pa_simple_write(stream, silence, len(silence), c.byref(error)) < 0:
        raise SystemExit(f'libpulse write error {error.value}')
    if lib.pa_simple_drain(stream, c.byref(error)) < 0:
        raise SystemExit(f'libpulse drain error {error.value}')
finally:
    lib.pa_simple_free(stream)
PY
  cmd+=(-audiodev pa,id=audio0 -device intel-hda,id=hda0
    -device hda-output,bus=hda0.0,audiodev=audio0)
fi
