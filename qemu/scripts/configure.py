"""Offline guest integration. Retain the release's theme, ROM paths and saves."""
import json,os,shutil,sys,xml.etree.ElementTree as ET
from pathlib import Path
root=Path(os.environ['ROOT']); work=Path(os.environ['WORK_DIR']); q=Path(__file__).resolve().parents[1]
profile=json.loads((work/'state/profile.json').read_text())
def write(path,text,mode=None):
    p=root/path.lstrip('/'); p.parent.mkdir(parents=True,exist_ok=True); p.write_text(text)
    if mode: p.chmod(mode)
def link(path,target):
    p=root/path.lstrip('/'); p.parent.mkdir(parents=True,exist_ok=True); p.unlink(missing_ok=True); p.symlink_to(target)
# Original fstab retained alongside a portable, image-derived QEMU profile.
p=root/'etc/fstab'; original=root/'etc/fstab.before-qemu'
if not original.exists(): shutil.copy2(p,original)
lines=[]
for part,mount,fs,opts in [('root','/',profile['root_fstype'],'defaults,noatime,compress=zlib:1'),('boot','/boot','vfat','defaults,nofail'),('roms','/roms','vfat','defaults,umask=000,uid=1000,gid=1000,nofail')]:
    if profile.get(part+'_partuuid'): lines.append(f'PARTUUID={profile[part+"_partuuid"]} {mount} {fs} {opts} 0 0')
write('/etc/fstab','\n'.join(lines)+'\n')
for name in ['firstboot','emulationstation','ogage','audiostate','audiopath','shutdowntasks','welcome-message','buttonmon','panel','check_battery','351mp','batt_led','logo','wifi_importer']:
    link('/etc/systemd/system/'+name+'.service','/dev/null')
link('/etc/systemd/system/multi-user.target.wants/ssh.service','/usr/lib/systemd/system/ssh.service')
link('/etc/systemd/system/getty.target.wants/serial-getty@ttyAMA0.service','/usr/lib/systemd/system/serial-getty@.service')
write('/etc/systemd/system/serial-getty@ttyAMA0.service.d/qemu.conf','[Service]\nExecStart=\nExecStart=-/sbin/agetty --autologin ark --noclear %I 115200 vt100\n')
write('/etc/ssh/sshd_config.d/00-qemu.conf','HostKey /etc/ssh/ssh_host_ed25519_key\nPubkeyAuthentication yes\nPasswordAuthentication no\nKbdInteractiveAuthentication no\nPermitRootLogin no\n')
# Explicit DHCP profile: do not depend on first-boot wired-profile generation.
write('/etc/NetworkManager/system-connections/qemu-virtio.nmconnection','[connection]\nid=QEMU VirtIO Ethernet\nuuid=057ad911-3d70-5eec-94f7-0bc2a3450542\ntype=ethernet\nautoconnect=true\nautoconnect-priority=100\n\n[ethernet]\n\n[ipv4]\nmethod=auto\n\n[ipv6]\nmethod=disabled\n',0o600)
write('/home/ark/.ssh/authorized_keys',(work/'ssh/id_ed25519.pub').read_text(),0o600)
os.chmod(root/'home/ark/.ssh',0o700)
os.chown(root/'home/ark/.ssh',1000,1000); os.chown(root/'home/ark/.ssh/authorized_keys',1000,1000)
write('/etc/darkos-qemu-profile','G350 release-to-QEMU ARM64 profile\n')
write('/etc/sudoers.d/qemu-development','ark ALL=(ALL) NOPASSWD: ALL\n',0o440)
# Keep originals, restrict the QEMU system menu to the accepted ARM64 families.
p=root/'etc/emulationstation/es_systems.cfg'; original=p.with_suffix('.cfg.before-qemu')
if not original.exists(): shutil.copy2(p,original)
tree=ET.parse(original); systems=tree.getroot(); selected={
 'gb':'gambatte','gbc':'gambatte','nes':'fceumm','snes':'snes9x','gba':'mgba','megadrive':'genesis_plus_gx'}
found=set()
for system in list(systems):
    name=system.findtext('name')
    if name not in selected or name in found or (name=='snes' and system.findtext('path','').rstrip('/')!='/roms/snes'): systems.remove(system); continue
    found.add(name)
    core=selected[name]
    if not (root/f'home/ark/.config/retroarch/cores/{core}_libretro.so').is_file(): raise RuntimeError('Missing original ARM64 core: '+core)
    system.find('command').text=f'/bin/bash /opt/darkos-qemu/retroarch.sh {core} %ROM%'
    for node in list(system):
        if node.tag in ['emulators','emulator']: system.remove(node)
if found!=set(selected): raise RuntimeError('Unexpected G350 ES system names: '+str(found))
# Ports are launched through the QEMU graphics adapter, independent of board hooks.
ports=ET.SubElement(systems,'system')
for tag,value in [('name','ports'),('fullname','Ports'),('path','/roms/ports'),
                  ('extension','.sh .SH'),('command','/bin/bash /opt/darkos-qemu/ports.sh %ROM%'),
                  ('platform','pc'),('theme','ports')]:
    ET.SubElement(ports,tag).text=value
tree.write(p,encoding='utf-8',xml_declaration=True)
# Stable keyboard mappings, matching the existing QEMU profile.
inputs=ET.Element('inputList'); keyboard=ET.SubElement(inputs,'inputConfig',type='keyboard',deviceName='Keyboard',deviceGUID='-1')
keys={'up':1073741906,'down':1073741905,'left':1073741904,'right':1073741903,'a':13,'b':27,'x':115,'y':97,'start':32,'select':9,'leftshoulder':113,'rightshoulder':119,'lefttrigger':49,'righttrigger':50,'hotkeyenable':27}
for name,key in keys.items(): ET.SubElement(keyboard,'input',name=name,type='key',id=str(key),value='1')
ET.ElementTree(inputs).write(root/'etc/emulationstation/es_input.cfg',encoding='utf-8',xml_declaration=True)
# ES uses sibling XML settings; preserve original theme and unrelated defaults.
p=root/'home/ark/.emulationstation/es_settings.cfg'
t=p.read_text().replace('<?xml version="1.0"?>',''); settings=ET.fromstring('<settings>'+t+'</settings>')
for tag,name,value in [('string','LogLevel','debug'),('string','PowerSaverMode','disabled'),('bool','BrightnessPopup','false'),('bool','VolumePopup','false'),('bool','EnableSounds','true'),('bool','ShowBattery','false'),('bool','HideWindow','true'),('int','ScreenRotate','0')]:
    for old in list(settings):
        if old.get('name')==name: settings.remove(old)
    ET.SubElement(settings,tag,name=name,value=value)
p.write_text('<?xml version="1.0"?>\n'+''.join(ET.tostring(x,encoding='unicode')+'\n' for x in settings))
# Preserve the released RetroArch defaults and override only QEMU I/O.
base=root/'home/ark/.config/retroarch/retroarch.cfg'
text=base.read_text(); overrides={'video_driver':'gl','video_context_driver':'kms','audio_driver':'alsathread','audio_enable':'true','midi_driver':'null','quit_press_twice':'false','input_driver':'udev','input_joypad_driver':'udev','video_fullscreen':'true','input_enable_hotkey':'nul','input_enable_hotkey_btn':'nul','input_enable_hotkey_axis':'nul','input_enable_hotkey_mbtn':'nul','input_exit_emulator':'escape','input_menu_toggle':'f1','input_save_state':'f2','input_load_state':'f4','savestate_auto_save':'false','savestate_auto_load':'false','menu_driver':'ozone','video_shader_enable':'false','input_player1_a':'z','input_player1_b':'x','input_player1_x':'s','input_player1_y':'a','input_player1_l':'q','input_player1_r':'w','input_player1_start':'enter','input_player1_select':'rshift','input_player1_up':'up','input_player1_down':'down','input_player1_left':'left','input_player1_right':'right','video_rotation':'0','video_allow_rotate':'false','savefile_directory':'/home/ark/.config/retroarch/saves','savestate_directory':'/home/ark/.config/retroarch/states'}
for name in ['saves','states','logs']: (base.parent/name).mkdir(exist_ok=True)
lines=[line for line in text.splitlines() if line.split('=',1)[0].strip() not in overrides]
write('/home/ark/.config/retroarch/retroarch.qemu.cfg','\n'.join(lines)+'\n'+''.join(f'{k} = "{v}"\n' for k,v in overrides.items()))
for f in (q/'runtime').iterdir():
    if f.is_file(): shutil.copy2(f,root/'opt/darkos-qemu'/f.name)
print('G350 runtime profile configured:',profile)

write('/opt/system/351Files.sh','#!/usr/bin/env bash\nexec bash /opt/darkos-qemu/351files.sh\n',0o755)
