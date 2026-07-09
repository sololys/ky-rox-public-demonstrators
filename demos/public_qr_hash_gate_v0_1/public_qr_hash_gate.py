#!/usr/bin/env python3
"""Public QR Hash Gate v0.1.

Claim-controlled public demonstrator for payload hash verification.

The payload is a pointer, not authority. The gate opens only when the target
file exists and its SHA-256 digest matches the declared digest.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Optional

SHA256_RE = re.compile(r"\b([a-fA-F0-9]{64})\b")


@dataclass(frozen=True)
class PayloadIndex:
    raw_payload: str
    payload_hash: str
    document: Optional[str]
    canonical_entry: Optional[str]
    declared_sha256: Optional[str]
    status: Optional[str]
    malformed_sha_line: bool = False


@dataclass(frozen=True)
class GateResult:
    decision: str
    reason: str
    index: PayloadIndex
    target_path: Optional[str]
    actual_sha256: Optional[str]


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def parse_payload(payload: str) -> PayloadIndex:
    text = payload.strip()
    lines = [line.strip() for line in text.splitlines() if line.strip()]

    document: Optional[str] = None
    canonical_entry: Optional[str] = None
    declared_sha256: Optional[str] = None
    status: Optional[str] = None
    malformed_sha_line = False

    for index, line in enumerate(lines):
        lower = line.lower()
        if lower.startswith("document:"):
            document = line.split(":", 1)[1].strip() or None
        elif lower.startswith("canonical entry:"):
            after = line.split(":", 1)[1].strip()
            if after:
                canonical_entry = after
            elif index + 1 < len(lines):
                next_line = lines[index + 1]
                if not next_line.lower().startswith(("document:", "canonical entry:", "sha-256:", "sha256:", "status:")):
                    canonical_entry = next_line
        elif lower.startswith("sha-256:") or lower.startswith("sha256:"):
            match = SHA256_RE.search(line)
            if match:
                declared_sha256 = match.group(1).lower()
            else:
                malformed_sha_line = True
        elif lower.startswith("status:"):
            status = line.split(":", 1)[1].strip() or None

    if declared_sha256 is None and not malformed_sha_line:
        match = SHA256_RE.search(text)
        if match:
            declared_sha256 = match.group(1).lower()

    return PayloadIndex(
        raw_payload=text,
        payload_hash=sha256_text(text),
        document=document,
        canonical_entry=canonical_entry,
        declared_sha256=declared_sha256,
        status=status,
        malformed_sha_line=malformed_sha_line,
    )


def decide(index: PayloadIndex, target: Optional[Path]) -> GateResult:
    if not index.raw_payload:
        return GateResult("KILL", "PAYLOAD_EMPTY", index, None, None)

    if index.malformed_sha_line:
        return GateResult("KILL", "DECLARED_SHA256_MALFORMED", index, None, None)

    if index.declared_sha256 is None:
        return GateResult("HOLD", "DECLARED_SHA256_MISSING", index, None, None)

    if index.document is None or index.canonical_entry is None or index.status is None:
        return GateResult("HOLD", "CANONICAL_FIELDS_INCOMPLETE", index, None, None)

    target_path = target or Path(index.document)
    if not target_path.exists():
        return GateResult("HOLD", "TARGET_MISSING", index, str(target_path), None)

    actual = sha256_file(target_path)
    if actual != index.declared_sha256:
        return GateResult("KILL", "HASH_MISMATCH", index, str(target_path), actual)

    return GateResult("OPEN", "HASH_MATCH", index, str(target_path), actual)


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Public fail-closed QR/payload hash gate")
    parser.add_argument("--payload", help="Raw decoded payload text")
    parser.add_argument("--payload-file", help="Text file containing decoded payload")
    parser.add_argument("--target", help="Target file to hash. Defaults to Document field from payload")
    parser.add_argument("--json", action="store_true", help="Print full JSON result")
    return parser


def load_payload(args: argparse.Namespace) -> str:
    sources = [args.payload is not None, args.payload_file is not None]
    if sum(sources) != 1:
        raise ValueError("Provide exactly one of --payload or --payload-file")
    if args.payload is not None:
        return args.payload
    return Path(args.payload_file).read_text(encoding="utf-8")


def main(argv: Optional[list[str]] = None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    try:
        payload = load_payload(args)
        parsed = parse_payload(payload)
        target = Path(args.target) if args.target else None
        result = decide(parsed, target)

        if args.json:
            print(json.dumps(asdict(result), indent=2, ensure_ascii=False))
        else:
            print(f"DECISION={result.decision}")
            print(f"REASON={result.reason}")
            print(f"DOCUMENT={result.index.document}")
            print(f"DECLARED_SHA256={result.index.declared_sha256}")
            print(f"TARGET={result.target_path}")
            print(f"ACTUAL_SHA256={result.actual_sha256}")

        return {"OPEN": 0, "HOLD": 2, "KILL": 3}[result.decision]
    except Exception as exc:
        print("DECISION=KILL", file=sys.stderr)
        print(f"REASON={exc}", file=sys.stderr)
        return 3


if __name__ == "__main__":
    raise SystemExit(main())
