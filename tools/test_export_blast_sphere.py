#!/usr/bin/env python3
"""Unit tests (6/6 PASS, 0 float) for tools/export_blast_sphere.py."""
from __future__ import annotations

import ast
from pathlib import Path
import unittest

from contract_blast_radius_scanner import build_contract_graph
from export_blast_sphere import build_blast_sphere_manifest


class TestExportBlastSphere(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.repo_root = Path(__file__).resolve().parents[1]
        cls.manifest = build_blast_sphere_manifest(cls.repo_root, hold_threshold=3)
        cls.by_id = {n["id"]: n for n in cls.manifest["nodes"]}

    def test_01_graph_sha256_parity_with_scanner(self) -> None:
        scanner_graph = build_contract_graph(self.repo_root)
        self.assertEqual(self.manifest["graph_sha256"], scanner_graph["graph_sha256"])
        self.assertEqual(self.manifest["source_tree_sha256"], scanner_graph["source_tree_sha256"])

    def test_02_exact_integer_3d_coordinates_on_all_nodes(self) -> None:
        self.assertGreater(self.manifest["node_count"], 20)
        for node in self.manifest["nodes"]:
            for coord in ("ix", "iy", "iz"):
                self.assertIsInstance(node[coord], int)
                self.assertNotIsInstance(node[coord], bool)

    def test_03_decoder_205b_is_hold_with_three_direct_consumers(self) -> None:
        dec = self.by_id["L2_GATE/fpga_capsule_frame_205b_decoder.sv"]
        self.assertEqual(dec["layer"], "L2_GATE")
        self.assertEqual(dec["verdict"], "HOLD")
        self.assertEqual(dec["total_affected"], 3)
        self.assertEqual(dec["float_constants"], 0)
        self.assertIn("L2_GATE/gothenburg_corridor_rosetta_top.sv", dec["direct_consumers"])
        self.assertIn("L2_GATE/tb_kpod_guillotine_and_205b_decoder.sv", dec["direct_consumers"])

    def test_04_deterministic_manifest_sha256(self) -> None:
        m2 = build_blast_sphere_manifest(self.repo_root, hold_threshold=3)
        self.assertEqual(self.manifest["manifest_sha256"], m2["manifest_sha256"])

    def test_05_passive_glass_authority_none(self) -> None:
        self.assertEqual(self.manifest["physical_authority"], "NONE")
        self.assertEqual(self.manifest["witness_authority"], "NONE")
        self.assertTrue(self.manifest["rendered_not_authorized"])

    def test_06_zero_float_ast_check(self) -> None:
        src = (Path(__file__).resolve().parent / "export_blast_sphere.py").read_text(encoding="utf-8")
        tree = ast.parse(src)
        floats = [n for n in ast.walk(tree) if isinstance(n, ast.Constant) and isinstance(n.value, float)]
        self.assertEqual(floats, [])


if __name__ == "__main__":
    unittest.main()
