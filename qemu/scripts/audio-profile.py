"""Apply the QEMU HDA guest profile, or inspect it without modifying the guest."""
import argparse
import json
import os
from pathlib import Path
import re
import shutil
import subprocess as sp
import xml.etree.ElementTree as ET


def backup(path):
    saved = path.with_name(path.name + '.before-qemu-audio')
    if path.exists() and not saved.exists():
        shutil.copy2(path, saved)


def write_changed(path, text):
    if path.exists() and path.read_text() == text:
        return
    backup(path)
    # Write in place to retain the owner/mode of existing user settings.
    path.write_text(text)


def settings_audio(path, card, mixer, enable):
    text = path.read_text()
    body = re.sub(r'<\?xml[^>]*\?>', '', text).strip()
    parsed = ET.fromstring('<qemu-wrapper>' + body + '</qemu-wrapper>')
    rooted = len(parsed) == 1 and parsed[0].tag in ('config', 'settings')
    root = parsed[0] if rooted else parsed
    changes = [('string', 'AudioCard', f'hw:{card}'), ('string', 'AudioDevice', mixer)]
    if enable:
        changes.append(('bool', 'EnableSounds', 'true'))
    for tag, name, value in changes:
        item = root.find(f"{tag}[@name='{name}']")
        if item is None:
            item = ET.SubElement(root, tag, name=name)
        item.set('value', value)
    output = ET.tostring(root, encoding='unicode') if rooted else '\n'.join(
        ET.tostring(child, encoding='unicode').strip() for child in root)
    write_changed(path, '<?xml version="1.0"?>\n' + output + '\n')


def alsa_config(card):
    return f'''# dArkOS QEMU HDA: shared stereo playback for ES and games.
pcm.qemu_dmix {{
    type dmix
    ipc_key 567320
    ipc_perm 0666
    slave {{
        pcm "hw:CARD={card},DEV=0"
        rate 44100
        channels 2
        period_size 2048
        buffer_size 8192
    }}
}}
pcm.!default {{ type plug slave.pcm "qemu_dmix" }}
ctl.!default {{ type hw card "{card}" }}
'''


def retroarch_audio(path):
    values = {'audio_driver': 'alsathread', 'audio_enable': 'true', 'audio_device': 'default'}
    lines = [line for line in path.read_text().splitlines()
             if line.split('=', 1)[0].strip() not in values]
    write_changed(path, '\n'.join(lines) + '\n' + ''.join(
        f'{name} = "{value}"\n' for name, value in values.items()))


def detect_card():
    cards = []
    for path in sorted(Path('/sys/class/sound').glob('card[0-9]*')):
        driver = (path / 'device/driver').resolve().name
        if driver == 'snd_hda_intel':
            cards.append((path / 'id').read_text().strip())
    if len(cards) != 1 or not re.fullmatch(r'[A-Za-z0-9_]+', cards[0]):
        raise RuntimeError(f'Expected one QEMU HDA card, found {cards}; boot the HDA kernel and launcher')
    return cards[0]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply', action='store_true', help='install/update the guest profile')
    args = parser.parse_args()
    if args.apply and os.geteuid() != 0:
        raise RuntimeError('Use sudo to apply the guest audio profile')
    # SSH may become ready before sound-node permissions and coldplug finish.
    sp.run(['udevadm', 'settle', '--timeout=30'], check=True)
    card = detect_card()
    controls = sp.check_output(['amixer', '-c', card, 'scontrols'], text=True)
    names = re.findall(r"Simple mixer control '([^']+)'", controls)
    mixer = next((name for name in ('Master', 'PCM', 'Speaker', 'Front') if name in names), None)
    if mixer is None:
        raise RuntimeError(f'No supported playback mixer: {names}')
    print(f'HDA card={card}; ES mixer={mixer}')
    if not args.apply:
        for command in (['aplay', '-l'], ['aplay', '-L'], ['amixer', '-c', card, 'sget', mixer]):
            sp.run(command, check=True)
        return
    # G350's board script can mute the HDA mixer during boot. Preserve the unit
    # before masking it, including installations with a regular file in /etc.
    unit = Path('/etc/systemd/system/audiopath.service')
    if not (unit.is_symlink() and os.readlink(unit) == '/dev/null'):
        loaded = sp.check_output(['systemctl', 'show', '-p', 'LoadState', '--value', 'audiopath.service'], text=True).strip()
        if loaded == 'loaded':
            sp.run(['systemctl', 'stop', 'audiopath.service'], check=True)
        backup(unit)
        unit.unlink(missing_ok=True)
        unit.symlink_to('/dev/null')
        sp.run(['systemctl', 'daemon-reload'], check=True)
    state = Path('/var/lib/darkos-qemu/audio-v1.json')
    previous = json.loads(state.read_text()) if state.exists() else {}
    # Validate all settings before modifying anything.
    settings = [path for path in (
        Path('/home/ark/.emulationstation/es_settings.cfg'),
        Path('/opt/darkos-es/home/.emulationstation/es_settings.cfg'),
    ) if path.is_file()]
    for path in settings:
        ET.fromstring('<qemu-wrapper>' + re.sub(r'<\?xml[^>]*\?>', '', path.read_text()) + '</qemu-wrapper>')
    for path in (Path('/etc/asound.conf'), Path('/home/ark/.asoundrc')):
        existed = path.exists()
        write_changed(path, alsa_config(card))
        if not existed and path.parent == Path('/home/ark'):
            owner = path.parent.stat()
            os.chown(path, owner.st_uid, owner.st_gid)
    migrated = previous.get('settings', [])
    for path in settings:
        settings_audio(path, card, mixer, str(path) not in migrated)
    retroarch = Path('/home/ark/.config/retroarch/retroarch.qemu.cfg')
    if retroarch.is_file() and not previous.get('retroarch'):
        retroarch_audio(retroarch)
    # Upgrade existing deployed wrappers, including G350 and SDK demo launchers.
    wrappers = list(Path('/opt/darkos-apps').glob('*/es-env.sh'))
    wrappers += [Path('/opt/darkos-qemu/env.sh'), Path('/opt/darkos-es/scripts/es-env.sh'),
                 Path('/opt/darkos-emulators/peanut-gb/scripts/es-env.sh'),
                 Path('/opt/darkos-emulators/peanut-gb/scripts/gb-run.sh')]
    for path in wrappers:
        if path.is_file():
            write_changed(path, path.read_text().replace(
                'SDL_AUDIODRIVER=dummy', 'SDL_AUDIODRIVER=${SDL_AUDIODRIVER:-alsa}'))
    if not previous:
        sp.run(['amixer', '-c', card, 'sset', mixer, '50%', 'unmute'], check=True)
    state.parent.mkdir(parents=True, exist_ok=True)
    # A no-audio serial boot can replace ALSA's global state with an empty file.
    # Keep a card-specific state; a skipped service never stores absent hardware.
    mixer_state = state.parent / 'alsa-hda.state'
    if not mixer_state.exists():
        sp.run(['/usr/sbin/alsactl', '-f', str(mixer_state), 'store', card], check=True)
    service = Path('/etc/systemd/system/darkos-qemu-audio.service')
    service_text = f'''[Unit]
Description=dArkOS QEMU HDA mixer state
Wants=alsa-restore.service
After=alsa-restore.service
ConditionPathExists=/proc/asound/{card}
ConditionPathExists={mixer_state}

[Service]
Type=oneshot
RemainAfterExit=yes
ExecStart=/usr/sbin/alsactl -f {mixer_state} restore {card}
ExecStop=/usr/sbin/alsactl -f {mixer_state} store {card}

[Install]
WantedBy=multi-user.target
'''
    if not service.exists() or service.read_text() != service_text:
        write_changed(service, service_text)
        sp.run(['systemctl', 'daemon-reload'], check=True)
    sp.run(['systemctl', 'enable', '--now', 'darkos-qemu-audio.service'], check=True)
    sp.run(['/usr/sbin/alsactl', '-f', str(mixer_state), 'store', card], check=True)
    sp.run(['/usr/sbin/alsactl', 'store', card], check=True)
    temporary = state.with_suffix('.tmp')
    temporary.write_text(json.dumps({'card': card, 'mixer': mixer,
                                'retroarch': retroarch.is_file(),
                                'settings': sorted(set(migrated + list(map(str, settings))))}, indent=2) + '\n')
    temporary.replace(state)
    print('QEMU audio profile applied; restart ES to use ALSA. Original files have .before-qemu-audio backups.')


if __name__ == '__main__':
    try:
        main()
    except (RuntimeError, OSError, ValueError, ET.ParseError, sp.CalledProcessError) as error:
        raise SystemExit(f'Audio profile: {error}')
