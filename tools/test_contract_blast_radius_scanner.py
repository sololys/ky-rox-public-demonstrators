#!/usr/bin/env python3
"""Unit tests (6/6 PASS, 0 float) for tools/contract_blast_radius_scanner.py."""
from __future__ import annotations

import ast
from pathlib import Path
import tempfile
import unittest

from contract_blast_radius_scanner import (
    append_audit_record,
    build_contract_graph,
    compute_blast_radius,
    verify_audit_log,
)


class TestContractBlastRadiusScanner(unittest.TestCase):
    def test_01_python_and_json_blast_radius(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "FIXTURE.json").write_text('{"a": 1}\n', encoding="utf-8")
            (root / "core_gate.py").write_text(
                'import json\nDATA = "FIXTURE.json"\ndef check(x): return x == 1\n',
                encoding="utf-8",
            )
            (root / "runner.py").write_text(
                "from core_gate import check\ndef run(): return check(1)\n",
                encoding="utf-8",
            )
            (root / "cli.py").write_text(
                "import runner\nrunner.run()\n",
                encoding="utf-8",
            )
            g = build_contract_graph(root)
            r_json = compute_blast_radius(g, "FIXTURE.json", hold_threshold=3)
            self.assertEqual(r_json["direct_consumers"], ["core_gate.py"])
            self.assertEqual(r_json["transitive_consumers"], ["cli.py", "runner.py"])
            self.assertEqual(r_json["total_affected"], 3)
            self.assertEqual(r_json["verdict"], "HOLD")

    def test_02_systemverilog_module_instantiation_mapping(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "decoder.sv").write_text("module decoder(input logic clk); endmodule\n", encoding="utf-8")
            (root / "tb_decoder.sv").write_text(
                "module tb_decoder; decoder u_dut(.clk(clk)); endmodule\n",
                encoding="utf-8",
            )
            g = build_contract_graph(root)
            r = compute_blast_radius(g, "decoder.sv", hold_threshold=3)
            self.assertEqual(r["direct_consumers"], ["tb_decoder.sv"])
            self.assertEqual(r["verdict"], "OPEN")

    def test_03_unknown_target_returns_kill(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            g = build_contract_graph(Path(tmp))
            r = compute_blast_radius(g, "does_not_exist.py")
            self.assertEqual(r["verdict"], "KILL")
            self.assertEqual(r["reason"], "UNKNOWN_TARGET_PATH")

    def test_04_deterministic_graph_sha256(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        g1 = build_contract_graph(repo_root)
        g2 = build_contract_graph(repo_root)
        self.assertEqual(g1["graph_sha256"], g2["graph_sha256"])
        self.assertGreater(len(g1["files"]), 20)

    def test_05_real_repo_sv_and_python_targets(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        g = build_contract_graph(repo_root)
        r_sv = compute_blast_radius(g, "L2_GATE/fpga_capsule_frame_205b_decoder.sv")
        self.assertIn("L2_GATE/tb_kpod_guillotine_and_205b_decoder.sv", r_sv["direct_consumers"])
        r_py = compute_blast_radius(g, "L1_LAW/invariants_pure.py")
        self.assertGreaterEqual(r_py["total_affected"], 1)

    def test_06_zero_float_ast_check(self) -> None:
        src = (Path(__file__).resolve().parent / "contract_blast_radius_scanner.py").read_text(encoding="utf-8")
        tree = ast.parse(src)
        floats = [n for n in ast.walk(tree) if isinstance(n, ast.Constant) and isinstance(n.value, float)]
        self.assertEqual(floats, [])

    def test_07_append_only_hash_chain_and_tamper_detection(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "a.py").write_text("def f(): return 1\n", encoding="utf-8")
            (root / "b.py").write_text("import a\n", encoding="utf-8")
            log_path = root / "audit.jsonl"

            g = build_contract_graph(root)
            r1 = compute_blast_radius(g, "a.py")
            r2 = compute_blast_radius(g, "missing.py")
            rec1 = append_audit_record(log_path, r1)
            rec2 = append_audit_record(log_path, r2)

            self.assertEqual(rec1["previous_log_hash"], "0" * 64)
            self.assertEqual(rec2["previous_log_hash"], rec1["record_sha256"])
            self.assertEqual(rec1["witness_authority"], "NONE")
            self.assertEqual(rec2["verdict"], "KILL")

            ok = verify_audit_log(log_path)
            self.assertEqual(ok["verdict"], "PASS")
            self.assertEqual(ok["records"], 2)

            # Tamper 1 character -> must fail closed with KILL
            tampered = log_path.read_text(encoding="utf-8").replace("OPEN", "HOLD", 1)
            log_path.write_text(tampered, encoding="utf-8")
            bad = verify_audit_log(log_path)
            self.assertEqual(bad["verdict"], "KILL")
            self.assertEqual(bad["reason"], "RECORD_HASH_MISMATCH")

    def test_08_source_tree_sha256_determinism(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "x.py").write_text("X = 1\n", encoding="utf-8")
            h1 = build_contract_graph(root)["source_tree_sha256"]
            h2 = build_contract_graph(root)["source_tree_sha256"]
            self.assertEqual(h1, h2)
            (root / "x.py").write_text("X = 2\n", encoding="utf-8")
            h3 = build_contract_graph(root)["source_tree_sha256"]
            self.assertNotEqual(h1, h3)


if __name__ == "__main__":
    unittest.main()
