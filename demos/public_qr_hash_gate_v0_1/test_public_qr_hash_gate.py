#!/usr/bin/env python3
"""Deterministic tests for Public QR Hash Gate v0.1."""

from __future__ import annotations

import hashlib
import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
MODULE_PATH = ROOT / "public_qr_hash_gate.py"

spec = importlib.util.spec_from_file_location("public_qr_hash_gate", MODULE_PATH)
assert spec and spec.loader
public_qr_hash_gate = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = public_qr_hash_gate
spec.loader.exec_module(public_qr_hash_gate)


class PublicQRHashGateTests(unittest.TestCase):
    def payload_for(self, digest: str, document: str = "example_target.txt") -> str:
        return f"""PUBLIC DEMO INDEX v0.1
Document: {document}
Canonical Entry:
DEMO-001 | Public QR Hash Gate Demonstrator | v0.1
SHA-256: {digest}
Status: PUBLIC / DEMO
"""

    def test_open_on_hash_match(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "example_target.txt"
            data = b"public-demo-target\n"
            path.write_bytes(data)
            digest = hashlib.sha256(data).hexdigest()
            parsed = public_qr_hash_gate.parse_payload(self.payload_for(digest))
            result = public_qr_hash_gate.decide(parsed, path)
            self.assertEqual(result.decision, "OPEN")
            self.assertEqual(result.reason, "HASH_MATCH")
            self.assertEqual(result.actual_sha256, digest)

    def test_hold_when_target_missing(self) -> None:
        parsed = public_qr_hash_gate.parse_payload(self.payload_for("0" * 64))
        result = public_qr_hash_gate.decide(parsed, Path("missing.txt"))
        self.assertEqual(result.decision, "HOLD")
        self.assertEqual(result.reason, "TARGET_MISSING")

    def test_kill_on_hash_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "example_target.txt"
            path.write_bytes(b"actual\n")
            parsed = public_qr_hash_gate.parse_payload(self.payload_for("1" * 64))
            result = public_qr_hash_gate.decide(parsed, path)
            self.assertEqual(result.decision, "KILL")
            self.assertEqual(result.reason, "HASH_MISMATCH")

    def test_hold_on_missing_canonical_field(self) -> None:
        payload = "SHA-256: " + ("0" * 64)
        parsed = public_qr_hash_gate.parse_payload(payload)
        result = public_qr_hash_gate.decide(parsed, None)
        self.assertEqual(result.decision, "HOLD")
        self.assertEqual(result.reason, "CANONICAL_FIELDS_INCOMPLETE")

    def test_kill_on_malformed_sha_line(self) -> None:
        payload = """PUBLIC DEMO INDEX v0.1
Document: example_target.txt
Canonical Entry:
DEMO-001 | Public QR Hash Gate Demonstrator | v0.1
SHA-256: not-a-valid-sha
Status: PUBLIC / DEMO
"""
        parsed = public_qr_hash_gate.parse_payload(payload)
        result = public_qr_hash_gate.decide(parsed, None)
        self.assertEqual(result.decision, "KILL")
        self.assertEqual(result.reason, "DECLARED_SHA256_MALFORMED")

    def test_blank_canonical_entry_does_not_consume_next_field(self) -> None:
        payload = f"""PUBLIC DEMO INDEX v0.1
Document: example_target.txt
Canonical Entry:
SHA-256: {"0" * 64}
Status: PUBLIC / DEMO
"""
        parsed = public_qr_hash_gate.parse_payload(payload)
        result = public_qr_hash_gate.decide(parsed, None)
        self.assertEqual(result.decision, "HOLD")
        self.assertEqual(result.reason, "CANONICAL_FIELDS_INCOMPLETE")


if __name__ == "__main__":
    unittest.main()
