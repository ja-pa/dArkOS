"""Local Ports acceptance: ES -> PortMaster / SDLPoP -> same ES process."""
import hashlib
import json
import os
from pathlib import Path
import shlex
import subprocess as sp
import sys
import time
import xml.etree.ElementTree as ET
from PIL import Image
from helpers.workflow_qmp import QMP

Q = Path(__file__).resolve().parents[1]
W = Path(os.environ['WORK_DIR'])
OUT = W / ('logs/portmaster-cold' if '--cold' in sys.argv else 'logs/portmaster')
OUT.mkdir(parents=True, exist_ok=True)
qmp = QMP(os.environ.get('QMP_SOCKET', str(W / 'state/qmp.sock')))
result = {'passed': False, 'physical_g350': 'unverified', 'cold_boot': '--cold' in sys.argv, 'runs': []}
ssh = ['bash', str(Q / 'scripts/graphics-ssh.sh')]

def remote(command, **kwargs):
    return sp.run([*ssh, command], check=True, capture_output=True, **kwargs).stdout

def wait(command, timeout=180):
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        value = sp.run([*ssh, command], capture_output=True)
        if value.returncode == 0:
            return value.stdout.decode().strip()
        time.sleep(1)
    raise RuntimeError('Timed out: ' + command)

def key(*codes, hold=200):
    qmp.command('send-key', {'keys': [{'type': 'qcode', 'data': c} for c in codes], 'hold-time': hold})
    time.sleep(1)

def shot(name, timeout=30):
    for attempt in range(12):
        remote('sudo -n mkdir -p /run/darkos-qemu; sudo -n rm -f /run/darkos-qemu/frame.ppm; sudo -n touch /run/darkos-qemu/capture.request')
        wait('test -s /run/darkos-qemu/frame.ppm && test ! -e /run/darkos-qemu/capture.request', timeout)
        data = remote('sudo -n cat /run/darkos-qemu/frame.ppm')
        p = OUT / (name + '.ppm')
        p.write_bytes(data)
        im = Image.open(p).convert('RGB')
        if len(im.getcolors(im.width * im.height)) > 8:
            im.save(p.with_suffix('.png'))
            return hashlib.sha256(im.tobytes()).hexdigest()
        time.sleep(2)
    raise RuntimeError('Blank frame: ' + name)

def prince_x(name):
    # Fixed acceptance scene: level 1, room 1. White trousers identify the kid;
    # exclude the bars at the left edge, torches above and HUD at the bottom.
    im = Image.open(OUT / (name + '.png')).convert('RGB')
    w, h = im.size
    xs = [x for y in range(int(h * .45), int(h * .85))
          for x in range(int(w * .06), int(w * .94))
          if min(im.getpixel((x, y))) > 200]
    if not xs:
        raise RuntimeError('Cannot locate SDLPoP kid in first-room acceptance scene')
    return sum(xs) / len(xs) / w

settings = remote('sudo -n cat /home/ark/.emulationstation/es_settings.cfg')
savepath = '/home/ark/.SDLPoP/QUICKSAVE.SAV'
saved = sp.run([*ssh, 'sudo -n cat ' + savepath], capture_output=True)
es_pid = None
app = None
children = []
try:
    wait('! pidof emulationstation prince.aarch64 >/dev/null && ! pgrep -f "^python3 /opt/darkos-qemu/portmaster-gui.py" >/dev/null')
    script = r"""from pathlib import Path
import re, xml.etree.ElementTree as E
p=Path('/home/ark/.emulationstation/es_settings.cfg')
t=E.fromstring('<settings>'+re.sub(r'<\?xml.*?\?>','',p.read_text())+'</settings>')
for tag,name,value in [('string','StartupSystem','ports'),('bool','StartupOnGameList','true')]:
 for old in list(t):
  if old.get('name')==name:t.remove(old)
 E.SubElement(t,tag,name=name,value=value)
p.write_text('<?xml version="1.0"?>\n'+'\n'.join(E.tostring(x,encoding='unicode') for x in t))
"""
    remote('sudo -n python3 -', input=script.encode())
    f = (OUT / 'es.log').open('w')
    app = sp.Popen([*ssh, 'cd /opt/darkos-es && sudo -n env DARKOS_QEMU_CAPTURE=1 bash /opt/darkos-qemu/env.sh ./emulationstation --home /home/ark --debug --no-splash'], stdout=f, stderr=sp.STDOUT)
    es_pid = wait('pidof emulationstation')
    time.sleep(6)
    shot('ports-menu')
    key('ret')  # PortMaster is alphabetically first.
    pm_pid = wait('pgrep -f "^python3 /opt/darkos-qemu/portmaster-gui.py"')
    children.append((pm_pid, 'portmaster-gui.py'))
    time.sleep(8)
    shot('portmaster', timeout=180)  # First launch installs the pinned pilot before rendering.
    # Pinned pugwash/scenes/startup.py requires 15 seconds before accepting
    # the first-run disclaimer. Do not race it on a clean image.
    time.sleep(16)
    # Accept the first-run upstream notice, or enter a harmless port list.
    key('z')
    time.sleep(4)
    shot('portmaster-list')
    key('x')
    key('esc')
    wait('! pgrep -f "^python3 /opt/darkos-qemu/portmaster-gui.py" >/dev/null')
    if wait('pidof emulationstation') != es_pid:
        raise RuntimeError('PortMaster restarted ES')
    shot('portmaster-returned')
    result['portmaster_returned_to_same_es'] = True
    # Newly installed files require an explicit ES rescan/restart. Do it only
    # after verifying that quitting PortMaster resumed the same frontend.
    key('f4')
    wait('! pidof emulationstation >/dev/null')
    app.wait(timeout=30)
    app = sp.Popen([*ssh, 'cd /opt/darkos-es && sudo -n env DARKOS_QEMU_CAPTURE=1 bash /opt/darkos-qemu/env.sh ./emulationstation --home /home/ark --debug --no-splash'], stdout=f, stderr=sp.STDOUT)
    es_pid = wait('pidof emulationstation')
    time.sleep(6)
    shot('ports-refreshed')
    key('down')
    for number in range(1 if '--cold' in sys.argv else 2):
        key('ret')
        game_pid = wait('pidof prince.aarch64')
        children.append((game_pid, 'prince.aarch64'))
        time.sleep(3)
        key('ret'); key('ret')
        time.sleep(8)  # Allow the intro sound to end and release crouch immobilization.
        shot(f'game-{number}')
        before_x = prince_x(f'game-{number}')
        key('right', hold=500)
        shot(f'movement-{number}')
        after_x = prince_x(f'movement-{number}')
        if abs(after_x - before_x) < .03:
            raise RuntimeError('SDLPoP kid did not move: menu input/save-load alone is insufficient; check WSLg audio playback')
        maps = remote('sudo -n cat /proc/' + game_pid + '/maps').decode()
        (OUT / f'game-{number}.maps').write_text(maps)
        if '/opt/darkos-graphics/usr/lib/aarch64-linux-gnu/libSDL2' not in maps or any(s in maps.lower() for s in ['libmali', 'librga', 'libgo2']):
            raise RuntimeError('Unexpected graphics dependencies')
        before_save = remote('sudo -n stat -c %Y ' + savepath + ' 2>/dev/null || echo 0').decode().strip()
        key('f6')
        wait('sudo -n test -s ' + savepath + ' && test $(sudo -n stat -c %Y ' + savepath + ') -gt ' + before_save)
        key('right'); key('up'); key('f9')
        shot(f'loaded-{number}')
        key('ctrl', 'q')
        wait('! pidof prince.aarch64 >/dev/null')
        if wait('pidof emulationstation') != es_pid:
            raise RuntimeError('Game restarted ES')
        wait('! pidof gptokeyb gptokeyb2 oga_controls >/dev/null')
        shot(f'returned-{number}')
        result['runs'].append({'game_pid': game_pid, 'es_pid': es_pid, 'save_load': True, 'returned': True,
                               'movement': {'before_x_fraction': before_x, 'after_x_fraction': after_x}})
    result['binary_sha256'] = remote('sha256sum /roms/ports/sdlpop/prince.aarch64').decode().split()[0]
    result['image_receipt'] = json.loads((W / 'state/image.json').read_text())['fingerprint']
    result['passed'] = True
    key('f4')
    wait('! pidof emulationstation >/dev/null')
    app.wait(timeout=30)
finally:
    for child_pid, expected in children:
        command = 'sudo -n cat /proc/' + child_pid + '/cmdline 2>/dev/null'
        current = sp.run([*ssh, command], capture_output=True).stdout
        if expected.encode() in current:
            sp.run([*ssh, 'sudo -n kill -TERM ' + shlex.quote(child_pid)], capture_output=True)
    if es_pid and sp.run([*ssh, 'pidof emulationstation'], capture_output=True).stdout.decode().strip() == es_pid:
        # Only stop this test's process, never an unrelated frontend.
        sp.run([*ssh, 'sudo -n kill -TERM ' + shlex.quote(es_pid)], capture_output=True)
    if saved.returncode == 0:
        remote('sudo -n tee ' + savepath + ' >/dev/null', input=saved.stdout)
    else:
        remote('sudo -n rm -f ' + savepath)
    remote('sudo -n tee /home/ark/.emulationstation/es_settings.cfg >/dev/null', input=settings)
    (OUT / 'results.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps(result, indent=2))
