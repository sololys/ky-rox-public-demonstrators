#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Open 0-Float Contract & Blast-Radius Scanner for Python, JSON & SystemVerilog.
==============================================================================
Surface          : tools/contract_blast_radius_scanner.py
Dependencies     : Python 3.10+ Standard Library ONLY (argparse, ast, collections, hashlib, json, pathlib, re, sys)
Arithmetic       : Exact integer arithmetic ONLY (ZERO float)
Epistemic Tier   : L1 Deterministic Static Observer (PHYSICAL_AUTHORITY = NONE, Authority(W) = NONE)
Epistemic Bound  : INSPIRED_BY != IMPLEMENTS != PROVES
"""
from __future__ import annotations

import argparse
import ast
from collections import deque
import hashlib
import json
from pathlib import Path
import re
import sys


PHYSICAL_AUTHORITY = "NONE"
WITNESS_AUTHORITY = "NONE"

SKIP_DIRS = frozenset({".git", "__pycache__", "node_modules", "dist", ".venv", "venv"})
SV_MODULE_DEF_RE = re.compile(r"\bmodule\s+([A-Za-z_][A-Za-z0-9_]*)\b")
SV_KEYWORDS = frozenset({
    "module", "endmodule", "input", "output", "inout", "wire", "reg", "logic",
    "always", "always_ff", "always_comb", "initial", "begin", "end", "if", "else",
    "case", "endcase", "for", "while", "assign", "parameter", "localparam",
    "function", "endfunction", "task", "endtask", "typedef", "struct", "enum",
    "generate", "endgenerate", "return", "assert", "property", "sequence",
})
SV_INST_RE = re.compile(r"(?:^|[;\n])\s*([A-Za-z_][A-Za-z0-9_]*)\s+(?:#\s*\([^;]*\)\s*)?([A-Za-z_][A-Za-z0-9_]*)\s*\(", re.MULTILINE)
MD_LINK_RE = re.compile(r"\[[^\]]*\]\(([^)\s#]+)")


def sha256_canonical(obj: dict) -> str:
    raw = json.dumps(obj, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def scan_python_file(path: Path) -> dict:
    src = path.read_text(encoding="utf-8", errors="replace")
    tree = ast.parse(src, filename=str(path))
    imports: set[str] = set()
    exports: set[str] = set()
    float_count = 0

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imports.add(node.module.split(".")[0])
                imports.add(node.module.split(".")[-1])
        elif isinstance(node, ast.Constant) and isinstance(node.value, float):
            float_count += 1

    for stmt in tree.body:
        if isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            if not stmt.name.startswith("_"):
                exports.add(stmt.name)

    return {
        "kind": "python",
        "imports": sorted(imports),
        "exports": sorted(exports),
        "float_constants": float_count,
        "raw_text": src,
    }


def scan_sv_file(path: Path) -> dict:
    src = path.read_text(encoding="utf-8", errors="replace")
    defined = sorted(set(SV_MODULE_DEF_RE.findall(src)))
    instantiated: set[str] = set()
    for mod_name, _inst_name in SV_INST_RE.findall(src):
        if mod_name not in SV_KEYWORDS and mod_name not in defined:
            instantiated.add(mod_name)
    return {
        "kind": "systemverilog",
        "modules_defined": defined,
        "modules_instantiated": sorted(instantiated),
        "float_constants": 0,
    }


def scan_json_file(path: Path) -> dict:
    raw = path.read_text(encoding="utf-8", errors="replace")
    try:
        data = json.loads(raw)
        keys = sorted(data.keys()) if isinstance(data, dict) else []
        valid = True
    except Exception:
        keys = []
        valid = False
    return {
        "kind": "json",
        "valid_json": valid,
        "top_keys": keys,
        "float_constants": 0,
    }


def scan_markdown_file(path: Path) -> dict:
    raw = path.read_text(encoding="utf-8", errors="replace")
    links = [
        lnk for lnk in MD_LINK_RE.findall(raw)
        if not lnk.startswith(("http://", "https://", "mailto:", "file://"))
    ]
    return {
        "kind": "markdown",
        "local_links": sorted(set(links)),
        "float_constants": 0,
    }


def build_contract_graph(root: Path) -> dict:
    root = root.resolve()
    files: dict[str, dict] = {}
    py_stem_to_paths: dict[str, list[str]] = {}
    sv_mod_to_paths: dict[str, list[str]] = {}
    json_name_to_paths: dict[str, list[str]] = {}

    for p in sorted(root.rglob("*")):
        if not p.is_file() or any(part in SKIP_DIRS for part in p.parts):
            continue
        rel = p.relative_to(root).as_posix()
        suf = p.suffix.lower()
        if suf == ".py":
            info = scan_python_file(p)
            files[rel] = info
            py_stem_to_paths.setdefault(p.stem, []).append(rel)
        elif suf == ".sv":
            info = scan_sv_file(p)
            files[rel] = info
            for mod in info["modules_defined"]:
                sv_mod_to_paths.setdefault(mod, []).append(rel)
        elif suf == ".json":
            info = scan_json_file(p)
            files[rel] = info
            json_name_to_paths.setdefault(p.name, []).append(rel)
        elif suf == ".md":
            files[rel] = scan_markdown_file(p)

    # Directed dependency edges: provider -> sorted list of direct consumers
    consumers: dict[str, set[str]] = {rel: set() for rel in files}

    for rel, info in files.items():
        kind = info["kind"]
        if kind == "python":
            for imp in info["imports"]:
                for provider in py_stem_to_paths.get(imp, ()):
                    if provider != rel:
                        consumers[provider].add(rel)
            raw_text = info.pop("raw_text", "")
            for jname, jpaths in json_name_to_paths.items():
                if jname in raw_text:
                    for jp in jpaths:
                        if Path(jp).parent == Path(rel).parent or jp in raw_text:
                            consumers[jp].add(rel)
        elif kind == "systemverilog":
            for mod in info["modules_instantiated"]:
                for provider in sv_mod_to_paths.get(mod, ()):
                    if provider != rel:
                        consumers[provider].add(rel)
        elif kind == "markdown":
            base = (root / rel).parent
            for lnk in info["local_links"]:
                try:
                    resolved = (base / lnk).resolve()
                    target_rel = resolved.relative_to(root).as_posix()
                    if target_rel in consumers and target_rel != rel:
                        consumers[target_rel].add(rel)
                except Exception:
                    pass

    edges = {k: sorted(v) for k, v in sorted(consumers.items()) if v}
    file_hashes = {
        rel: hashlib.sha256((root / rel).read_bytes()).hexdigest()
        for rel in sorted(files)
    }
    source_tree_sha256 = sha256_canonical(file_hashes)
    graph_payload = {
        "file_count": len(files),
        "edge_count": sum(len(v) for v in edges.values()),
        "edges": edges,
    }
    return {
        "root": root.name,
        "physical_authority": PHYSICAL_AUTHORITY,
        "witness_authority": WITNESS_AUTHORITY,
        "arithmetic": "EXACT_INTEGER_ZERO_FLOAT",
        "files": files,
        "edges": edges,
        "source_tree_sha256": source_tree_sha256,
        "graph_sha256": sha256_canonical(graph_payload),
    }


def compute_blast_radius(graph: dict, target: str, hold_threshold: int = 3) -> dict:
    if target not in graph["files"]:
        return {
            "target": target,
            "verdict": "KILL",
            "reason": "UNKNOWN_TARGET_PATH",
            "direct_consumers": [],
            "transitive_consumers": [],
            "total_affected": 0,
            "source_tree_sha256": graph["source_tree_sha256"],
            "graph_sha256": graph["graph_sha256"],
        }

    edges: dict[str, list[str]] = graph["edges"]
    direct = list(edges.get(target, []))
    visited: dict[str, int] = {target: 0}
    queue: deque[tuple[str, int]] = deque([(target, 0)])

    while queue:
        curr, depth = queue.popleft()
        for nxt in edges.get(curr, []):
            if nxt not in visited:
                visited[nxt] = depth + 1
                queue.append((nxt, depth + 1))

    transitive = sorted(node for node, d in visited.items() if d >= 2)
    total_affected = len(direct) + len(transitive)
    float_hits = graph["files"][target].get("float_constants", 0)

    if total_affected >= hold_threshold:
        verdict = "HOLD"
        reason = "HIGH_BLAST_RADIUS_REQUIRES_VERIFICATION"
    else:
        verdict = "OPEN"
        reason = "BOUNDED_LOCAL_BLAST_RADIUS"

    return {
        "target": target,
        "kind": graph["files"][target]["kind"],
        "float_constants_in_target": float_hits,
        "direct_consumers": direct,
        "transitive_consumers": transitive,
        "total_affected": total_affected,
        "verdict": verdict,
        "reason": reason,
        "source_tree_sha256": graph["source_tree_sha256"],
        "graph_sha256": graph["graph_sha256"],
    }


def append_audit_record(log_path: Path, report: dict, run_id: str | None = None) -> dict:
    """
    Appends one tamper-evident SHA-256-chained JSONL record.
    Software append-only hash chain ONLY (not physical WORM hardware).
    Authority(W) = NONE.
    """
    prev_hash = "0" * 64
    seq_index = 1
    if log_path.is_file():
        lines = [ln for ln in log_path.read_text(encoding="utf-8").splitlines() if ln.strip()]
        if lines:
            last = json.loads(lines[-1])
            prev_hash = str(last["record_sha256"])
            seq_index = len(lines) + 1

    affected = sorted(set(report.get("direct_consumers", [])) | set(report.get("transitive_consumers", [])))
    body = {
        "affected_nodes": affected,
        "graph_sha256": report["graph_sha256"],
        "ledger_class": "APPEND_ONLY_SHA256_JSONL_NOT_PHYSICAL_WORM",
        "previous_log_hash": prev_hash,
        "reason_codes": [report["reason"]],
        "run_id": run_id if run_id is not None else f"RUN-{seq_index:06d}",
        "source_tree_sha256": report["source_tree_sha256"],
        "target": report["target"],
        "verdict": report["verdict"],
        "witness_authority": WITNESS_AUTHORITY,
    }
    record_hash = sha256_canonical(body)
    record = dict(body)
    record["record_sha256"] = record_hash

    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, sort_keys=True, separators=(",", ":")) + "\n")
    return record


def verify_audit_log(log_path: Path) -> dict:
    """Verifies the full SHA-256 hash chain from genesis (0*64). Fails closed to KILL."""
    if not log_path.is_file():
        return {"verdict": "KILL", "reason": "LOG_FILE_NOT_FOUND", "records": 0}

    expected_prev = "0" * 64
    lines = [ln for ln in log_path.read_text(encoding="utf-8").splitlines() if ln.strip()]
    if not lines:
        return {"verdict": "KILL", "reason": "EMPTY_AUDIT_LOG", "records": 0}

    for idx, line in enumerate(lines, 1):
        try:
            rec = json.loads(line)
        except Exception:
            return {"verdict": "KILL", "reason": "MALFORMED_JSON", "line": idx}

        if rec.get("previous_log_hash") != expected_prev:
            return {"verdict": "KILL", "reason": "BROKEN_CHAIN_LINK", "line": idx}

        if rec.get("witness_authority") != WITNESS_AUTHORITY:
            return {"verdict": "KILL", "reason": "INVALID_WITNESS_AUTHORITY", "line": idx}

        stored = rec.get("record_sha256")
        body = {k: v for k, v in rec.items() if k != "record_sha256"}
        if sha256_canonical(body) != stored:
            return {"verdict": "KILL", "reason": "RECORD_HASH_MISMATCH", "line": idx}

        expected_prev = str(stored)

    return {
        "verdict": "PASS",
        "records": len(lines),
        "tip_sha256": expected_prev,
        "ledger_class": "APPEND_ONLY_SHA256_JSONL_NOT_PHYSICAL_WORM",
        "witness_authority": WITNESS_AUTHORITY,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Open 0-float contract & blast-radius scanner.")
    parser.add_argument("--root", default=".", help="Repository root to scan")
    parser.add_argument("--target", default="", help="Relative path to assess blast radius for")
    parser.add_argument("--hold-threshold", type=int, default=3, help="Affected file count triggering HOLD")
    parser.add_argument("--append-log", default="", help="Append SHA-256 chained audit record to JSONL file")
    parser.add_argument("--verify-log", default="", help="Verify an existing JSONL audit chain and exit")
    args = parser.parse_args(argv)

    if args.verify_log:
        res = verify_audit_log(Path(args.verify_log))
        print(json.dumps(res, indent=2, sort_keys=True))
        return 0 if res["verdict"] == "PASS" else 2

    graph = build_contract_graph(Path(args.root))
    if args.target:
        report = compute_blast_radius(graph, args.target, hold_threshold=args.hold_threshold)
        if args.append_log:
            rec = append_audit_record(Path(args.append_log), report)
            report["audit_record_sha256"] = rec["record_sha256"]
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0 if report["verdict"] != "KILL" else 2

    summary = {
        "root": graph["root"],
        "arithmetic": graph["arithmetic"],
        "files_scanned": len(graph["files"]),
        "dependency_edges": sum(len(v) for v in graph["edges"].values()),
        "source_tree_sha256": graph["source_tree_sha256"],
        "graph_sha256": graph["graph_sha256"],
        "witness_authority": WITNESS_AUTHORITY,
    }
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
