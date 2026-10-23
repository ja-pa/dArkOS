"""Read-only binary version evidence; does not claim source provenance."""
import hashlib
import json
from pathlib import Path
import re
import sys

root, output = map(Path, sys.argv[1:])
rows = {}
for name, relative, pattern in [
    ('emulationstation', 'usr/bin/emulationstation/emulationstation', rb'2\.\d+\.\d+\.\d+ CHMOD'),
    ('retroarch', 'opt/retroarch/bin/retroarch', rb'(?<![\d.])1\.\d+\.\d+(?![\d.])'),
    ('351files', 'opt/351Files/351Files', rb'351Files[^\x00\r\n]{0,80}'),
    ('hardware_kernel', 'boot/Image', rb'Linux version [^\x00\r\n]{1,240}')]:
    path = root / relative
    if not path.is_file():
        rows[name] = {'path': '/' + relative, 'version': None, 'evidence': 'File absent'}
        continue
    data = path.read_bytes()
    matches = sorted(set(x.decode('ascii', errors='replace') for x in re.findall(pattern, data)))
    rows[name] = {'path': '/' + relative, 'sha256': hashlib.sha256(data).hexdigest(),
                  'matches': matches, 'version': matches[0] if len(matches) == 1 and name != '351files' else None,
                  'evidence': 'Embedded binary strings; source provenance unverified'}
output.write_text(json.dumps(rows, indent=2) + '\n')
print(json.dumps(rows, indent=2))
