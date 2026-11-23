#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
0-Float 3D Blast-Radius Sphere Exporter (Python Standard Library ONLY).
=======================================================================
Surface          : tools/export_blast_sphere.py
Dependencies     : Python 3.10+ Standard Library ONLY + tools/contract_blast_radius_scanner.py
Arithmetic       : Exact integer arithmetic ONLY (ZERO float)
Architecture     : SCAN (0 float) -> JSON MANIFEST (ix, iy, iz) -> PASSIVE GLASS VIEWER
Epistemic Tier   : L1 Deterministic Software Exporter (PHYSICAL_AUTHORITY = NONE, Authority(W) = NONE)
Epistemic Bound  : INSPIRED_BY != IMPLEMENTS != PROVES // RENDERED != AUTHORIZED
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

from contract_blast_radius_scanner import (
    build_contract_graph,
    compute_blast_radius,
)


PHYSICAL_AUTHORITY = "NONE"
WITNESS_AUTHORITY = "NONE"

# 32-point exact integer unit-circle LUT scaled by 1000 (0 float)
COS_32: tuple[int, ...] = (
    1000, 981, 924, 831, 707, 556, 383, 195,
    0, -195, -383, -556, -707, -831, -924, -981,
    -1000, -981, -924, -831, -707, -556, -383, -195,
    0, 195, 383, 556, 707, 831, 924, 981,
)
SIN_32: tuple[int, ...] = (
    0, 195, 383, 556, 707, 831, 924, 981,
    1000, 981, 924, 831, 707, 556, 383, 195,
    0, -195, -383, -556, -707, -831, -924, -981,
    -1000, -981, -924, -831, -707, -556, -383, -195,
)

# Fixed integer Z-planes and base radii per architectural layer
LAYER_GEOMETRY: dict[str, tuple[int, int]] = {
    "L1_LAW": (-300, 420),
    "L2_GATE": (-100, 520),
    "microtests": (100, 620),
    "tools": (300, 460),
    "surface": (0, 300),
}


def sha256_canonical(obj: dict) -> str:
    raw = json.dumps(obj, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def classify_layer(rel_path: str) -> str:
    if rel_path.startswith("L1_LAW/"):
        return "L1_LAW"
    if rel_path.startswith("L2_GATE/"):
        return "L2_GATE"
    if rel_path.startswith(("artifacts/microtests/", "monoliths/")):
        return "microtests"
    if rel_path.startswith("tools/"):
        return "tools"
    return "surface"


def build_blast_sphere_manifest(root: Path, hold_threshold: int = 3) -> dict:
    """
    Produces a deterministic, 0-float 3D sphere manifest from contract_blast_radius_scanner.
    Every node receives exact integer coordinates (ix, iy, iz) and precomputed
    blast-radius verdicts so the HTML viewer never invents its own truth.
    """
    graph = build_contract_graph(root)
    if not graph.get("graph_sha256"):
        raise ValueError("KILL:MISSING_GRAPH_SHA256")

    by_layer: dict[str, list[str]] = {}
    for rel in sorted(graph["files"]):
        layer = classify_layer(rel)
        by_layer.setdefault(layer, []).append(rel)

    nodes: list[dict] = []
    for layer, rels in sorted(by_layer.items()):
        iz_base, radius_base = LAYER_GEOMETRY[layer]
        total_in_layer = len(rels)
        for idx, rel in enumerate(rels):
            # Distribute deterministically on concentric integer rings (32 slots per ring)
            ring = idx // 32
            slot = (idx * 32) // max(min(total_in_layer, 32), 1)
            slot = slot % 32
            radius = radius_base + ring * 140
            ix = (radius * COS_32[slot]) // 1000
            iy = (radius * SIN_32[slot]) // 1000
            iz = iz_base + (ring * 35)

            br = compute_blast_radius(graph, rel, hold_threshold=hold_threshold)
            nodes.append({
                "id": rel,
                "layer": layer,
                "kind": graph["files"][rel]["kind"],
                "ix": ix,
                "iy": iy,
                "iz": iz,
                "float_constants": br["float_constants_in_target"],
                "direct_consumers": br["direct_consumers"],
                "transitive_consumers": br["transitive_consumers"],
                "total_affected": br["total_affected"],
                "verdict": br["verdict"],
                "reason": br["reason"],
            })

    edges: list[dict] = []
    for provider, consumers in sorted(graph["edges"].items()):
        for consumer in consumers:
            edges.append({"from": provider, "to": consumer})

    manifest_body = {
        "schema": "KY_ROX_BLAST_SPHERE_v0.1",
        "root": graph["root"],
        "arithmetic": "EXACT_INTEGER_ZERO_FLOAT",
        "physical_authority": PHYSICAL_AUTHORITY,
        "witness_authority": WITNESS_AUTHORITY,
        "rendered_not_authorized": True,
        "hold_threshold": hold_threshold,
        "source_tree_sha256": graph["source_tree_sha256"],
        "graph_sha256": graph["graph_sha256"],
        "node_count": len(nodes),
        "edge_count": len(edges),
        "nodes": nodes,
        "edges": edges,
    }
    manifest_sha256 = sha256_canonical(manifest_body)
    manifest = dict(manifest_body)
    manifest["manifest_sha256"] = manifest_sha256
    return manifest


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="0-float 3D Contract & Blast-Radius Sphere Exporter.")
    parser.add_argument("--root", default=".", help="Repository root to scan")
    parser.add_argument("--hold-threshold", type=int, default=3, help="Affected file count triggering HOLD")
    parser.add_argument("--out", default="", help="Optional output path for JSON manifest")
    args = parser.parse_args(argv)

    manifest = build_blast_sphere_manifest(Path(args.root), hold_threshold=args.hold_threshold)
    text = json.dumps(manifest, indent=2, sort_keys=True) + "\n"
    if args.out:
        out_path = Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(text, encoding="utf-8")
        print(json.dumps({
            "written": str(out_path),
            "node_count": manifest["node_count"],
            "edge_count": manifest["edge_count"],
            "graph_sha256": manifest["graph_sha256"],
            "manifest_sha256": manifest["manifest_sha256"],
        }, indent=2, sort_keys=True))
    else:
        sys.stdout.write(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
