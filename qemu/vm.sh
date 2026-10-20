#!/usr/bin/env bash
source "$(dirname "$0")/lib.sh"
source "$QEMU_DIR/scripts/workflow-common.sh"
controls() { python3 "$QEMU_DIR/scripts/controls-window.py" "$1" "$WORK_DIR" || true; }
case ${1:-help} in
 start) vm start "${2:-gtk-gl}";;
 stop) vm stop; controls stop;;
 status|check) vm "$@";;
 controls) controls start;;
 ssh) vm verify; shift; remote "$@";;
 es)
  vm start gtk-gl
  remote 'if pidof emulationstation retroarch >/dev/null; then echo "Quit existing graphical application first" >&2; exit 1; fi; cd /opt/darkos-es && sudo -n bash /opt/darkos-qemu/env.sh ./emulationstation --home /home/ark --debug --no-splash'
  ;;
 diagnose) vm verify; remote sudo -n bash -s < "$QEMU_DIR/scripts/graphics-diagnose.sh" | tee "$WORK_DIR/logs/graphics-diagnose.log";;
 logs) tail -n 100 "$WORK_DIR/logs/workflow/serial.log";;
 export) vm check; python3 "$QEMU_DIR/bundle.py" export-runtime "$2";;
 *) echo 'Usage: qemu/vm.sh start [gtk-gl|serial]|stop|status|ssh [command]|es|logs|check|export <directory>'; exit 2;;
esac
