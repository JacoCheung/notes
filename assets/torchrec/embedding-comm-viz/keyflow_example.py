#!/usr/bin/env python3
"""Replay the SVG example using Python lists (Python 3.11).

This is a layout simulation, not a measured distributed collective. The SVG
supplies owner ranks, not embedding IDs. Key(src, feature, index, owner) names
one occurrence so repeated owner digits remain distinguishable.

The metadata follows TorchRec's KeyedJaggedTensor input dist. A lengths tensor
travels with the values, and a small splits exchange announces every segment
size first. Each rank holds one sample (stride 1), so a feature has exactly one
lengths entry per segment.

    python3.11 keyflow_example.py
    python3.11 keyflow_example.py --json
    python3.11 keyflow_example.py --svg rowwise-keyflow-animated.svg --json
"""

import argparse
from collections import Counter
from dataclasses import dataclass
import json
from pathlib import Path
import re
import xml.etree.ElementTree as ET


FEATURES = ("A", "B")
WORLD_SIZE = 4
STRIDE = 1  # samples per rank; a (segment, feature) block has STRIDE lengths
BLOCK = len(FEATURES) * STRIDE  # lengths entries sent to each destination
SOURCE_SVG = "rowwise-keyflow-animated.svg"

# Each integer is the owner rank shown in a cell. Feature 0 is A; feature 1 is B.
OWNERS = (
    ((0, 1, 2, 0, 3, 0), (0, 1, 3)),
    ((0, 1, 1, 2, 3, 3), (3, 2, 1, 0, 1)),
    ((3, 1, 2, 1), (3, 1, 2, 3, 1, 0)),
    ((0, 0, 2, 1, 3, 3, 2), (1, 2, 0)),
)


@dataclass(frozen=True)
class Key:
    src: int
    feature: int
    index: int
    owner: int

    @property
    def occurrence(self):
        return f"{self.src}:{self.feature}:{self.index}"


def flatten(groups):
    return [item for group in groups for item in group]


def labels(keys):
    return [key.occurrence for key in keys]


def make_inputs():
    # A single list per rank: all A occurrences, followed by all B occurrences.
    return [
        [
            Key(src, feature, index, owner)
            for feature, owners in enumerate(features)
            for index, owner in enumerate(owners)
        ]
        for src, features in enumerate(OWNERS)
    ]


def stable_bucketize(keys):
    buckets = [[[] for _ in FEATURES] for _ in range(WORLD_SIZE)]
    for key in keys:
        buckets[key.owner][key.feature].append(key)
    # Destination rank is the outer dimension; feature is the inner dimension.
    return [flatten(feature_buckets) for feature_buckets in buckets]


def segment_lengths(segments):
    """KJT lengths at stride 1: one key count per (segment, feature)."""
    return [
        sum(key.feature == feature for key in segment)
        for segment in segments
        for feature in range(len(FEATURES))
    ]


def lengths_segments(lengths):
    """Cut a rank-major lengths tensor into one block per rank."""
    return [lengths[start:start + BLOCK] for start in range(0, len(lengths), BLOCK)]


def dist_splits(lengths):
    """Per-destination sizes of the lengths and values tensors (KJT.dist_splits)."""
    return [BLOCK] * WORLD_SIZE, [sum(block) for block in lengths_segments(lengths)]


def exchange(send):
    """AllToAll on nested lists: recv[dst][src] = send[src][dst]."""
    return [[send[src][dst] for src in range(WORLD_SIZE)] for dst in range(WORLD_SIZE)]


def get_recat(local_split, num_splits):
    """Block order after TorchRec's _get_recat (stagger 1): feature, then source."""
    return [
        feature + src * local_split
        for feature in range(local_split)
        for src in range(num_splits)
    ]


def recat(lengths, values):
    """Regroup received tensors by feature. The receiver has no per-key tags:
    block k holds source k // 2, feature k % 2, and lengths gives its size."""
    order = get_recat(len(FEATURES), WORLD_SIZE)
    rows = [lengths[start:start + STRIDE] for start in range(0, len(lengths), STRIDE)]
    starts = [0]
    for row in rows:
        starts.append(starts[-1] + sum(row))
    permutation = [
        index for block in order for index in range(starts[block], starts[block + 1])
    ]
    return flatten(rows[block] for block in order), [values[i] for i in permutation], permutation


def verify_svg(path, inputs, send_counts, lengths, splits):
    """Check the 40 occurrences, 16 route labels, lengths and splits in the SVG."""
    root = ET.parse(path).getroot()
    observed = {}
    routes = {}
    drawn_lengths = {}
    drawn_splits = {}
    travelling = {}
    exchanged = {}
    for node in root.iter():
        if "data-len" in node.attrib:
            # A travelling lengths cell stacks its counter digits 0..count.
            digits = [
                int(child.text)
                for child in node.iter()
                if child.tag.rsplit("}", 1)[-1] == "text"
            ]
            assert digits == list(range(len(digits))), node.attrib["data-len"]
            travelling[tuple(map(int, node.attrib["data-len"].split(":")))] = digits[-1]
        if "data-lengths" in node.attrib:
            drawn_lengths[node.attrib["data-lengths"]] = [
                int(child.text)
                for child in node.iter()
                if child.tag.rsplit("}", 1)[-1] == "text" and (child.text or "").isdigit()
            ]
        if "data-splits" in node.attrib:
            drawn_splits[node.attrib["data-splits"]] = [
                int(child.text)
                for child in node.iter()
                if child.tag.rsplit("}", 1)[-1] == "text" and (child.text or "").isdigit()
            ]
        if "data-split" in node.attrib:
            # One send splits entry on its way to a peer: src:dst:tensor.
            src, dst, name = node.attrib["data-split"].split(":")
            (entry,) = [child.text for child in node.iter() if (child.text or "").isdigit()]
            exchanged[int(src), int(dst), name] = int(entry)
        if "data-moving-key" in node.attrib:
            occurrence = node.attrib["data-moving-key"]
            src, feature, index = map(int, occurrence.split(":"))
            owner = int(node.attrib["data-dst"])
            assert int(node.attrib["data-src"]) == src, occurrence
            assert 0 <= src < WORLD_SIZE and 0 <= owner < WORLD_SIZE
            assert feature in (0, 1) and index >= 0
            digits = [
                int(child.text.strip())
                for child in node.iter()
                if child.tag.rsplit("}", 1)[-1] == "text"
            ]
            assert digits == [owner], (occurrence, digits, owner)
            cells = [
                child for child in node.iter()
                if child.tag.rsplit("}", 1)[-1] == "rect"
            ]
            assert len(cells) == 1, occurrence
            assert f"table-{FEATURES[feature].lower()}" in cells[0].get("class", "").split()
            assert occurrence not in observed, occurrence
            observed[occurrence] = Key(src, feature, index, owner)
        if node.tag.rsplit("}", 1)[-1] == "title":
            match = re.fullmatch(r"Rank (\d+) → Rank (\d+): (\d+) keys", node.text or "")
            if match:
                src, dst, count = map(int, match.groups())
                assert (src, dst) not in routes
                routes[src, dst] = count
    expected = {key.occurrence: key for key in flatten(inputs)}
    assert len(observed) == 40 and observed == expected
    assert routes == {
        (src, dst): send_counts[src][dst]
        for src in range(WORLD_SIZE)
        for dst in range(WORLD_SIZE)
    }
    # Each cell is counted on its source rank and ends in its owner's lookup lengths.
    assert len(travelling) == WORLD_SIZE * WORLD_SIZE * len(FEATURES)
    for src in range(WORLD_SIZE):
        assert lengths["send"][src] == [
            travelling[src, dst, feature]
            for dst in range(WORLD_SIZE)
            for feature in range(len(FEATURES))
        ]
    for dst in range(WORLD_SIZE):
        drawn_lengths[f"lookup:{dst}"] = [
            travelling[src, dst, feature]
            for feature in range(len(FEATURES))
            for src in range(WORLD_SIZE)
        ]
    assert drawn_lengths == {
        f"{stage}:{rank}": tensor
        for stage, tensors in lengths.items()
        for rank, tensor in enumerate(tensors)
    }
    # The receive splits are the entries that travelled: recv[dst][src] = send[src][dst].
    assert len(exchanged) == 2 * WORLD_SIZE * WORLD_SIZE
    for name in ("values", "lengths"):
        for dst in range(WORLD_SIZE):
            drawn_splits[f"recv:{dst}:{name}"] = [
                exchanged[src, dst, name] for src in range(WORLD_SIZE)
            ]
    assert drawn_splits == {
        f"{stage}:{rank}:{name}": sizes
        for stage, tensors in splits.items()
        for name, per_rank in tensors.items()
        for rank, sizes in enumerate(per_rank)
    }


def simulate(svg=None):
    inputs = make_inputs()
    send = [stable_bucketize(keys) for keys in inputs]
    send_counts = [[len(segment) for segment in segments] for segments in send]

    # What a sender knows after bucketize: lengths, and from them the sizes of
    # the per-destination segments of both tensors.
    input_lengths = [segment_lengths([keys]) for keys in inputs]
    send_lengths = [segment_lengths(segments) for segments in send]
    send_splits = [dist_splits(lengths) for lengths in send_lengths]
    assert [values for _, values in send_splits] == send_counts

    # Splits AllToAll: every rank sends each peer [lengths size, values size,
    # stride]. The receiver reads them back as one row per field.
    packed_splits = [
        [[lengths[dst], values[dst], STRIDE] for dst in range(WORLD_SIZE)]
        for lengths, values in send_splits
    ]
    recv_fields = [list(map(list, zip(*triples))) for triples in exchange(packed_splits)]
    recv_lengths_splits = [fields[0] for fields in recv_fields]
    recv_splits = [fields[1] for fields in recv_fields]
    stride_per_rank = [fields[2] for fields in recv_fields]

    # Payload AllToAll, once per tensor: send[src][dst] becomes recv[dst][src].
    # Each receive buffer concatenates the source segments in source-rank order.
    recv = exchange(send)
    received = [flatten(segments) for segments in recv]
    recv_lengths = [
        flatten(blocks)
        for blocks in exchange([lengths_segments(lengths) for lengths in send_lengths])
    ]
    for dst in range(WORLD_SIZE):
        assert [len(segment) for segment in recv[dst]] == recv_splits[dst]
        assert len(recv_lengths[dst]) == sum(recv_lengths_splits[dst])
        assert recv_lengths[dst] == segment_lengths(recv[dst])
        assert stride_per_rank[dst] == [STRIDE] * WORLD_SIZE

    recatted = [recat(lengths, values) for lengths, values in zip(recv_lengths, received)]
    lookup_lengths = [lengths for lengths, _, _ in recatted]
    lookup = [keys for _, keys, _ in recatted]

    original = Counter(flatten(inputs))
    assert len(original) == 40 and set(original.values()) == {1}
    stages = {
        "input": flatten(inputs),
        "send": flatten([flatten(segments) for segments in send]),
        "recv": flatten(received),
        "lookup": flatten(lookup),
    }
    for stage in stages.values():
        assert Counter(stage) == original
    assert send_counts == [[4, 2, 1, 2], [2, 4, 2, 3], [1, 4, 2, 3], [3, 2, 3, 2]]
    for dst in range(WORLD_SIZE):
        assert recv_splits[dst] == [send_counts[src][dst] for src in range(WORLD_SIZE)]
        assert all(key.owner == dst for key in received[dst])
        assert sorted(recatted[dst][2]) == list(range(len(received[dst])))
        assert sum(lookup_lengths[dst]) == len(lookup[dst])
        expected = [
            key
            for feature in range(2)
            for src in range(WORLD_SIZE)
            for key in inputs[src]
            if key.feature == feature and key.owner == dst
        ]
        assert lookup[dst] == expected
    lengths = {
        "input": input_lengths,
        "send": send_lengths,
        "recv": recv_lengths,
        "lookup": lookup_lengths,
    }
    splits = {
        "send": {
            "values": [values for _, values in send_splits],
            "lengths": [sizes for sizes, _ in send_splits],
        },
        "recv": {"values": recv_splits, "lengths": recv_lengths_splits},
    }
    if svg is not None:
        verify_svg(svg, inputs, send_counts, lengths, splits)

    return {
        "kind": "pure_python_layout_simulation",
        "source_svg": SOURCE_SVG,
        "cell_digits": "owner ranks; actual embedding IDs are not supplied",
        "occurrence_format": "src:feature:index; feature 0=A, 1=B",
        "input_owners": [
            {name: list(owners) for name, owners in zip(FEATURES, features)}
            for features in OWNERS
        ],
        "input_occurrences": [labels(keys) for keys in inputs],
        "send_counts": send_counts,
        "send_splits": send_counts,
        "recv_splits": recv_splits,
        "stride": STRIDE,
        "lengths": lengths,
        "lengths_splits": {"send": splits["send"]["lengths"], "recv": splits["recv"]["lengths"]},
        "packed_splits": [flatten(triples) for triples in packed_splits],
        "stride_per_rank": stride_per_rank,
        "recat_blocks": get_recat(len(FEATURES), WORLD_SIZE),
        "send_buffers": [labels(flatten(segments)) for segments in send],
        "rank0": {
            "recv_segments_by_source": [labels(segment) for segment in recv[0]],
            "recv_source_major": labels(received[0]),
            "recat_permutation": recatted[0][2],
            "lookup_feature_major": labels(lookup[0]),
            "lookup_by_feature": {
                name: labels([key for key in lookup[0] if key.feature == feature])
                for feature, name in enumerate(FEATURES)
            },
        },
        "lookup_feature_counts": [
            [sum(key.feature == feature for key in keys) for feature in range(2)]
            for keys in lookup
        ],
        "checks": {
            "occurrences_per_stage": {name: len(stage) for name, stage in stages.items()},
            "unique_occurrences": len(original),
            "all_owners_match_destination": True,
            "stable_order_within_source_feature": True,
        },
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="print the complete example as JSON")
    parser.add_argument("--svg", type=Path, help="also validate the original SVG's occurrence data")
    args = parser.parse_args()
    result = simulate(args.svg)
    if args.json:
        print(json.dumps(result, indent=2))
        return
    print("Pure Python layout simulation; no distributed collective is executed.")
    print("Cell digits are owner ranks. Occurrences use src:feature:index (0=A, 1=B).")
    for rank in range(WORLD_SIZE):
        print(f"rank {rank} input owners: {result['input_owners'][rank]}")
        print(f"rank {rank} input occurrences: {result['input_occurrences'][rank]}")
        print(f"rank {rank} send lengths: {result['lengths']['send'][rank]}")
        print(f"rank {rank} send splits (values): {result['send_splits'][rank]}")
        print(f"rank {rank} recv splits (values): {result['recv_splits'][rank]}")
        print(f"rank {rank} recv lengths: {result['lengths']['recv'][rank]}")
        print(f"rank {rank} lookup lengths: {result['lengths']['lookup'][rank]}")
    print("send_counts[src][dst]:", result["send_counts"])
    print("rank 0 received by source:", result["rank0"]["recv_segments_by_source"])
    print("recat block order:", result["recat_blocks"])
    print("rank 0 recat permutation:", result["rank0"]["recat_permutation"])
    print("rank 0 lookup by feature:", result["rank0"]["lookup_by_feature"])
    print("Conservation:", result["checks"]["occurrences_per_stage"])


if __name__ == "__main__":
    main()
