#!/usr/bin/env python3
"""Lay out DynamicEmb's hierarchical input dist for the key-flow example (Python 3.11).

This is a layout simulation in plain Python lists, not a run of the operator.
It follows NVIDIA/recsys-examples pull request 528 (HierOutputDist) and the
reference models in its test_hier_dedup.py, specialised to the case drawn in
the article:

* four nodes with one GPU each, so a rank is its own node and its own proxy,
  and every key for another rank crosses InfiniBand in a GIN put;
* tables A and B share one lookup group, so the owner needs a row map;
* a rank has each (table, key) once, so index dedup and node dedup change
  nothing, and the keys carry no weights.

Names are the ones the source uses. Capacity-sized tables are shown up to
their valid entries.

    python3.11 hier_input_dist_example.py
    python3.11 hier_input_dist_example.py --json
"""

import argparse
import json
from itertools import accumulate

from keyflow_example import FEATURES, WORLD_SIZE, flatten, make_inputs

NUM_NODES = WORLD_SIZE
LOCAL_SIZE = 1  # GPUs per node
NUM_FEATURES = len(FEATURES)
GROUPS = ((0, NUM_FEATURES),)  # lookup groups as feature ranges [first, last)
KJT_STRIDE = LOCAL_SIZE + NUM_NODES - 1  # owner KJT columns per feature
TASK_ROWS = 32  # rows per task of the out kernels
RECORD_BYTES = 8  # a key record without weights
CHUNK_BYTES = 16  # sizeof(OwnerChunk)


def others(node):
    return [other for other in range(NUM_NODES) if other != node]


def tasks(count):
    return -(-count // TASK_ROWS)


def bucketize(keys):
    """bucketize_rows: a stable counting sort by owner. It writes inv and the
    bucket feature of each row; the keys themselves stay in the KJT."""
    inv = sorted(range(len(keys)), key=lambda row: (keys[row].owner, keys[row].feature))
    counts = [0] * (WORLD_SIZE * NUM_FEATURES)
    for key in keys:
        counts[key.owner * NUM_FEATURES + key.feature] += 1
    offsets = [0] + list(accumulate(counts))
    return {
        "rows": [keys[row] for row in inv],  # what kjt[inv[row]] reads, never stored
        "inv": inv,
        "bucket_feature_of_row": [
            keys[row].owner * NUM_FEATURES + keys[row].feature for row in inv
        ],
        "offset_per_bucket_feature": offsets,
        "offset_per_bucket": offsets[::NUM_FEATURES],
    }


def node_push(rank, bucketized):
    """node_exchange and node_key_push on a one-GPU node: the gather through
    inv stores each key once, into this rank's own node_keys."""
    offsets = bucketized["offset_per_bucket_feature"]
    first = rank * NUM_FEATURES
    own = bucketized["rows"][offsets[first]:offsets[first + NUM_FEATURES]]
    remote = [
        (row, owner_node, feature, bucketized["rows"][row])
        for owner_node in others(rank)
        for feature in range(NUM_FEATURES)
        for row in range(*offsets[owner_node * NUM_FEATURES + feature:][:2])
    ]
    own_lengths = [
        offsets[first + feature + 1] - offsets[first + feature]
        for feature in range(NUM_FEATURES)
    ]
    return {
        # NodeRow: keys for the remote part, then the offsets at its own bucket features
        "node_row": [len(remote)] + offsets[first:first + NUM_FEATURES + 1],
        "own_part": own,  # node_keys[0, lookup_keys): feature, requester, position
        "own_lengths": own_lengths,
        "own_offsets": [0] + list(accumulate(own_lengths))[:-1],
        "remote_part": remote,  # node_keys[lookup_keys, ...): owner node, feature, position
        "node_bucket_feature_of_row": [
            owner_node * NUM_FEATURES + feature for _, owner_node, feature, _ in remote
        ],
    }


def proxy_plan(node, pushed):
    """proxy_keys, proxy_chunks_and_slots and proxy_push_order. Every
    occurrence is its own node-unique key here, and each owner node's keys fit
    one chunk of the stream."""
    occurrences = pushed["remote_part"]
    assert len({(key.feature, key.occurrence) for *_, key in occurrences}) == len(occurrences)
    lengths = [0] * (NUM_NODES * NUM_FEATURES)
    for _, owner_node, feature, _ in occurrences:
        lengths[owner_node * NUM_FEATURES + feature] += 1
    node_offset_per_bucket = [
        sum(lengths[:owner_node * NUM_FEATURES]) for owner_node in range(NUM_NODES + 1)
    ]
    node_length_per_bucket = [
        b - a for a, b in zip(node_offset_per_bucket, node_offset_per_bucket[1:])
    ]
    chunk_length_per_bucket = [int(count > 0) for count in node_length_per_bucket]
    # The stream takes the owner nodes in turn from the node after its own.
    stream = [
        owner_node
        for owner_node in ((node + turn) % NUM_NODES for turn in range(1, NUM_NODES))
        if chunk_length_per_bucket[owner_node]
    ]
    chunk_offset_per_bucket = [0] + list(accumulate(chunk_length_per_bucket))
    chunks, chunk_inv, key_row, at = [], [0] * len(stream), [0] * len(occurrences), 0
    for chunk, owner_node in enumerate(stream):
        key_lo, keys = node_offset_per_bucket[owner_node], node_length_per_bucket[owner_node]
        chunks.append({"owner_node": owner_node, "key_lo": key_lo, "keys": keys,
                       "pulls": keys, "start": at, "end": at + keys, "round": 0})
        chunk_inv[chunk_offset_per_bucket[owner_node]] = chunk
        for key in range(key_lo, key_lo + keys):
            key_row[key] = at + key - key_lo  # its row in proxy_rows
        at += keys
    chunk_of_key = [0] * len(occurrences)
    for chunk, row in enumerate(chunks):
        for key in range(row["key_lo"], row["key_lo"] + row["keys"]):
            chunk_of_key[key] = chunk
    # A requester pushes its rows chunk after chunk, in each chunk in its own order.
    order = sorted(range(len(occurrences)), key=lambda occ: chunk_of_key[occ])
    position = [0] * len(occurrences)
    for place, occ in enumerate(order):
        position[occ] = place
    push_table = [0] + list(accumulate(row["keys"] for row in chunks))
    stage, stage_offsets, byte = {}, {}, 0
    for owner_node in others(node):
        chunk = chunks[chunk_inv[chunk_offset_per_bucket[owner_node]]]
        records = [key for *_, key in occurrences[chunk["key_lo"]:chunk["key_lo"] + chunk["keys"]]]
        stage[owner_node] = {
            "chunks": [{"record_lo": 0, "record_hi": chunk["keys"],
                        "start": chunk["start"], "end": chunk["end"]}],
            "records": records,
        }
        stage_offsets[owner_node] = byte
        byte += CHUNK_BYTES + RECORD_BYTES * len(records)
    return {
        "occurrences": occurrences,
        "node_num_uniques": len(occurrences),
        "node_length_per_bucket_feature": lengths,
        "node_offset_per_bucket": node_offset_per_bucket,
        "node_length_per_bucket": node_length_per_bucket,
        "chunk_length_per_bucket": chunk_length_per_bucket,
        "chunk_offset_per_bucket": chunk_offset_per_bucket,
        "chunk_inv": chunk_inv,
        "num_chunks": len(chunks),
        "chunks": chunks,
        "stream_end": at,
        # RemoteMap, an entry per occurrence of the remote part
        "remote_map": {"row": key_row, "slot": list(key_row), "position": position},
        # ProxyHeader: chunks, stream end, each chunk's end, the requester's push table
        "proxy_header": [len(chunks), at] + [row["end"] for row in chunks] + push_table,
        "push_table": push_table,
        "key_stage": stage,
        "stage_offsets": stage_offsets,
        "node_exp_off": list(range(len(occurrences) + 1)),
        "reduce_task_offsets": [0] + list(accumulate(tasks(row["keys"]) for row in chunks)),
    }


def count_message(node, pushed, proxy, peer):
    """CountMessage of a rank to the rail peer on node `peer`: a header the
    same to all, then the peer's own part."""
    lengths = proxy["node_length_per_bucket_feature"]
    header = (
        [len(proxy["occurrences"]), int(bool(proxy["occurrences"]))]  # the needs
        + [sum(pushed["own_lengths"][lo:hi]) for lo, hi in GROUPS]
        + proxy["chunk_length_per_bucket"]
        + [sum(lengths[other * NUM_FEATURES + lo:other * NUM_FEATURES + hi])
           for other in range(NUM_NODES) for lo, hi in GROUPS]
    )
    return {"header": header, "part": lengths[peer * NUM_FEATURES:(peer + 1) * NUM_FEATURES]}


def lookup_rows_of(lengths):
    """Each KJT key's row in lookup_rows, and where each group's slice starts:
    a group's own part first, then every other node's records, in node order."""
    offsets = [0] + list(accumulate(lengths))
    rows, starts, row = [0] * offsets[-1], [], 0
    for first, last in GROUPS:
        starts.append(row)
        own = [(feature, column) for feature in range(first, last) for column in range(LOCAL_SIZE)]
        other = [(feature, column) for column in range(LOCAL_SIZE, KJT_STRIDE)
                 for feature in range(first, last)]
        for feature, column in own + other:
            index = feature * KJT_STRIDE + column
            for position in range(offsets[index], offsets[index + 1]):
                rows[position] = row
                row += 1
    return rows, starts + [row]


def group_runs(lengths, column):
    """GroupRuns of the source node in `column`: where each group's records
    start among the node's records, then each group's shift into lookup_rows."""
    def keys(first, last, columns):
        return sum(lengths[feature * KJT_STRIDE + c] for feature in range(first, last) for c in columns)

    first, shift, start = [0], [], 0
    for lo, hi in GROUPS:
        before = keys(lo, hi, range(LOCAL_SIZE)) + keys(lo, hi, range(LOCAL_SIZE, column))
        shift.append(start + before - first[-1])
        first.append(first[-1] + keys(lo, hi, [column]))
        start += keys(lo, hi, range(KJT_STRIDE))
    return first + shift


def owner_tables(rank, pushed, proxies):
    """rail_layout_of as owner, then owner_kjt_kernel: the KJT, where the rail
    slices land, the chunks its forward puts and the row map."""
    sources = others(rank)
    lengths, keys = [], []
    feature_offsets = dict.fromkeys(sources, 0)
    for feature in range(NUM_FEATURES):
        first = pushed["own_offsets"][feature]
        lengths.append(pushed["own_lengths"][feature])
        keys += pushed["own_part"][first:first + lengths[-1]]
        for source in sources:
            records = proxies[source]["key_stage"][rank]["records"]
            count = proxies[source]["node_length_per_bucket_feature"][rank * NUM_FEATURES + feature]
            start = feature_offsets[source]
            feature_offsets[source] += count
            lengths.append(count)
            keys += records[start:start + count]
    rows, group_offsets = lookup_rows_of(lengths)
    own_before, group_shift = 0, []
    for (lo, hi), start in zip(GROUPS, group_offsets):
        group_shift.append(start - own_before)
        own_before += sum(pushed["own_lengths"][lo:hi])
    group_of_key = [group for group, (lo, hi) in enumerate(GROUPS)
                    for feature in range(lo, hi)
                    for _ in range(sum(lengths[feature * KJT_STRIDE:(feature + 1) * KJT_STRIDE]))]
    rail_keys, slice_in, byte = {}, {}, 0
    fwd_chunks, fwd_chunk_offsets = [], [0]
    for source in range(NUM_NODES):
        if source != rank:
            stage = proxies[source]["key_stage"][rank]
            rail_keys[source] = stage
            slice_in[source] = byte
            byte += CHUNK_BYTES * len(stage["chunks"]) + RECORD_BYTES * len(stage["records"])
            fwd_chunks += stage["chunks"]
        fwd_chunk_offsets.append(len(fwd_chunks))
    return {
        "kjt_keys": keys,
        "kjt_lengths": lengths,
        "kjt_offsets": [0] + list(accumulate(lengths)),
        "length_per_key": [sum(lengths[f * KJT_STRIDE:(f + 1) * KJT_STRIDE])
                           for f in range(NUM_FEATURES)],
        "num_recv": len(keys),
        "lookup_rows": rows,
        "row_map": [row - group_offsets[group] for row, group in zip(rows, group_of_key)],
        "group_offsets": group_offsets,
        "group_shift": group_shift,
        "rail_keys": rail_keys,
        "slice_in": slice_in,
        "node_length_per_source": [0 if source == rank else len(rail_keys[source]["records"])
                                   for source in range(NUM_NODES)],
        "fwd_chunks": fwd_chunks,
        "fwd_chunk_offsets": fwd_chunk_offsets,
        "fwd_groups": [[0] * (2 * len(GROUPS) + 1) if source == rank
                       else group_runs(lengths, LOCAL_SIZE + sources.index(source))
                       for source in range(NUM_NODES)],
    }


def requester_tables(rank, bucketized, proxy, owner):
    """requester_kernel: where the forward reads each bucketized row (src) and
    where the backward writes its gradient (dst), and its push order."""
    offsets = bucketized["offset_per_bucket_feature"]
    occurrence_of = {row: occ for occ, (row, *_) in enumerate(proxy["occurrences"])}
    src, dst, at_proxy = [], [], []
    for row, bucket_feature in enumerate(bucketized["bucket_feature_of_row"]):
        owner_rank, feature = divmod(bucket_feature, NUM_FEATURES)
        if owner_rank == rank:  # a row of its own lookup_rows
            place = owner["kjt_offsets"][feature * KJT_STRIDE] + row - offsets[bucket_feature]
            src.append(owner["lookup_rows"][place])
            dst.append(src[-1])
        else:  # rows of its proxy's proxy_rows
            occ = occurrence_of[row]
            src.append(proxy["remote_map"]["row"][occ])
            dst.append(proxy["remote_map"]["slot"][occ])
            at_proxy.append((proxy["remote_map"]["position"][occ], row))
    table = proxy["push_table"]
    return {
        "src": src,
        "dst": dst,
        "push_order": [row for _, row in sorted(at_proxy)],
        "push_order_off": [0, len(at_proxy)],
        "proxy_push_tables": table,
        "proxy_num_chunks": [proxy["num_chunks"]],
        "proxy_ends": [row["end"] for row in proxy["chunks"]] + [proxy["stream_end"]],
        "remote_task_offsets": [0] + list(accumulate(tasks(b - a) for a, b in zip(table, table[1:]))),
    }


def simulate():
    inputs = make_inputs()
    ranks = range(WORLD_SIZE)
    bucketized = [bucketize(keys) for keys in inputs]
    pushed = [node_push(rank, bucketized[rank]) for rank in ranks]
    proxies = [proxy_plan(rank, pushed[rank]) for rank in ranks]
    messages = [{peer: count_message(rank, pushed[rank], proxies[rank], peer) for peer in others(rank)}
                for rank in ranks]
    owners = [owner_tables(rank, pushed[rank], proxies) for rank in ranks]
    requesters = [requester_tables(rank, bucketized[rank], proxies[rank], owners[rank]) for rank in ranks]
    for rank in ranks:
        owner = owners[rank]
        # Every owner gets exactly its keys, each once.
        assert sorted(key.occurrence for key in owner["kjt_keys"]) == sorted(
            key.occurrence for key in flatten(inputs) if key.owner == rank)
        # lookup_rows holds the own part, then each source's records, in the order they arrived.
        arrival = pushed[rank]["own_part"] + flatten(
            owner["rail_keys"][source]["records"] for source in others(rank))
        assert [arrival[row] for row in owner["lookup_rows"]] == owner["kjt_keys"]
        assert sorted(owner["row_map"]) == list(range(owner["num_recv"]))
        for source in others(rank):
            # A proxy's bwd_groups row for an owner is that owner's fwd_groups row for it:
            # record k of group g lies at row k + shift(g) of the owner's lookup_rows.
            runs = owner["fwd_groups"][source]
            for k, key in enumerate(owner["rail_keys"][source]["records"]):
                assert arrival[k + runs[len(GROUPS) + 1]] is key
            # The key put carries what the count message announced.
            assert messages[source][rank]["part"] == [
                sum(key.feature == feature for key in owner["rail_keys"][source]["records"])
                for feature in range(NUM_FEATURES)]
        # A requester reads its own keys' rows where its owner side placed them: the own part.
        assert sorted(
            row for row, bucket in zip(requesters[rank]["src"], bucketized[rank]["bucket_feature_of_row"])
            if bucket // NUM_FEATURES == rank) == list(range(len(pushed[rank]["own_part"])))
    plans = [{
        "fwd": {
            "offset_per_bucket": bucketized[rank]["offset_per_bucket"],
            "src": requesters[rank]["src"],
            "inv": bucketized[rank]["inv"],
            "push_order": requesters[rank]["push_order"],
            "proxy_ends": requesters[rank]["proxy_ends"],
            "proxy_push_tables": requesters[rank]["proxy_push_tables"],
            "remote_task_offsets": requesters[rank]["remote_task_offsets"],
            "num_chunks": proxies[rank]["num_chunks"],
            "chunks": proxies[rank]["chunks"],
            "chunk_offset_per_bucket": proxies[rank]["chunk_offset_per_bucket"],
            "chunk_inv": proxies[rank]["chunk_inv"],
            "node_offset_per_bucket": proxies[rank]["node_offset_per_bucket"],
            "push_order_off": requesters[rank]["push_order_off"],
            "fwd_chunks": owners[rank]["fwd_chunks"],
            "fwd_chunk_offsets": owners[rank]["fwd_chunk_offsets"],
            "fwd_groups": owners[rank]["fwd_groups"],
            "node_length_per_bucket": proxies[rank]["node_length_per_bucket"],
            "proxy_num_chunks": requesters[rank]["proxy_num_chunks"],
        },
        "bwd": {
            "num_recv": owners[rank]["num_recv"],
            "dst": requesters[rank]["dst"],
            "bwd_groups": [[0] * (2 * len(GROUPS) + 1) if owner == rank
                           else owners[owner]["fwd_groups"][rank] for owner in ranks],
            "node_length_per_source": owners[rank]["node_length_per_source"],
            "reduce_task_offsets": proxies[rank]["reduce_task_offsets"],
            "node_exp_off": proxies[rank]["node_exp_off"],
        },
    } for rank in ranks]
    return {"inputs": inputs, "bucketized": bucketized, "pushed": pushed, "proxies": proxies,
            "messages": messages, "owners": owners, "requesters": requesters, "plans": plans}


def plain(value):
    """Keys become their occurrence labels so the result prints as JSON."""
    if hasattr(value, "occurrence"):
        return value.occurrence
    if isinstance(value, dict):
        return {str(name): plain(item) for name, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [plain(item) for item in value]
    return value


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="print every table as JSON")
    args = parser.parse_args()
    result = simulate()
    if args.json:
        print(json.dumps(plain(result), indent=1))
        return
    print("Layout simulation of the hierarchical input dist; no operator is run.")
    print("Keys print as src:feature:index (0=A, 1=B).")
    for rank in range(WORLD_SIZE):
        b, p, o, r = (result[name][rank] for name in ("bucketized", "proxies", "owners", "requesters"))
        print(f"rank {rank} inv: {b['inv']}")
        print(f"rank {rank} bucket_feature_of_row: {b['bucket_feature_of_row']}")
        print(f"rank {rank} offset_per_bucket: {b['offset_per_bucket']}")
        print(f"rank {rank} chunks (owner node, key_lo, keys, start, end): "
              f"{[[c['owner_node'], c['key_lo'], c['keys'], c['start'], c['end']] for c in p['chunks']]}")
        print(f"rank {rank} remote_map row: {p['remote_map']['row']} position: {p['remote_map']['position']}")
        print(f"rank {rank} count message header: {result['messages'][rank][others(rank)[0]]['header']}")
        print(f"rank {rank} KJT lengths: {o['kjt_lengths']}")
        print(f"rank {rank} row_map: {o['row_map']}")
        print(f"rank {rank} fwd_groups: {o['fwd_groups']}")
        print(f"rank {rank} src: {r['src']} push_order: {r['push_order']}")


if __name__ == "__main__":
    main()
