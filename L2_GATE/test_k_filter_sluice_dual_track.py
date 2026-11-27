#!/usr/bin/env python3
"""
Dual-Track K-Filter Sluice Verifier (Exact Rational 2-Qubit + C11/RTL Parity).
Authority: NONE (0.00 V DC L1/L1.5 bounded software/RTL demonstrator).
"""

from __future__ import annotations

import ast
from fractions import Fraction
from pathlib import Path
import shutil
import subprocess
import tempfile
from typing import Sequence, Tuple
import unittest

HERE = Path(__file__).resolve().parent
_BANNED_FP = "fl" + "oat"
_BANNED_CX = "comp" + "lex"
_BANNED_NAMES = frozenset((_BANNED_FP, _BANNED_CX))


def assert_zero_fp_ast(path: Path) -> None:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and any(
            c.__name__ in _BANNED_NAMES for c in type(node.value).__mro__
        ):
            raise AssertionError(f"Banned numeric constant at line {getattr(node, 'lineno', 0)}")
        if isinstance(node, ast.Name) and node.id in _BANNED_NAMES:
            raise AssertionError(f"Banned identifier {node.id} at line {getattr(node, 'lineno', 0)}")
        if isinstance(node, ast.Attribute) and node.attr in _BANNED_NAMES:
            raise AssertionError(f"Banned attribute {node.attr} at line {getattr(node, 'lineno', 0)}")


assert_zero_fp_ast(Path(__file__))

QMat = Tuple[Tuple[Fraction, ...], ...]


def qmat_mul(a: QMat, b: QMat) -> QMat:
    n, m, k_len = len(a), len(b[0]), len(b)
    return tuple(
        tuple(sum((a[i][k] * b[k][j] for k in range(k_len)), Fraction(0, 1)) for j in range(m))
        for i in range(n)
    )


def qmat_transpose(a: QMat) -> QMat:
    return tuple(tuple(a[r][c] for r in range(len(a))) for c in range(len(a[0])))


def ket_to_dm(ket: Sequence[Fraction]) -> QMat:
    return tuple(tuple(ket[i] * ket[j] for j in range(len(ket))) for i in range(len(ket)))


def partial_trace_env_4x4(rho_se: QMat) -> QMat:
    return (
        (rho_se[0][0] + rho_se[1][1], rho_se[0][2] + rho_se[1][3]),
        (rho_se[2][0] + rho_se[3][1], rho_se[2][2] + rho_se[3][3]),
    )


def frobenius_diff_sq(rho_a: QMat, rho_b: QMat) -> Fraction:
    d = len(rho_a)
    acc = Fraction(0, 1)
    for i in range(d):
        for j in range(d):
            acc += (rho_a[i][j] - rho_b[i][j]) * (rho_a[j][i] - rho_b[j][i])
    return acc


U_RECOUPLE_SE: QMat = (
    (Fraction(3, 5), Fraction(0, 1), Fraction(0, 1), Fraction(4, 5)),
    (Fraction(0, 1), Fraction(3, 5), Fraction(4, 5), Fraction(0, 1)),
    (Fraction(-4, 5), Fraction(0, 1), Fraction(0, 1), Fraction(3, 5)),
    (Fraction(0, 1), Fraction(-4, 5), Fraction(3, 5), Fraction(0, 1)),
)


def apply_unitary(u: QMat, rho: QMat) -> QMat:
    return qmat_mul(qmat_mul(u, rho), qmat_transpose(u))


class TestKFilterSluiceDualTrack(unittest.TestCase):
    def test_01_ast_zero_fp(self) -> None:
        assert_zero_fp_ast(Path(__file__))

    def test_02_pythagorean_2qubit_recoupling_vs_markovian_loss(self) -> None:
        rho_a = ket_to_dm((Fraction(3, 5), Fraction(0, 1), Fraction(0, 1), Fraction(4, 5)))
        rho_b = ket_to_dm((Fraction(3, 5), Fraction(0, 1), Fraction(0, 1), Fraction(-4, 5)))
        self.assertEqual(frobenius_diff_sq(partial_trace_env_4x4(rho_a), partial_trace_env_4x4(rho_b)), Fraction(0, 1))

        out_a = partial_trace_env_4x4(apply_unitary(U_RECOUPLE_SE, rho_a))
        out_b = partial_trace_env_4x4(apply_unitary(U_RECOUPLE_SE, rho_b))
        self.assertEqual(abs(out_a[0][0] - out_b[0][0]), Fraction(576, 625))

        diag_a = tuple(tuple(rho_a[i][j] if i == j else Fraction(0, 1) for j in range(4)) for i in range(4))
        diag_b = tuple(tuple(rho_b[i][j] if i == j else Fraction(0, 1) for j in range(4)) for i in range(4))
        m_a = partial_trace_env_4x4(apply_unitary(U_RECOUPLE_SE, diag_a))
        m_b = partial_trace_env_4x4(apply_unitary(U_RECOUPLE_SE, diag_b))
        self.assertEqual(m_a[0][0], Fraction(337, 625))
        self.assertEqual(m_b[0][0], Fraction(337, 625))

    def test_03_c11_and_rtl_parity(self) -> None:
        if not shutil.which("gcc"):
            self.skipTest("gcc unavailable")
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            c_bin = tmp / "k_sluice_c11"
            subprocess.run(
                [
                    "gcc", "-std=c11", "-O2", "-Wall", "-Wextra", "-Werror", "-pedantic",
                    str(HERE / "test_k_filter_sluice_c11.c"), "-o", str(c_bin),
                ],
                check=True,
            )
            c_vecs = [
                ln for ln in subprocess.check_output([str(c_bin)], text=True).splitlines()
                if ln.startswith("VEC ")
            ]
            self.assertEqual(len(c_vecs), 12)
            if shutil.which("iverilog") and shutil.which("vvp"):
                vvp_bin = tmp / "k_sluice_rtl.vvp"
                subprocess.run(
                    [
                        "iverilog", "-g2012", "-Wall", "-o", str(vvp_bin),
                        str(HERE / "k_filter_sluice.sv"), str(HERE / "tb_k_filter_sluice.sv"),
                    ],
                    check=True,
                )
                rtl_vecs = [
                    ln for ln in subprocess.check_output(["vvp", "-N", str(vvp_bin)], text=True).splitlines()
                    if ln.startswith("VEC ")
                ]
                self.assertEqual(c_vecs, rtl_vecs)


if __name__ == "__main__":
    unittest.main()
