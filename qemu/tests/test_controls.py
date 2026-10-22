"""Host legend: process safety, optional GUI failure and real Tk profile rendering."""
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

SCRIPT = Path(__file__).resolve().parents[1] / 'scripts/controls-window.py'
spec = importlib.util.spec_from_file_location('controls', SCRIPT)
controls = importlib.util.module_from_spec(spec)
spec.loader.exec_module(controls)


class ControlsTests(unittest.TestCase):
    def test_stale_pid_cannot_target_current_process(self):
        with tempfile.TemporaryDirectory() as folder:
            work = Path(folder)
            state = work / 'controls.json'
            state.write_text(json.dumps({'pid': os.getpid(), 'started': 'wrong'}))
            self.assertIsNone(controls.window_pid(state, work))
            started = Path(f'/proc/{os.getpid()}/stat').read_text().rsplit(')', 1)[1].split()[19]
            state.write_text(json.dumps({'pid': os.getpid(), 'started': started}))
            self.assertIsNone(controls.window_pid(state, work))

    def test_unavailable_display_is_optional(self):
        with tempfile.TemporaryDirectory() as folder:
            env = dict(os.environ, DISPLAY=':9876', WAYLAND_DISPLAY='missing')
            result = subprocess.run([sys.executable, str(SCRIPT), 'start', folder],
                                    env=env, capture_output=True, text=True, timeout=10)
            self.assertEqual(result.returncode, 0)
            self.assertIn('controls window unavailable', result.stderr)
            self.assertFalse((Path(folder) / 'state/controls.json').exists())

    @unittest.skipUnless(os.environ.get('DISPLAY'), 'Requires WSLg or X11')
    def test_real_tk_profiles_resize_and_cleanup(self):
        settings = json.loads(controls.CONFIG.read_text())

        def verify(root):
            try:
                self.assertEqual(root.cget('cursor'), '')
                canvas = root.diagram
                self.assertIsInstance(canvas, controls.ControlsDiagram)
                self.assertEqual(canvas.cget('cursor'), '')
                for geometry in ['980x720', '1120x920', '1400x1000']:
                    root.geometry(geometry)
                    root.update()
                    image = canvas.template_image
                    items = canvas.find_all()
                    self.assertEqual(len(items), 25)
                    self.assertEqual(sum(canvas.type(i) == 'image' for i in items), 1)
                    self.assertEqual(sum(canvas.type(i) == 'text' for i in items), 24)
                    for index, profile in enumerate(settings['profiles']):
                        root.profile.current(index)
                        root.profile.event_generate('<<ComboboxSelected>>')
                        root.update()
                        self.assertIs(canvas.template_image, image)
                        self.assertEqual(canvas.find_all(), items)
                        self.assertEqual(root.note.cget('text'), profile['note'])
                        self.assertEqual([w.cget('text') for w in root.rows.winfo_children()],
                                         [text for row in profile['controls'] for text in row])
                        width, height = canvas.template_size
                        sx, sy = width/canvas.template.width, height/canvas.template.height
                        ox, oy = (canvas.winfo_width()-width)/2, (canvas.winfo_height()-height)/2
                        for box, field, item in canvas.entries:
                            expected = (box['label'] if field['source'] == 'label' else
                                        profile['diagram'].get(box['key'], settings['diagram']['missing_key']))
                            self.assertEqual(canvas.itemcget(item, 'text'), expected)
                            x1, y1, x2, y2 = box['box']
                            bx1, by1, bx2, by2 = canvas.bbox(item)
                            self.assertGreaterEqual(bx1, ox+x1*sx)
                            self.assertLessEqual(bx2, ox+x2*sx)
                            self.assertGreaterEqual(by1, oy+y1*sy)
                            self.assertLessEqual(by2, oy+y2*sy)
            finally:
                root.destroy()

        with tempfile.TemporaryDirectory() as folder:
            work = Path(folder)
            (work / 'state').mkdir()
            state = work / 'state/controls.json'
            with patch.object(controls.ControlsWindow, 'mainloop', verify):
                controls.show(work, state)
            self.assertFalse(state.exists())

    @unittest.skipUnless(os.environ.get('DISPLAY'), 'Requires WSLg or X11')
    def test_diagram_respects_custom_field_styles_and_missing_key(self):
        settings = json.loads(controls.CONFIG.read_text())
        diagram = settings['diagram']
        diagram['boxes'] = [{
            'key': 'custom', 'label': 'Custom label', 'box': [100, 100, 400, 200],
            'styles': {'mapping': {'position': [.4, .7],
                                  'font': ['sans', 26, 'normal'], 'color': '#123456'}}
        }]
        root = controls.tk.Tk()
        try:
            canvas = controls.ControlsDiagram(root, diagram, controls.CONFIG.parent)
            canvas.configure(width=627, height=627)
            canvas.pack()
            root.update()
            canvas.set_mapping({'custom': 'Test'})
            item = canvas.entries[1][2]
            self.assertEqual(canvas.coords(item), [110.0, 85.0])
            self.assertEqual(canvas.itemcget(item, 'text'), 'Test')
            self.assertEqual(canvas.itemcget(item, 'font'), 'sans -13 normal')
            self.assertEqual(canvas.itemcget(item, 'fill'), '#123456')
            canvas.set_mapping({})
            self.assertEqual(canvas.itemcget(item, 'text'), diagram['missing_key'])
        finally:
            root.destroy()


if __name__ == '__main__':
    unittest.main()
