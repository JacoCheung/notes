"""Draw TorchRec's lengths tensors and split sizes into the key-flow SVG and
animate them with the keys.

usage: animate_lengths.py <source svg> <output svg> <dir holding keyflow_example.py>

The source animation lasts 18 s (Bucketize 0-5.2, AllToAll 5.2-13, Recat 13-16.5).
AllToAll is stretched by EXTEND seconds to fit the splits exchange and the buffer
allocation, so everything after it moves later by the same amount.
  * Send lengths count up while keys land; the send splits appear once every key is in place.
  * AllToAll runs as three calls: the splits entries fly and the receive buffers are
    allocated from them, then the lengths cells fly, then the keys.
  * Recat moves lengths cells and keys together.
"""
import importlib.util
import re
import sys
from pathlib import Path

source, output, module_dir = map(Path, sys.argv[1:4])
spec = importlib.util.spec_from_file_location('keyflow_example', module_dir / 'keyflow_example.py')
example = importlib.util.module_from_spec(spec)
sys.modules['keyflow_example'] = example
spec.loader.exec_module(example)
data = example.simulate()
lengths = data['lengths']
splits = {
    'send': {'values': data['send_splits'], 'lengths': data['lengths_splits']['send']},
    'recv': {'values': data['recv_splits'], 'lengths': data['lengths_splits']['recv']},
}
P, F = example.WORLD_SIZE, len(example.FEATURES)

svg = source.read_text()


def swap(old, new, count=1):
    global svg
    assert svg.count(old) == count, (old[:80], svg.count(old))
    svg = svg.replace(old, new)


def sub(pattern, replacement, count, flags=0):
    global svg
    svg, found = re.subn(pattern, replacement, svg, flags=flags)
    assert found == count, (pattern, found)


SOURCE_DURATION, STEP = 18.0, 0.05
EXTEND = 1.2                       # extra seconds inside the AllToAll step
DURATION = SOURCE_DURATION + EXTEND
PHASES = (0, 5.2, 13 + EXTEND, 16.5 + EXTEND)
OVERVIEW_FADE = (16 + EXTEND, 16.5 + EXTEND)
HEIGHT = 1010
BAND, TOP, ROW = 180, 230, 34
SIZE, PITCH = 22, 24
COLUMNS = {'send': (594, 656, 774), 'recv': (1192, 1254, 1372)}  # label, values, lengths
STRIPS = {'input': 148, 'lookup': 1650}

SEND_SPLITS_FADE = (4.4, 4.8)       # after the last key lands at 4.2
RECV_SPLITS_FADE = (5.25, 5.55)    # empty receive brackets open as AllToAll starts
SPLITS_FLIGHT = (5.3, 0.1, 1.6)     # call 1: start, gap between the two entries on a route, duration
RECV_ALLOC_FADE = (7.05, 7.65)      # receive buffers appear once the splits are in
LENGTHS_FLIGHT = (7.75, 0.08, 0.85)  # call 2
VALUES_SHIFT = (2.05, 1.65, 1.3, .9)  # call 3: delay of each destination wave, on top of EXTEND
TICK = 0.12                         # spacing of counter ticks before a wave lands


def row_y(rank, row):
    return TOP + BAND * rank + 22 + ROW * row


def send_pos(rank, row, feature):
    return COLUMNS['send'][2] + PITCH * feature, row_y(rank, row)


def recv_pos(rank, row, feature):
    return COLUMNS['recv'][2] + PITCH * feature, row_y(rank, row)


def strip_pos(stage, rank, index, per_feature):
    return (STRIPS[stage] + 58 + PITCH * index + (8 if index >= per_feature else 0),
            TOP + BAND * rank + 123)


def digit(value, attrs='', track=''):
    return (f'<text x="{SIZE / 2:g}" y="{SIZE / 2 + .5:g}" class="len-digit" text-anchor="middle" '
            f'dominant-baseline="middle"{attrs}>{value}{track}</text>')


def static_cell(pos, feature, value):
    return (f'<g transform="translate({pos[0]} {pos[1]})"><rect width="{SIZE}" height="{SIZE}" rx="3" '
            f'class="len-{"ab"[feature]}"/>{digit(value)}</g>')


def slot(pos):
    return f'<rect x="{pos[0]}" y="{pos[1]}" width="{SIZE}" height="{SIZE}" rx="3" class="len-slot"/>'


def bracketed(values):
    return '[' + ' '.join(map(str, values)) + ']'


def key_time(t):
    return f'{t / DURATION:.7f}'.rstrip('0').rstrip('.') if t else '0'


# --- 1. Read the key tracks: when each wave lands, leaves and regroups ------
KEY = re.compile(r'(<g data-moving-key="(\d):(\d):(\d+)" data-src="\d" data-dst="(\d)" class="moving-key">.*?'
                 r'<animateTransform [^>]*?values=")([^"]+)(")', re.S)


def segments(points):
    found, i = [], 0
    while i < len(points) - 1:
        if points[i + 1] != points[i]:
            j = i
            while j < len(points) - 1 and points[j + 1] != points[j]:
                j += 1
            found.append((i, j))
            i = j
        else:
            i += 1
    return found


landed = {}   # (src, dst, feature) -> time the wave reaches the send buffer
regroup = {}  # feature -> (start, end) of the recat move


def retime(match):
    src, feature, dst = int(match[2]), int(match[3]), int(match[5])
    points = match[6].split(';')
    assert len(points) == round(SOURCE_DURATION / STEP) + 1
    moves = segments(points)
    assert len(moves) == 3, moves
    landed[src, dst, feature] = round(moves[0][1] * STEP, 2)
    start, end = (round(i * STEP + EXTEND, 2) for i in moves[2])
    low, high = regroup.get(feature, (start, end))
    regroup[feature] = (min(low, start), max(high, end))
    a, b = moves[1]
    shift, extend = round(VALUES_SHIFT[dst] / STEP), round(EXTEND / STEP)
    assert all(point == points[b] for point in points[b + 1:b + 1 + shift])
    # Keys leave only after the lengths cells for the same destination have arrived.
    assert (b + shift) * STEP + EXTEND < PHASES[2]
    assert a * STEP + VALUES_SHIFT[dst] + EXTEND >= LENGTHS_FLIGHT[0] + dst * LENGTHS_FLIGHT[1] + LENGTHS_FLIGHT[2]
    assert RECV_ALLOC_FADE[0] >= SPLITS_FLIGHT[0] + SPLITS_FLIGHT[1] + SPLITS_FLIGHT[2]
    assert LENGTHS_FLIGHT[0] >= RECV_ALLOC_FADE[1]
    points = points[:a] + [points[a]] * (shift + extend) + points[a:b + 1] + points[b + 1 + shift:]
    assert len(points) == round(DURATION / STEP) + 1
    return match[1] + ';'.join(points) + match[7]


sub(KEY, retime, 40)

# --- 1b. Stage markers and the closing overview on the stretched timeline ----
swap('keyTimes="0;0.2888889;0.7222222;0.9166667;1"',
     'keyTimes="' + ';'.join(key_time(t) for t in PHASES) + ';1"', 4)
sub(r'(<g class="motion-overview" opacity="0"><animate attributeName="opacity" values=")[^"]+(" dur="18s")',
    lambda m: f'{m[1]}0;0;1;1" keyTimes="0;{key_time(OVERVIEW_FADE[0])};{key_time(OVERVIEW_FADE[1])};1{m[2]}', 1)

# --- 2. Header, legend wording, description, styles -------------------------
swap('<rect class="nav-mark" data-mark="step:1" x="900" y="127" width="230" height="74" rx="10"',
     '<rect class="nav-mark" data-mark="step:1" x="900" y="127" width="230" height="93" rx="10"')
swap('send[src][dst] → recv[dst][src]</text><rect class="nav-hit" x="900" y="127" width="230" height="74" rx="10">',
     'send[src][dst] → recv[dst][src]</text><text x="1015" y="201" class="layout" text-anchor="middle">'
     '3 calls: splits, lengths, values</text><rect class="nav-hit" x="900" y="127" width="230" height="93" rx="10">')
swap('>Cell number = owner rank, not key ID<', '>Filled cell number = owner rank, not key ID<')
swap('All 40 keys are conserved.',
     'All 40 keys are conserved. Outlined cells are the lengths tensor: one key count per rank segment and '
     'feature. The counts rise as keys land in the send buffer, and the send splits appear once they are '
     'complete. AllToAll then runs as three calls: every splits entry travels to its peer, the receiver '
     'allocates its buffers from them, the lengths cells follow, and the keys go last. The final permutation moves lengths cells together with the keys.')
swap('.offset{font-size:12px;fill:#687581;font-family:monospace}',
     '.meta{font-size:12px;fill:#687581;font-family:monospace}'
     '.len-a{fill:#fdeee2;stroke:#eaa06c;stroke-width:1}.len-b{fill:#e3f3f7;stroke:#5fb3c8;stroke-width:1}'
     '.len-slot{fill:#f6f8fa;stroke:#e1e6eb;stroke-width:.8}'
     '.len-digit{font-size:14px;font-family:Arial,sans-serif;font-weight:500}'
     '.split-digit{font-size:12px;font-family:monospace;fill:#46525e}')

# --- 3. Remove slice labels, captions and the footer notes; trim the canvas --
sub(r'<text x="(?:774|1372)" y="\d+" class="offset" dominant-baseline="middle">\[\d+:\d+\]</text>', '', 32)
sub(r'<text x="(?:594|1192)" y="\d+" class="count">one flat tensor · rows show rank segments</text>', '', 8)
sub(r'<text x="(148|1650)" y="(\d+)" class="count">',
    lambda m: f'<text x="{m[1]}" y="{int(m[2]) + 26}" class="count">', 8)
sub(r'<text x="40" y="(?:992|1025)" class="note">[^<]*</text>', '', 2)
swap('<text x="2030" y="992" class="note" text-anchor="end">40 keys → 40 keys</text>', '')
swap('<text x="2030" y="1025" class="note" text-anchor="end">Dashed route = same-rank segment</text>',
     '<text x="2030" y="986" class="note" text-anchor="end">Dashed route = same-rank segment · 40 keys → 40 keys</text>')
swap('width="2070" height="1070" viewBox="0 0 2070 1070"', f'width="2070" height="{HEIGHT}" viewBox="0 0 2070 {HEIGHT}"')
swap('<rect x="0" y="0" width="2070" height="1070"', f'<rect x="0" y="0" width="2070" height="{HEIGHT}"')

# --- 3b. Receive buffers exist only after the splits arrive ------------------
allocated = []


def take(pattern, count=None):
    global svg
    found = re.findall(pattern, svg)
    assert found and count in (None, len(found)), (pattern, len(found))
    svg = re.sub(pattern, '', svg)
    allocated.extend(found)
    return len(found)


take(r'<rect x="(?:1254|1280|1306|1332)" y="\d+" width="26" height="30" class="motion-slot"/>', 40)
take(r'<rect x="1254" y="\d+" width="\d+" height="30" class="buffer-edge"></rect>', 16)
dividers = take(r'<line x1="(?:1280|1306|1332)" y1="\d+" x2="\d+" y2="\d+" class="feature-divider"></line>')
take(r'<path d="M1244 \d+h-7v132h7" class="bracket"></path>', 4)

# --- 4. Static frame: labels, empty slots, input lengths ---------------------
static = []
for rank in range(P):
    top = TOP + BAND * rank
    for stage, (label_x, values_x, lengths_x) in COLUMNS.items():
        static.append(f'<text x="{values_x}" y="{top + 13}" class="meta">values</text>'
                      f'<text x="{lengths_x}" y="{top + 13}" class="meta">lengths</text>'
                      f'<text x="{label_x}" y="{top + 170}" class="meta">splits</text>')
        position, target = (send_pos, static) if stage == 'send' else (recv_pos, allocated)
        target.append(''.join(slot(position(rank, row, feature)) for row in range(P) for feature in range(F)))
    static.append(f'<text x="{STRIPS["input"]}" y="{top + 138}" class="meta">lengths</text>'
                  f'<g class="lengths" data-lengths="input:{rank}">'
                  + ''.join(static_cell(strip_pos('input', rank, feature, 1), feature, value)
                            for feature, value in enumerate(lengths['input'][rank])) + '</g>')
    static.append(f'<text x="{STRIPS["lookup"]}" y="{top + 138}" class="meta">lengths</text>'
                  + ''.join(slot(strip_pos('lookup', rank, index, P)) for index in range(P * F)))

# --- 5. Splits rows fade in when they are computed or received ---------------
def splits_y(rank):
    return TOP + BAND * rank + 170


def entry_x(base, index):
    return base + 15 + 14 * index


def brackets(base, y):
    return (f'<text x="{base + 4}" y="{y}" class="meta" text-anchor="middle">[</text>'
            f'<text x="{base + 15 + 14 * P - 3}" y="{y}" class="meta" text-anchor="middle">]</text>')


def splits_group(stage, fade, with_entries):
    rows = ''
    for rank in range(P):
        for name, base in zip(('values', 'lengths'), COLUMNS[stage][1:]):
            entries = ''.join(
                f'<text x="{entry_x(base, index)}" y="{splits_y(rank)}" class="split-digit" text-anchor="middle">{value}</text>'
                for index, value in enumerate(splits[stage][name][rank])) if with_entries else ''
            assert all(value < 10 for value in splits[stage][name][rank])
            rows += f'<g data-splits="{stage}:{rank}:{name}">{brackets(base, splits_y(rank))}{entries}</g>' if with_entries                 else brackets(base, splits_y(rank))
    return (f'<g class="splits" data-splits-row="{stage}" opacity="0"><animate attributeName="opacity" '
            f'values="0;0;1;1" keyTimes="0;{key_time(fade[0])};{key_time(fade[1])};1" dur="18s" '
            f'repeatCount="indefinite" calcMode="linear"/>{rows}</g>')


static.insert(0, '<g class="recv-alloc" data-alloc="recv" opacity="0"><animate attributeName="opacity" '
              f'values="0;0;1;1" keyTimes="0;{key_time(RECV_ALLOC_FADE[0])};{key_time(RECV_ALLOC_FADE[1])};1" '
              'dur="18s" repeatCount="indefinite" calcMode="linear"/>' + ''.join(allocated) + '</g>')
static.append(splits_group('send', SEND_SPLITS_FADE, True))
static.append(splits_group('recv', RECV_SPLITS_FADE, False))
swap('<g class="motion-trails">', ''.join(static) + '<g class="motion-trails">')

# --- 6. Closing overview: lengths copies in the send and receive columns -----
copies = []
for stage, position in (('send', send_pos), ('recv', recv_pos)):
    for rank in range(P):
        copies.append(f'<g class="lengths" data-lengths="{stage}:{rank}">' + ''.join(
            static_cell(position(rank, row, feature), feature, lengths[stage][rank][row * F + feature])
            for row in range(P) for feature in range(F)) + '</g>')

# --- 7. The 32 travelling lengths cells --------------------------------------
def ease(x):
    return x * x * (3 - 2 * x)


def flight(start, end, t0, t1):
    """Keyframes of an S-shaped move with horizontal tangents."""
    (x0, y0), (x1, y1) = start, end
    reach = (x1 - x0) / 2
    frames, steps = [], max(2, round((t1 - t0) / STEP))
    for i in range(steps + 1):
        u = ease(i / steps)
        a, b, c, d = (1 - u) ** 3, 3 * (1 - u) ** 2 * u, 3 * (1 - u) * u ** 2, u ** 3
        frames.append((t0 + (t1 - t0) * i / steps,
                       a * x0 + b * (x0 + reach) + c * (x1 - reach) + d * x1,
                       a * y0 + b * y0 + c * y1 + d * y1))
    return frames


def wire(src, dst, samples=48):
    """Points on the drawn AllToAll route from a send row to a receive row."""
    y0, y1 = TOP + BAND * src + 33 + ROW * dst, TOP + BAND * dst + 33 + ROW * src
    assert f'd="M852 {y0} C965 {y0} 1058 {y1} 1178 {y1}"' in svg, (src, dst)
    points = []
    for i in range(samples + 1):
        u = i / samples
        a, b, c, d = (1 - u) ** 3, 3 * (1 - u) ** 2 * u, 3 * (1 - u) * u ** 2, u ** 3
        points.append((a * 852 + b * 965 + c * 1058 + d * 1178, a * y0 + b * y0 + c * y1 + d * y1))
    return points


def along(points, t0, t1):
    """Keyframes of an eased move along a polyline, paced by distance."""
    marks = [0.0]
    for (xa, ya), (xb, yb) in zip(points, points[1:]):
        marks.append(marks[-1] + ((xb - xa) ** 2 + (yb - ya) ** 2) ** .5)
    frames, steps, segment = [], max(2, round((t1 - t0) / STEP)), 0
    for i in range(steps + 1):
        reach = ease(i / steps) * marks[-1]
        while segment < len(points) - 2 and marks[segment + 1] < reach:
            segment += 1
        span = marks[segment + 1] - marks[segment]
        part = (reach - marks[segment]) / span if span else 0
        (xa, ya), (xb, yb) = points[segment], points[segment + 1]
        frames.append((t0 + (t1 - t0) * i / steps, xa + part * (xb - xa), ya + part * (yb - ya)))
    return frames


def opacity_track(values, times):
    return (f'<animate attributeName="opacity" values="{";".join(map(str, values))}" '
            f'keyTimes="{";".join(key_time(t) for t in times)}" calcMode="discrete" dur="18s" '
            f'repeatCount="indefinite"/>')


# Call 1: a copy of every send splits entry travels to its peer, where the
# copies line up as that rank's receive splits. The two entries for a peer
# ride its route in single file, lengths count first as in the packed tensor.
entries = []
for src in range(P):
    for dst in range(P):
        # A digit's anchor is its baseline; 4 px below the line centres it on the route.
        route = [(x, y + 4) for x, y in wire(src, dst)]
        for order, (name, send_base, recv_base) in enumerate(reversed(list(zip(('values', 'lengths'), COLUMNS['send'][1:], COLUMNS['recv'][1:])))):
            p0, p1 = (entry_x(send_base, dst), splits_y(src)), (entry_x(recv_base, src), splits_y(dst))
            t0 = SPLITS_FLIGHT[0] + SPLITS_FLIGHT[1] * order
            frames = [(0, *p0)] + along([p0] + route + [p1], t0, t0 + SPLITS_FLIGHT[2]) + [(DURATION, *p1)]
            value = splits['send'][name][src][dst]
            assert value == splits['recv'][name][dst][src]
            entries.append(
                f'<g data-split="{src}:{dst}:{name}" transform="translate({p0[0]} {p0[1]})">'
                f'<animateTransform attributeName="transform" type="translate" '
                f'values="{";".join(f"{x:.2f},{y:.2f}" for _, x, y in frames)}" '
                f'keyTimes="{";".join(key_time(t) for t, _, _ in frames)}" dur="18s" '
                f'repeatCount="indefinite" calcMode="linear"/>'
                f'<text class="split-digit" text-anchor="middle">{value}</text></g>')
splits_flight = ('<g class="splits-flight" opacity="0"><animate attributeName="opacity" values="0;1;0" '
                 f'keyTimes="0;{key_time(SPLITS_FLIGHT[0])};1" calcMode="discrete" dur="18s" '
                 f'repeatCount="indefinite"/>' + ''.join(entries) + '</g>')

cells, digit_tracks = [], 0
for src in range(P):
    for dst in range(P):
        for feature in range(F):
            count = lengths['send'][src][dst * F + feature]
            assert count == lengths['recv'][dst][src * F + feature] == lengths['lookup'][dst][feature * P + src]
            p0, p1, p2 = send_pos(src, dst, feature), recv_pos(dst, src, feature), strip_pos('lookup', dst, feature * P + src, P)
            t0 = LENGTHS_FLIGHT[0] + LENGTHS_FLIGHT[1] * dst
            # The pair of cells for one segment rides the route as a unit, centred on the line.
            offset = (PITCH * feature - (PITCH + SIZE) / 2, -SIZE / 2)
            centres = [(p0[0] - offset[0], p0[1] - offset[1])] + wire(src, dst) + [(p1[0] - offset[0], p1[1] - offset[1])]
            ride = [(t, x + offset[0], y + offset[1]) for t, x, y in along(centres, t0, t0 + LENGTHS_FLIGHT[2])]
            assert all(abs(a - b) < 1e-6 for a, b in zip(ride[0][1:] + ride[-1][1:], p0 + p1))
            frames = [(0, *p0)] + ride + flight(p1, p2, *regroup[feature]) + [(DURATION, *p2)]
            assert all(a[0] <= b[0] for a, b in zip(frames, frames[1:]))
            track = (f'<animateTransform attributeName="transform" type="translate" '
                     f'values="{";".join(f"{x:.2f},{y:.2f}" for _, x, y in frames)}" '
                     f'keyTimes="{";".join(key_time(t) for t, _, _ in frames)}" dur="18s" '
                     f'repeatCount="indefinite" calcMode="linear"/>')
            if count == 0:
                digits = digit(0)
            else:
                assert (src, dst, feature) in landed
                ticks = [round(landed[src, dst, feature] - TICK * (count - 1 - i), 2) for i in range(count)]
                digits = digit(0, track=opacity_track([1, 0, 1], [0, ticks[0], DURATION]))
                for value in range(1, count + 1):
                    shown = [0, ticks[value - 1]] + ([ticks[value]] if value < count else []) + [DURATION]
                    states = [0, 1] + ([0] if value < count else []) + [0]
                    digits += digit(value, ' opacity="0"', opacity_track(states, shown))
                digit_tracks += count + 1
            # The transform track comes first so track order matches element order.
            cells.append(f'<g data-len="{src}:{dst}:{feature}" class="moving-len" transform="translate({p0[0]} {p0[1]})">'
                         f'{track}<rect width="{SIZE}" height="{SIZE}" rx="3" class="len-{"ab"[feature]}"/>{digits}</g>')

swap('</g><g class="motion-cells">', ''.join(copies) + '</g>' + splits_flight + '<g class="motion-lengths">' + ''.join(cells) + '</g><g class="motion-cells">')

tracks = len(re.findall(r'<animate(?:Transform)? ', svg))
swap('dur="18s"', f'dur="{DURATION:g}s"', tracks)
# The player checks this count: 40 key paths, 32 lengths cells with 69 counter digits, 32 splits
# entries and their reveal, 4 stage markers, 2 splits rows, the receive buffers and the overview.
swap('<svg id="keyflow-motion-svg" ', f'<svg id="keyflow-motion-svg" data-tracks="{tracks}" ')
output.write_text(svg)
tracks = len(re.findall(r'<animate(?:Transform)? ', svg))
print(f'{output.name}: {len(svg)} bytes, {tracks} tracks ({digit_tracks} counter digits)')
print('landed', sorted(set(landed.values())), 'regroup', regroup, 'recv dividers', dividers)
