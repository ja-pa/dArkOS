"""Plan G350 overlay growth against its inspected immutable release layout."""
import copy
import json
import sys

def plan(current, baseline, sectors):
    current, baseline = current['partitiontable'], baseline['partitiontable']
    parts, original = current['partitions'], baseline['partitions']
    if current['label'] != 'dos' or baseline['label'] != 'dos' or current['id'] != baseline['id'] or len(parts) != 3 or len(original) != 3:
        raise ValueError('Overlay partition identity differs from the inspected base image')
    if any(any(a.get(k) != b.get(k) for k in ('start', 'size', 'type')) for a, b in zip(parts, original)):
        raise ValueError('Overlay layout differs from the inspected base image')
    if not (parts[0]['start'] == 32768 and parts[0]['type'] == 'c' and parts[1]['start'] == 237568 and parts[1]['type'] == '83' and parts[2]['type'] == 'c' and parts[2]['size'] == 614400):
        raise ValueError('Unsupported G350 layout; refusing partition changes')
    parts = copy.deepcopy(parts)
    start = (sectors - parts[2]['size']) // 2048 * 2048
    if start <= parts[2]['start']:
        raise ValueError('Overlay must grow before moving EASYROMS')
    parts[1]['size'] = start - parts[1]['start']
    parts[2]['start'] = start
    text = 'label: dos\nlabel-id: ' + current['id'] + '\nunit: sectors\n\n'
    for part in parts:
        text += 'start={}, size={}, type={}{}\n'.format(part['start'], part['size'], part['type'], ', bootable' if part.get('bootable') else '')
    return text

if __name__ == '__main__':
    with open(sys.argv[1]) as stream:
        current = json.load(stream)
    with open(sys.argv[2]) as stream:
        baseline = json.load(stream)
    print(plan(current, baseline, int(sys.argv[3])), end='')
