"""Optional host-side control legend; no guest connections or input injection."""
import argparse
import fcntl
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time
import tkinter as tk
from tkinter import ttk
from tkinter.font import Font

from PIL import Image, ImageTk

SCRIPT = Path(__file__).resolve()
CONFIG = SCRIPT.parents[1] / 'config/controls.json'


class ControlsDiagram(tk.Canvas):
    """Static background and configurable text, scaled together on resize."""

    def __init__(self, parent, settings, config_dir):
        super().__init__(parent, name='diagram', background=settings['background'],
                         highlightthickness=0)
        self.settings = settings
        self.mapping = {}
        with Image.open(config_dir / settings['image']) as image:
            self.template = image.convert('RGB')
        self.template_image = None
        self.template_size = None
        self.background = self.create_image(0, 0, anchor='nw')
        self.entries = [
            (box, field, self.create_text(0, 0, fill=field['color']))
            for box in settings['boxes'] for field in settings['fields']
        ]
        self.measure_font = Font(root=self)
        self.bind('<Configure>', self.redraw)

    def set_mapping(self, mapping):
        self.mapping = mapping
        self.redraw()

    def redraw(self, _event=None):
        scale = min(self.winfo_width() / self.template.width,
                    self.winfo_height() / self.template.height)
        size = tuple(max(1, round(dimension * scale)) for dimension in self.template.size)
        ox = (self.winfo_width() - size[0]) / 2
        oy = (self.winfo_height() - size[1]) / 2
        sx, sy = size[0] / self.template.width, size[1] / self.template.height
        if size != self.template_size:
            self.template_image = ImageTk.PhotoImage(
                self.template.resize(size, Image.Resampling.LANCZOS), master=self)
            self.itemconfigure(self.background, image=self.template_image)
            self.template_size = size
        self.coords(self.background, ox, oy)
        for box, field, item in self.entries:
            self._draw_text(box, field, item, ox, oy, sx, sy)

    def _draw_text(self, box, field, item, ox, oy, sx, sy):
        style = field | box.get('styles', {}).get(field['source'], {})
        x1, y1, x2, y2 = box['box']
        px, py = style['position']
        self.coords(item, ox + (x1 + (x2-x1)*px)*sx,
                    oy + (y1 + (y2-y1)*py)*sy)
        text = (box['label'] if field['source'] == 'label'
                else self.mapping.get(box['key'], self.settings['missing_key']))
        available = 2*min(px, 1-px)*(x2-x1)*sx - 2*self.settings['text_padding']*sx
        font = self._fit_font(text, style['font'], sy, available)
        self.itemconfigure(item, text=text, fill=style['color'], font=font)

    def _fit_font(self, text, specification, scale, available):
        family, base_size, weight = specification
        pixels = max(1, round(base_size * scale))
        self.measure_font.configure(family=family, size=-pixels, weight=weight)
        while pixels > 1 and self.measure_font.measure(text) > available:
            pixels -= 1
            self.measure_font.configure(size=-pixels)
        return family, -pixels, weight


class ControlsWindow(tk.Tk):
    """Profile selection, control diagram and sidebar; no process management."""

    def __init__(self, settings, config_dir):
        super().__init__()
        self.settings = settings
        self.ui = settings['ui']
        self.profiles = settings['profiles']
        try:
            self._configure_window(settings['window'])
            self._build_interface(config_dir)
            self.profile.current(0)
            self.select_profile()
        except Exception:
            self.destroy()
            raise

    def _configure_window(self, settings):
        self.title(settings['title'])
        self.attributes('-type', 'normal')
        width, height = settings['size']
        self.geometry(f'{min(width, self.winfo_screenwidth()-60)}x'
                      f'{min(height, self.winfo_screenheight()-90)}+40+40')
        self.minsize(*settings['minimum_size'])

    def _build_interface(self, config_dir):
        outer = ttk.Frame(self, padding=16)
        outer.pack(fill='both', expand=True)
        ttk.Label(outer, **self.ui['heading']).pack(anchor='w')
        ttk.Label(outer, **self.ui['subtitle']).pack(anchor='w', pady=(4, 8))
        self.profile = ttk.Combobox(outer, values=[p['name'] for p in self.profiles],
                                   state='readonly')
        self.profile.pack(fill='x', pady=(0, 10))
        self.profile.bind('<<ComboboxSelected>>', self.select_profile)
        body = ttk.Frame(outer)
        body.pack(fill='both', expand=True)
        self.diagram = ControlsDiagram(body, self.settings['diagram'], config_dir)
        self.diagram.pack(side='left', fill='both', expand=True)
        self._build_sidebar(body)

    def _build_sidebar(self, parent):
        side = ttk.Frame(parent, padding=(16, 0, 0, 0))
        side.pack(side='right', fill='y')
        ttk.Label(side, **self.ui['sidebar_heading']).pack(anchor='w', pady=(4, 12))
        self.rows = ttk.Frame(side, name='rows')
        self.rows.pack(fill='x')
        self.note = ttk.Label(side, wraplength=self.ui['sidebar_width'], justify='left')
        self.note.pack(fill='x', pady=(20, 0))
        for text in self.ui['help']:
            ttk.Label(side, text=text, wraplength=self.ui['sidebar_width'],
                      justify='left').pack(anchor='w', pady=(20, 0))

    def select_profile(self, _event=None):
        current = self.profiles[self.profile.current()]
        self._update_controls(current['controls'])
        self.note.configure(text=current['note'])
        self.diagram.set_mapping(current['diagram'])

    def _update_controls(self, controls):
        for child in self.rows.winfo_children():
            child.destroy()
        for row, (action, key) in enumerate(controls):
            ttk.Label(self.rows, text=action, wraplength=self.ui['action_width']).grid(
                row=row, column=0, sticky='w', pady=6)
            ttk.Label(self.rows, text=key, font=self.ui['key_font'],
                      wraplength=self.ui['key_width']).grid(
                row=row, column=1, sticky='e', padx=(10, 0), pady=6)


def window_pid(state, work):
    """Never signal an unrelated process when a PID file outlives its window."""
    try:
        saved = json.loads(state.read_text())
        proc = Path('/proc') / str(saved['pid'])
        args = (proc / 'cmdline').read_bytes().split(b'\0')
        started = (proc / 'stat').read_text().rsplit(')', 1)[1].split()[19]
        if (started == saved['started'] and str(SCRIPT).encode() in args
                and b'show' in args and str(work).encode() in args):
            return saved['pid']
    except (OSError, ValueError, KeyError, IndexError):
        pass
    return None


def show(work, state):
    """Own the single-instance lock, signal handling and PID state."""
    with (work / 'state/controls.lock').open('w') as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return
        settings = json.loads(CONFIG.read_text(encoding='utf-8'))
        window = ControlsWindow(settings, CONFIG.parent)
        previous_handler = signal.signal(signal.SIGTERM, lambda *_: window.destroy())

        def tick():
            # Wake Python to deliver SIGTERM; this does not redraw the window.
            window.after(200, tick)

        try:
            tick()
            window.update_idletasks()
            window.lift()
            pid = os.getpid()
            started = Path(f'/proc/{pid}/stat').read_text().rsplit(')', 1)[1].split()[19]
            state.write_text(json.dumps({'pid': pid, 'started': started}))
            window.mainloop()
        finally:
            signal.signal(signal.SIGTERM, previous_handler)
            state.unlink(missing_ok=True)
            try:
                window.destroy()
            except tk.TclError:
                pass  # Closing the window normally already destroyed it.


def stop_window(work, state):
    pid = window_pid(state, work)
    if pid:
        try:
            os.kill(pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
        for _ in range(20):
            if not window_pid(state, work):
                break
            time.sleep(0.1)


def start_window(work, state):
    if window_pid(state, work):
        return
    log = work / 'logs/workflow/controls.log'
    log.parent.mkdir(parents=True, exist_ok=True)
    with log.open('ab') as output:
        child = subprocess.Popen([sys.executable, str(SCRIPT), 'show', str(work)],
                                 stdin=subprocess.DEVNULL, stdout=output, stderr=output,
                                 start_new_session=True)
    for _ in range(30):
        if window_pid(state, work):
            return
        if child.poll() is not None:
            break
        time.sleep(0.1)
    print(f'Warning: controls window unavailable; install python3-tk python3-pil '
          f'python3-pil.imagetk and check WSLg. Log: {log}', file=sys.stderr)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['start', 'stop', 'show'])
    parser.add_argument('work', type=Path)
    args = parser.parse_args()
    work = args.work.resolve()
    (work / 'state').mkdir(parents=True, exist_ok=True)
    state = work / 'state/controls.json'
    actions = {'start': start_window, 'stop': stop_window, 'show': show}
    actions[args.action](work, state)


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        # Optional help must never prevent QEMU from starting.
        print(f'Warning: controls window: {error}', file=sys.stderr)
