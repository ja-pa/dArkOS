"""Play stereo markers in the verified guest and capture a host output monitor."""
import argparse
import io
import json
import math
import os
from pathlib import Path
import struct
import subprocess as sp
import time
import wave


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--monitor', required=True, help='Pulse output monitor, e.g. RDPSink.monitor (never a microphone)')
    parser.add_argument('--expect-muted', action='store_true', help='require silence while guest mixer is muted')
    args = parser.parse_args()
    if not args.monitor.endswith('.monitor'):
        parser.error('Select an output .monitor source explicitly')
    scripts = Path(__file__).resolve().parent
    sp.run(['python3', str(scripts / 'graphics-assert-vm.py')], check=True)
    logs = Path(os.environ['WORK_DIR']) / 'logs/audio'
    logs.mkdir(parents=True, exist_ok=True)
    rate = 44100
    output = io.BytesIO()
    with wave.open(output, 'wb') as wav:
        wav.setparams((2, 2, rate, 0, 'NONE', 'not compressed'))
        frames = bytearray()
        for channel in (0, 1):
            for i in range(rate):
                value = int(6500 * math.sin(2 * math.pi * (440 if channel == 0 else 880) * i / rate))
                frames.extend(struct.pack('<hh', value if channel == 0 else 0, value if channel == 1 else 0))
            frames.extend(bytes(rate // 2 * 4))
        wav.writeframes(frames)
    name = 'host-muted' if args.expect_muted else 'host-stereo'
    capture = logs / (name + '.wav')
    with (logs / 'host-capture.log').open('w') as log:
        recorder = sp.Popen(['ffmpeg', '-y', '-nostdin', '-hide_banner', '-loglevel', 'warning',
                             '-f', 'pulse', '-i', args.monitor, '-t', '6', '-ar', str(rate),
                             '-ac', '2', '-c:a', 'pcm_s16le', str(capture)], stdout=log, stderr=log)
        try:
            time.sleep(0.7)
            if recorder.poll() is not None:
                raise RuntimeError('Output monitor capture failed; inspect host-capture.log')
            sp.run(['bash', str(scripts / 'graphics-ssh.sh'), 'aplay', '-q'], input=output.getvalue(), check=True, timeout=30)
            recorder.wait(timeout=15)
            if recorder.returncode:
                raise RuntimeError('Output monitor capture failed')
        finally:
            if recorder.poll() is None:
                recorder.terminate()
                recorder.wait(timeout=5)
    with wave.open(str(capture), 'rb') as wav:
        samples = struct.unpack('<' + 'h' * (wav.getnframes() * 2), wav.readframes(wav.getnframes()))
    channels = (samples[0::2], samples[1::2])
    # A one-second marker must be visible mainly in its intended channel.
    windows = []
    for start in range(0, len(channels[0]) - rate // 10, rate // 10):
        count = rate // 10
        rms = [math.sqrt(sum(x*x for x in channel[start:start+count]) / count) for channel in channels]
        windows.append(rms)
    left = sum(a > 100 and a > 5*b for a, b in windows)
    right = sum(b > 100 and b > 5*a for a, b in windows)
    result = {'monitor': args.monitor, 'left_marker_windows': left, 'right_marker_windows': right,
              'expected_muted': args.expect_muted,
              'passed': max(max(pair) for pair in windows) < 2 if args.expect_muted else left >= 5 and right >= 5,
              'limitation': 'Confirms samples at the WSLg output monitor; physical audibility and crackling require listening.'}
    (logs / (name + '.json')).write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))
    if not result['passed']:
        raise RuntimeError(f'Unexpected output samples; inspect {capture}')


if __name__ == '__main__':
    main()
