#!/usr/bin/env python3
"""Draw and animate DynamicEmb's hierarchical input dist for the key-flow example.

Every number comes from the layout model next to the article's assets
(hier_input_dist_example.py). Run with python3.11; it rewrites
assets/torchrec/embedding-comm-viz/hier-input-dist.svg.

The animation has three steps (seconds, PHASES):
  1. Bucketize + push: inv fills in owner by owner while the keys stay put;
     then a copy of each key leaves the KJT for the own part or key_stage.
  2. GIN put: the count messages cross first and the rail layout follows from
     them; then each key_stage slice crosses in one put.
  3. Owner tables: the keys are copied into the owner's KJT and the row map
     is written.
A key cell that travels is a copy: its source cell stays where it is.
"""
import sys
from html import escape
from pathlib import Path

ASSETS = Path(__file__).resolve().parents[1] / 'assets/torchrec/embedding-comm-viz'
sys.path.insert(0, str(ASSETS))
import hier_input_dist_example as model  # noqa: E402

data = model.simulate()
P, F = model.NUM_NODES, model.NUM_FEATURES
WIDTH, TOP, BAND = 2150, 204, 236  # compact: the whole figure fits one screen at column width
HEIGHT = TOP + BAND * P + 16
KEY_W, KEY_H, META, PITCH = 26, 26, 22, 24
SLICE, LINE = 29, 14  # pitch of the slice rows and of the text lines
A_LABEL, A_CELLS = 128, 300
B_LABEL, B_TAG, B_CELLS = 640, 694, 808
ROUTE_FROM, ROUTE_BEND, ROUTE_TO = 924, 1010, 1342
D_LABEL, D_TAG, D_CELLS = 1350, 1406, 1520
E_LABEL, E_CELLS = 1680, 1796

DURATION, STEP = 20.0, 0.05
PHASES = (0, 7.2, 14.6, 18.6)
INV_FADE = (0.5, 0.55, 0.4)        # first owner block, stagger per owner, fade
OFFSETS_FADE = (2.7, 3.1)
OWN_PUSH = (3.4, 5.0)              # local store of the keys a rank owns
REMOTE_PUSH = (3.9, 0.45, 1.3)     # start, stagger per slice, duration
PROXY_FADE = (6.3, 6.7)            # chunk headers and the proxy's tables
MESSAGE_FADE = (7.4, 7.8)
TOKEN_SHOW, TOKEN_FLIGHT, TOKEN_HIDE = (7.9, 8.1), (8.1, 9.7), (9.9, 10.2)
LAYOUT_FADE = (9.8, 10.3)          # what the rail layout gives each owner
KEY_PUT = (10.6, 0.12, 2.0)        # start, stagger per owner, duration
REQUESTER_FADE = (13.4, 13.9)
KJT_COPY = ((14.9, 16.6), (15.7, 17.4))  # feature A, feature B
ROW_MAP_FADE = ((16.5, 16.9), (17.3, 17.7))
FINAL_FADE = (17.8, 18.2)

static, moving, tracks = [], [], 0


def top_of(rank):
    return TOP + BAND * rank


def slice_y(rank, row):
    return top_of(rank) + 44 + SLICE * row


def key_time(t):
    return f'{t / DURATION:.7f}'.rstrip('0').rstrip('.') if t else '0'


def text(x, y, value, cls='meta', anchor=None):
    extra = f' text-anchor="{anchor}"' if anchor else ''
    return f'<text x="{x}" y="{y}" class="{cls}"{extra}>{escape(str(value))}</text>'


def key_shape(key):
    return (f'<rect width="{KEY_W}" height="{KEY_H}" class="cell table-{"ab"[key.feature]}"/>'
            f'<text x="{KEY_W / 2:g}" y="{KEY_H / 2 + .5:g}" class="digit" text-anchor="middle" '
            f'dominant-baseline="middle">{key.owner}</text>')


def meta_cell(x, y, feature, value):
    return (f'<rect x="{x}" y="{y}" width="{META}" height="{META}" rx="3" class="len-{"ab"[feature]}"/>'
            f'<text x="{x + META / 2:g}" y="{y + META / 2 + .5:g}" class="len-digit" text-anchor="middle" '
            f'dominant-baseline="middle">{value}</text>')


def tag_shape(chunk):
    label = f'[{chunk["record_lo"]},{chunk["record_hi"]} | {chunk["start"]},{chunk["end"]}]'
    return f'<rect y="2" width="104" height="{META}" rx="4" class="tag"/>' + text(52, 17, label, 'tag-text', 'middle')


def bracket(values):
    return '[' + ' '.join(map(str, values)) + ']'


def fade(content, *frames):
    """A group whose opacity follows (time, value) keyframes; it starts hidden."""
    global tracks
    tracks += 1
    frames = [(0, frames[0][1]), *frames, (DURATION, frames[-1][1])]
    return (f'<g opacity="{frames[0][1]}"><animate attributeName="opacity" '
            f'values="{";".join(str(v) for _, v in frames)}" keyTimes="{";".join(key_time(t) for t, _ in frames)}" '
            f'dur="{DURATION:g}s" repeatCount="indefinite" calcMode="linear"/>{content}</g>')


def appear(content, start, end):
    return fade(content, (start, 0), (end, 1))


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
        frames.append((t0 + (t1 - t0) * i / steps, a * x0 + b * (x0 + reach) + c * (x1 - reach) + d * x1,
                       a * y0 + b * y0 + c * y1 + d * y1))
    return frames


def wire(y0, y1, samples=48):
    """Points on a drawn route between two row centres."""
    points = [(ROUTE_FROM, y0)]
    for i in range(samples + 1):
        u = i / samples
        a, b, c, d = (1 - u) ** 3, 3 * (1 - u) ** 2 * u, 3 * (1 - u) * u ** 2, u ** 3
        points.append((a * ROUTE_BEND + b * 1126 + c * 1226 + d * ROUTE_TO, a * y0 + b * y0 + c * y1 + d * y1))
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


def traveller(shape, legs, attrs=''):
    """An element that rests at the start of its first leg, makes each leg in
    turn and stays at the end of the last. Legs are keyframe lists."""
    global tracks
    tracks += 1
    frames = [(0, *legs[0][0][1:])] + [frame for leg in legs for frame in leg] + [(DURATION, *legs[-1][-1][1:])]
    assert all(a[0] <= b[0] for a, b in zip(frames, frames[1:])), attrs
    x, y = frames[0][1:]
    return (f'<g{attrs} transform="translate({x:g} {y:g})"><animateTransform attributeName="transform" type="translate" '
            f'values="{";".join(f"{fx:.2f},{fy:.2f}" for _, fx, fy in frames)}" '
            f'keyTimes="{";".join(key_time(t) for t, _, _ in frames)}" dur="{DURATION:g}s" '
            f'repeatCount="indefinite" calcMode="linear"/>{shape}</g>')


def ride(start, end, y0, y1, offset, t0, t1):
    """Ride the route between two rows: the anchor (the slice's first record,
    at cell-centre height) follows the wire, the element keeps its offset."""
    anchor = [(start, y0)] + wire(y0, y1) + [(end, y1)]
    return [(t, x + offset[0], y + offset[1]) for t, x, y in along(anchor, t0, t1)]


# ---------------------------------------------------------------- header ---
def station(nav, x, width, title, lines, centre=None, cls='stage', mark_track=None):
    global tracks
    y, height = (98, 96) if cls == 'stage' else (101, 93 if len(lines) > 1 else 74)
    track = ''
    if mark_track:
        tracks += 1
        track = (f'<animate attributeName="opacity" values="{mark_track}" '
                 f'keyTimes="{";".join(key_time(t) for t in PHASES)};1" calcMode="discrete" dur="{DURATION:g}s" '
                 'repeatCount="indefinite"/>')
    first = mark_track.split(';')[0] if mark_track else '0'
    tx, anchor = (centre, 'middle') if centre else (x + 16, None)
    body = text(tx, 130, title, cls, anchor) + ''.join(text(tx, 155 + 20 * i, line, 'layout', anchor) for i, line in enumerate(lines))
    return (f'<g class="nav" data-nav="{nav}"><rect class="nav-mark" data-mark="{nav}" x="{x}" y="{y}" width="{width}" '
            f'height="{height}" rx="10" opacity="{first}">{track}</rect>{body}'
            f'<rect class="nav-hit" x="{x}" y="{y}" width="{width}" height="{height}" rx="10"/></g>')


header = [
    text(40, 46, 'DynamicEmb hierarchical input dist', 'title'),
    text(40, 74, '4 nodes × 1 GPU · same 40 keys, already unique on each rank · every remote key crosses InfiniBand in one GIN put', 'subtitle'),
    f'<rect x="{E_LABEL}" y="29" width="18" height="18" rx="3" class="table-a"/>', text(E_LABEL + 28, 44, 'Table A / Feature A', 'subtitle'),
    f'<rect x="{E_LABEL + 196}" y="29" width="18" height="18" rx="3" class="table-b"/>', text(E_LABEL + 224, 44, 'Table B / Feature B', 'subtitle'),
    text(E_LABEL, 74, "Key cell digit = owner rank, not the key's value", 'subtitle'),
    f'<line x1="40" y1="90" x2="{WIDTH - 40}" y2="90" class="rule"/>',
    # The step markers carry the stage tracks; the first of them gives the player its phase times.
    station('state:0', A_LABEL - 16, 190, 'Unique KJT', ['feature-major', 'keys stay in place']),
    station('step:0', 338, 250, '1. Bucketize + push', ['write inv owner by owner,', 'then store kjt[inv[row]]'], 463, 'step', '1;0;0;0;1'),
    station('state:1', B_LABEL - 16, 210, 'key_stage', ['remote keys by owner node', 'chunk header + key records']),
    station('step:1', 1061, 230, '2. GIN put', ['count_msg first, then', 'key_stage → rail_keys'], 1176, 'step', '0;1;0;0;0'),
    station('state:2', D_LABEL - 16, 200, 'Owner window', ['node_keys own part', 'rail_keys by source node']),
    station('step:2', 1538, 124, '3. Tables', ['owner_kjt_kernel'], 1600, 'step', '0;0;1;0;0'),
    station('state:3', E_LABEL - 16, 256, 'Owner KJT + row_map', ['KJT is feature-major', 'lookup_rows keeps arrival order'], None, 'stage', '0;0;0;1;0'),
]
static += header
static += [f'<line x1="40" y1="{top_of(rank)}" x2="{WIDTH - 40}" y2="{top_of(rank)}" class="lane-edge"/>' for rank in range(P + 1)]

# Routes: one GIN key put each.
for rank in range(P):
    for row, owner in enumerate(model.others(rank)):
        y0 = slice_y(rank, row) + KEY_H / 2
        y1 = slice_y(owner, model.others(owner).index(rank)) + KEY_H / 2
        static.append(f'<g data-route="{rank}-{owner}"><title>Rank {rank} → Rank {owner}: '
                      f'{len(data["proxies"][rank]["key_stage"][owner]["records"])} keys</title>'
                      f'<path d="M{ROUTE_FROM} {y0:g} H{ROUTE_BEND} C1126 {y0:g} 1226 {y1:g} {ROUTE_TO} {y1:g}" class="route" '
                      'marker-end="url(#hier-arrow)"/></g>')

inv_groups = [[] for _ in range(P)]  # bucketize output, an owner's block at a time
groups = {name: [] for name in ('offsets', 'proxy', 'message', 'layout', 'requester', 'final')}
row_map_groups, tokens = [[], []], []
kjt_place = [{key: index for index, key in enumerate(data['owners'][rank]['kjt_keys'])} for rank in range(P)]

for rank in range(P):
    top = top_of(rank)
    b, pushed, proxy, owner, req = (data[name][rank] for name in ('bucketized', 'pushed', 'proxies', 'owners', 'requesters'))
    kjt = data['inputs'][rank]
    static.append(text(40, top + BAND / 2 + 8, f'Rank {rank}', 'rank'))

    # A. the unique KJT (static: the bucketize moves no key) and the requester's tables
    count_a = sum(key.feature == 0 for key in kjt)
    static.append(text(A_LABEL, top + 30, 'KJT values (unique)'))
    static += [f'<g transform="translate({A_CELLS + KEY_W * i} {top + 12})">{key_shape(key)}</g>' for i, key in enumerate(kjt)]
    static.append(f'<rect x="{A_CELLS}" y="{top + 12}" width="{KEY_W * len(kjt)}" height="{KEY_H}" class="buffer-edge"/>'
                  f'<line x1="{A_CELLS + KEY_W * count_a}" y1="{top + 12}" x2="{A_CELLS + KEY_W * count_a}" y2="{top + 12 + KEY_H}" class="feature-divider"/>')
    static.append(text(A_LABEL, top + 62, 'lengths') + meta_cell(A_CELLS, top + 46, 0, count_a) + meta_cell(A_CELLS + PITCH, top + 46, 1, len(kjt) - count_a))
    features = [key.feature for key in b['rows']]
    strips = [('inv', b['inv'], inv_groups), ('bucket_feature_of_row', b['bucket_feature_of_row'], inv_groups),
              ('src', req['src'], None), ('dst', req['dst'], None)]
    for index, (name, values, by_owner) in enumerate(strips):
        static.append(text(A_LABEL, top + 92 + 24 * index, name))
        for row, value in enumerate(values):
            block = b['bucket_feature_of_row'][row] // F
            cell = meta_cell(A_CELLS + PITCH * row + 8 * block, top + 76 + 24 * index, features[row], value)
            (by_owner[block] if by_owner else groups['requester']).append(cell)
    for block in range(P):
        lo, hi = b['offset_per_bucket'][block:block + 2]
        if hi > lo:
            inv_groups[block].append(text(A_CELLS + PITCH * (lo + hi) / 2 + 8 * block - 1, top + 183, f'→{block}', 'meta', 'middle'))
    for index, (name, value, group) in enumerate([
            ('offset_per_bucket', bracket(b['offset_per_bucket']), 'offsets'),
            ('offset_per_bucket_feature', bracket(b['offset_per_bucket_feature']), 'offsets'),
            ('push_order', bracket(req['push_order']), 'requester')]):
        static.append(text(A_LABEL, top + 199 + LINE * index, name))
        groups[group].append(text(A_CELLS + 20, top + 199 + LINE * index, value, 'value'))

    # the local store of its own keys, and the hand-over to the proxy steps
    static.append(f'<path d="M{A_CELLS + 296} {top + 12 + KEY_H / 2:g} H{D_LABEL - 10}" class="local" marker-end="url(#hier-arrow)"/>')
    static.append(text(B_LABEL, top + 19, 'node_key_push: kjt[inv[row]] → own part, local store'))
    static.append(f'<path d="M{A_CELLS + 296} {slice_y(rank, 1) + KEY_H / 2:g} H{B_LABEL - 10}" class="local-arrow" marker-end="url(#hier-arrow)"/>')

    # B. key_stage: a slice per other owner node
    static.append(f'<path d="M{B_TAG - 8} {slice_y(rank, 0)}h-6v{SLICE * 2 + KEY_H}h6" class="bracket"/>')
    for row, owner_node in enumerate(model.others(rank)):
        static.append(text(B_LABEL, slice_y(rank, row) + 18, f'→ n{owner_node}', 'segment-label'))
        chunk = proxy['key_stage'][owner_node]['chunks'][0]
        there = slice_y(owner_node, model.others(owner_node).index(rank))
        t0 = KEY_PUT[0] + KEY_PUT[1] * owner_node
        groups['proxy'].append(f'<g transform="translate({B_TAG} {slice_y(rank, row)})">{tag_shape(chunk)}</g>')
        groups['proxy'].append(traveller(tag_shape(chunk), [ride(B_CELLS, D_CELLS, slice_y(rank, row) + KEY_H / 2, there + KEY_H / 2, (B_TAG - B_CELLS, -KEY_H / 2), t0, t0 + KEY_PUT[2])]))
        part = data['messages'][rank][owner_node]['part']
        tokens.append(traveller(text(0, 0, bracket(part), 'token', 'middle'), [along(
            [(ROUTE_FROM + 22, slice_y(rank, row) + KEY_H / 2 + 4)]
            + [(x, y + 4) for x, y in wire(slice_y(rank, row) + KEY_H / 2, there + KEY_H / 2)[1:-1]]
            + [(ROUTE_TO - 26, there + KEY_H / 2 + 4)], *TOKEN_FLIGHT)]))
    for index, (name, value, group) in enumerate([
            ('remote_map.row', bracket(proxy['remote_map']['row']), 'proxy'),
            ('remote_map.slot', bracket(proxy['remote_map']['slot']), 'proxy'),
            ('remote_map.position', bracket(proxy['remote_map']['position']), 'proxy'),
            ('node_bucket_feature_of_row', bracket(pushed['node_bucket_feature_of_row']), 'proxy'),
            ('chunks (stream)', ' '.join(f'n{c["owner_node"]} k{c["key_lo"]}:{c["key_lo"] + c["keys"]}' for c in proxy['chunks']), 'proxy'),
            ('count_msg header', bracket(data['messages'][rank][model.others(rank)[0]]['header']), 'message'),
            ('count_msg part', ' '.join(f'n{peer}{bracket(data["messages"][rank][peer]["part"])}' for peer in model.others(rank)), 'message')]):
        static.append(text(B_LABEL, top + 142 + LINE * index, name))
        groups[group].append(text(B_LABEL + 196, top + 142 + LINE * index, value, 'value'))

    # D. the owner's window
    static.append(text(D_LABEL, top + 30, 'own part', 'segment-label'))
    static.append(f'<path d="M{D_TAG - 8} {slice_y(rank, 0)}h-6v{SLICE * 2 + KEY_H}h6" class="bracket"/>')
    for row, source in enumerate(model.others(rank)):
        static.append(text(D_LABEL, slice_y(rank, row) + 18, f'← n{source}', 'segment-label'))
    for index, (name, value, group) in enumerate([
            ('slice_in (bytes)', ' '.join(f'n{source}@{owner["slice_in"][source]}' for source in model.others(rank)), 'layout'),
            ('node_length_per_source', bracket(owner['node_length_per_source']), 'layout'),
            ('fwd_chunk_offsets', bracket(owner['fwd_chunk_offsets']), 'final')]):
        static.append(text(D_LABEL, top + 142 + LINE * index, name))
        groups[group].append(text(D_LABEL + 172, top + 142 + LINE * index, value, 'value'))
    static.append(f'<path d="M{D_CELLS + 116} {slice_y(rank, 1) + KEY_H / 2:g} H{E_LABEL - 10}" class="local-arrow" marker-end="url(#hier-arrow)"/>')

    # E. the owner's KJT, row map and the order of lookup_rows
    lengths = owner['kjt_lengths']
    feature_start = owner['kjt_offsets'][model.KJT_STRIDE]
    static.append(text(E_LABEL, top + 30, 'KJT values') + text(E_LABEL, top + 62, 'lengths')
                  + text(E_LABEL, top + 90, 'row_map') + text(E_LABEL, top + 122, 'lookup_rows'))
    for index, value in enumerate(lengths):
        feature = index // model.KJT_STRIDE
        groups['layout'].append(meta_cell(E_CELLS + PITCH * index + 8 * feature, top + 46, feature, value))
    for index, (row, key) in enumerate(zip(owner['row_map'], owner['kjt_keys'])):
        row_map_groups[key.feature].append(meta_cell(E_CELLS + PITCH * index + 8 * key.feature, top + 74, key.feature, row))
    arrival = pushed['own_part'] + model.flatten(owner['rail_keys'][source]['records'] for source in model.others(rank))
    groups['final'] += [f'<rect x="{E_CELLS + KEY_W * i}" y="{top + 104}" width="{KEY_W}" height="{KEY_H}" class="row-{"ab"[key.feature]}"/>'
                        for i, key in enumerate(arrival)]
    at = E_CELLS
    for name, count in [('own', len(pushed['own_part']))] + [(f'n{source}', len(owner['rail_keys'][source]['records'])) for source in model.others(rank)]:
        if count:
            groups['final'].append(text(at + KEY_W * count / 2, top + 144, name, 'meta', 'middle'))
        at += KEY_W * count
        if at < E_CELLS + KEY_W * len(arrival):
            groups['final'].append(f'<line x1="{at}" y1="{top + 104}" x2="{at}" y2="{top + 104 + KEY_H}" class="feature-divider"/>')
    for index, (name, value) in enumerate([
            ('group_offsets', bracket(owner['group_offsets']) + '   group_shift ' + bracket(owner['group_shift'])),
            ('fwd_groups', ' '.join(f'n{source}{bracket(owner["fwd_groups"][source])}' for source in model.others(rank))),
            ('kjt_offsets', bracket(owner['kjt_offsets']))]):
        static.append(text(E_LABEL, top + 162 + LINE * index, name))
        groups['layout'].append(text(E_LABEL + 116, top + 162 + LINE * index, value, 'value'))

    # The key copies. Each starts on its KJT cell, so nothing shows before it leaves.
    for index, key in enumerate(kjt):
        start = (A_CELLS + KEY_W * index, top + 12)
        target = top_of(key.owner)
        final = (E_CELLS + KEY_W * kjt_place[key.owner][key], target + 12)
        copy = flight  # every hop of a key is a copy with eased timing
        if key.owner == rank:
            place = (D_CELLS + KEY_W * pushed['own_part'].index(key), top + 12)
            leg1 = copy(start, place, *OWN_PUSH)
            moving.append(traveller(key_shape(key), [leg1]))
            moving.append(traveller(key_shape(key), [leg1, copy(place, final, *KJT_COPY[key.feature])]))
            continue
        row = model.others(rank).index(key.owner)
        column = proxy['key_stage'][key.owner]['records'].index(key)
        staged = (B_CELLS + KEY_W * column, slice_y(rank, row))
        there = slice_y(key.owner, model.others(key.owner).index(rank))
        landed = (D_CELLS + KEY_W * column, there)
        t1 = REMOTE_PUSH[0] + REMOTE_PUSH[1] * row
        t2 = KEY_PUT[0] + KEY_PUT[1] * key.owner
        leg1 = copy(start, staged, t1, t1 + REMOTE_PUSH[2])
        leg2 = ride(B_CELLS, D_CELLS, staged[1] + KEY_H / 2, there + KEY_H / 2, (KEY_W * column, -KEY_H / 2), t2, t2 + KEY_PUT[2])
        assert abs(leg2[0][1] - staged[0]) < 1e-6 and abs(leg2[-1][1] - landed[0]) < 1e-6 and abs(leg2[-1][2] - landed[1]) < 1e-6
        moving.append(traveller(key_shape(key), [leg1]))
        moving.append(traveller(key_shape(key), [leg1, leg2]))
        moving.append(traveller(key_shape(key), [leg1, leg2, copy(landed, final, *KJT_COPY[key.feature])]))

layers = [
    *(appear(''.join(cells), INV_FADE[0] + INV_FADE[1] * block, INV_FADE[0] + INV_FADE[1] * block + INV_FADE[2])
      for block, cells in enumerate(inv_groups)),
    appear(''.join(groups['offsets']), *OFFSETS_FADE),
    appear(''.join(groups['message']), *MESSAGE_FADE),
    appear(''.join(groups['layout']), *LAYOUT_FADE),
    appear(''.join(groups['requester']), *REQUESTER_FADE),
    *(appear(''.join(cells), *ROW_MAP_FADE[feature]) for feature, cells in enumerate(row_map_groups)),
    appear(''.join(groups['final']), *FINAL_FADE),
]
overlay = [
    appear(''.join(groups['proxy']), *PROXY_FADE),  # chunk headers travel with their records
    fade(''.join(tokens), (TOKEN_SHOW[0], 0), (TOKEN_SHOW[1], 1), (TOKEN_HIDE[0], 1), (TOKEN_HIDE[1], 0)),
]
assert REMOTE_PUSH[0] + 2 * REMOTE_PUSH[1] + REMOTE_PUSH[2] <= PROXY_FADE[0] and PROXY_FADE[1] <= PHASES[1] <= MESSAGE_FADE[0]
assert TOKEN_FLIGHT[1] <= LAYOUT_FADE[0] <= KEY_PUT[0] and KEY_PUT[0] + 3 * KEY_PUT[1] + KEY_PUT[2] <= REQUESTER_FADE[0]
assert REQUESTER_FADE[1] <= PHASES[2] <= KJT_COPY[0][0] and FINAL_FADE[1] <= PHASES[3] < DURATION

STYLE = """
text{font-family:Arial,'Noto Sans CJK SC','Microsoft YaHei',sans-serif;fill:#202a35;font-size:17px}
.title{font-size:32px;font-weight:600}.subtitle{font-size:17px;fill:#566270}
.stage{font-size:22px;font-weight:600}.step{font-size:18px;font-weight:600;fill:#465463}.layout{font-size:15px;fill:#566270}
.rank{font-size:22px;font-weight:600}.rule{stroke:#d2d9df;stroke-width:1;fill:none}.lane-edge{stroke:#c9d1d9;stroke-width:1;fill:none}
.cell{stroke:#fff;stroke-width:.9}.table-a{fill:#f5ad78}.table-b{fill:#82cbdc}
.buffer-edge{fill:none;stroke:#c8d0d8;stroke-width:1}.feature-divider{stroke:#4c5965;stroke-width:1.3}
.digit{font-size:17px;font-family:Arial,sans-serif;font-weight:500}
.segment-label{font-size:16px;font-family:Arial,sans-serif}
.meta{font-size:12px;fill:#687581;font-family:monospace}.value{font-size:12px;fill:#46525e;font-family:monospace}
.token{font-size:12px;fill:#202a35;font-family:monospace;font-weight:600}
.len-a{fill:#fdeee2;stroke:#eaa06c;stroke-width:1}.len-b{fill:#e3f3f7;stroke:#5fb3c8;stroke-width:1}
.len-digit{font-size:13px;font-family:Arial,sans-serif;font-weight:500}
.row-a{fill:#fdeee2;stroke:#eaa06c;stroke-width:1;stroke-dasharray:3 2}.row-b{fill:#e3f3f7;stroke:#5fb3c8;stroke-width:1;stroke-dasharray:3 2}
.tag{fill:#f6f8fa;stroke:#c8d0d8;stroke-width:1}.tag-text{font-size:11px;fill:#46525e;font-family:monospace}
.route{fill:none;stroke:#637585;stroke-width:1.25;opacity:.26}
.local{fill:none;stroke:#637585;stroke-width:1.25;stroke-dasharray:4 4;opacity:.7}
.local-arrow{fill:none;stroke:#596775;stroke-width:1.6}.bracket{fill:none;stroke:#788692;stroke-width:1}
.nav-mark{fill:#e8edf2}.nav-hit{fill:none;pointer-events:all}
"""
body = ''.join(static) + ''.join(layers) + ''.join(moving) + ''.join(overlay)
svg = (
    f'<svg id="hier-input-svg" xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{HEIGHT}" viewBox="0 0 {WIDTH} {HEIGHT}" '
    f'data-tracks="{tracks}" role="img" aria-labelledby="hier-title hier-desc"><title id="hier-title">DynamicEmb hierarchical '
    'input dist: key data flow across four one-GPU nodes</title><desc id="hier-desc">Filled cells are keys; the digit in one '
    'is the key&apos;s owner rank, not its value, and each rank&apos;s input is already unique. Step 1: the bucketize writes inv '
    'and the bucket feature of each row, an owner at a time, and moves no key; the push then copies each key through inv, into '
    'the own part of node_keys with a local store or into a key_stage slice for its owner node. Step 2: a count message crosses '
    'each route first and the rail layout follows from it; then one GIN put with a signal carries each key_stage slice, a chunk '
    'header and its key records, into the owner&apos;s rail_keys. Step 3: the owner copies the keys into its feature-major KJT '
    'and writes a row map, so the lookup output stays in arrival order.</desc>'
    f'<style>{STYLE}</style><defs><marker id="hier-arrow" markerWidth="8" markerHeight="8" refX="7" refY="4" '
    'orient="auto" markerUnits="userSpaceOnUse"><path d="M1 1 L7 4 L1 7" fill="none" stroke="context-stroke" '
    'stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round"/></marker></defs>'
    f'<rect x="0" y="0" width="{WIDTH}" height="{HEIGHT}" fill="#ffffff"/>{body}</svg>')
target = ASSETS / 'hier-input-dist.svg'
target.write_text(svg)
print(f'{target.name}: {len(svg)} bytes, {WIDTH} x {HEIGHT}, {tracks} tracks, {DURATION:g} s, phases {PHASES}')
