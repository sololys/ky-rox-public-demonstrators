#!/usr/bin/env python3
"""
Self-Contained Zero-FP Consequence Sluice Verifier (Python Q/Z[phi] + C11 + iCE40 RTL).
Authority: NONE (0.00 V DC L1/L1.5 software & synthesis demonstrator).
"""

from __future__ import annotations

import ast
from dataclasses import dataclass
from fractions import Fraction
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
from typing import Dict, List, Optional, Sequence, Tuple
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


class MiniWal:
    def __init__(self) -> None:
        self.head = "0" * 64
        self.entries: List[Dict[str, object]] = []

    def append(self, phase: str, reason: str, payload: Dict[str, object], w_ext: str = "") -> str:
        if phase == "OPEN" and not w_ext.strip():
            raise PermissionError("OPEN requires explicit W_ext")
        body = {
            "seq": len(self.entries) + 1,
            "prev": self.head,
            "phase": phase,
            "reason": reason,
            "payload": payload,
            "w_ext": w_ext.strip(),
        }
        digest = hashlib.sha256(
            json.dumps(body, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()
        self.entries.append({"body": body, "hash": digest})
        self.head = digest
        return digest

    def verify(self) -> bool:
        prev = "0" * 64
        for idx, rec in enumerate(self.entries, start=1):
            body = rec["body"]
            if not isinstance(body, dict) or body["prev"] != prev or body["seq"] != idx:
                return False
            exp = hashlib.sha256(
                json.dumps(body, sort_keys=True, separators=(",", ":")).encode("utf-8")
            ).hexdigest()
            if exp != rec["hash"]:
                return False
            prev = exp
        return prev == self.head


QMat = List[List[Fraction]]


def q_zeros(rows: int, cols: int) -> QMat:
    return [[Fraction(0, 1) for _ in range(cols)] for _ in range(rows)]


def q_eye(dim: int) -> QMat:
    m = q_zeros(dim, dim)
    for i in range(dim):
        m[i][i] = Fraction(1, 1)
    return m


def q_kron(a: QMat, b: QMat) -> QMat:
    ra, ca = len(a), len(a[0])
    rb, cb = len(b), len(b[0])
    out = q_zeros(ra * rb, ca * cb)
    for i in range(ra):
        for j in range(ca):
            aij = a[i][j]
            if aij == 0:
                continue
            for k in range(rb):
                row = out[i * rb + k]
                bk = b[k]
                base_col = j * cb
                for l in range(cb):
                    bkl = bk[l]
                    if bkl != 0:
                        row[base_col + l] = aij * bkl
    return out


def q_matmul(a: QMat, b: QMat) -> QMat:
    ra, ca = len(a), len(a[0])
    cb = len(b[0])
    out = q_zeros(ra, cb)
    for i in range(ra):
        row_out = out[i]
        for k in range(ca):
            aik = a[i][k]
            if aik == 0:
                continue
            bk = b[k]
            for j in range(cb):
                if bk[j] != 0:
                    row_out[j] += aik * bk[j]
    return out


def q_transpose(a: QMat) -> QMat:
    r, c = len(a), len(a[0])
    return [[a[i][j] for i in range(r)] for j in range(c)]


def q_add_scaled(a: QMat, b: QMat, scale_b: Fraction = Fraction(1, 1)) -> QMat:
    r, c = len(a), len(a[0])
    return [[a[i][j] + scale_b * b[i][j] for j in range(c)] for i in range(r)]


def q_trace(a: QMat) -> Fraction:
    return sum((a[i][i] for i in range(len(a))), Fraction(0, 1))


def q_trace_prod(a: QMat, b: QMat) -> Fraction:
    n = len(a)
    acc = Fraction(0, 1)
    for i in range(n):
        ai = a[i]
        for j in range(n):
            aij = ai[j]
            if aij != 0 and b[j][i] != 0:
                acc += aij * b[j][i]
    return acc


def popcount_5bit(k_gamma: int) -> int:
    if k_gamma < 0 or k_gamma > 31:
        raise ValueError("K_gamma must be in 0..31")
    cnt = 0
    v = k_gamma
    while v > 0:
        cnt += v & 1
        v >>= 1
    return cnt


def singlet_rho_ab() -> QMat:
    rho = q_zeros(4, 4)
    half = Fraction(1, 2)
    rho[1][1] = half
    rho[1][2] = -half
    rho[2][1] = -half
    rho[2][2] = half
    return rho


def pauli_2q() -> Dict[str, QMat]:
    i2 = q_eye(2)
    x = [[Fraction(0, 1), Fraction(1, 1)], [Fraction(1, 1), Fraction(0, 1)]]
    z = [[Fraction(1, 1), Fraction(0, 1)], [Fraction(0, 1), Fraction(-1, 1)]]
    return {
        "ZI": q_kron(z, i2),
        "XI": q_kron(x, i2),
        "IZ": q_kron(i2, z),
        "IX": q_kron(i2, x),
        "ZZ": q_kron(z, z),
        "XX": q_kron(x, x),
    }


def partial_trace_aux_128_to_4(rho_128: QMat) -> QMat:
    rho_ab = q_zeros(4, 4)
    for i_ab in range(4):
        for j_ab in range(4):
            s = Fraction(0, 1)
            base_r = i_ab * 32
            base_c = j_ab * 32
            for aux in range(32):
                s += rho_128[base_r + aux][base_c + aux]
            rho_ab[i_ab][j_ab] = s
    return rho_ab


def frobenius_diff_sq(a: QMat, b: QMat) -> Fraction:
    r, c = len(a), len(a[0])
    s = Fraction(0, 1)
    for i in range(r):
        for j in range(c):
            d = a[i][j] - b[i][j]
            s += d * d
    return s


def evaluate_7qubit_popcount_channel(k_gamma: int) -> Dict[str, Fraction]:
    w = popcount_5bit(k_gamma)
    p_z = Fraction(w, 10)
    p_i = Fraction(1, 1) - p_z
    ops = pauli_2q()
    rho_ab_0 = singlet_rho_ab()
    proj_aux = q_zeros(32, 32)
    proj_aux[k_gamma][k_gamma] = Fraction(1, 1)
    rho_128_0 = q_kron(rho_ab_0, proj_aux)
    zi_128 = q_kron(ops["ZI"], q_eye(32))
    flipped_128 = q_matmul(zi_128, q_matmul(rho_128_0, zi_128))
    rho_128_k = q_add_scaled(q_add_scaled(q_zeros(128, 128), rho_128_0, p_i), flipped_128, p_z)
    rho_ab_k = partial_trace_aux_128_to_4(rho_128_k)
    exp_zz = q_trace_prod(rho_ab_k, ops["ZZ"])
    exp_xx = q_trace_prod(rho_ab_k, ops["XX"])
    s_tilde = Fraction(-2, 1) * exp_zz + Fraction(-2, 1) * exp_xx
    return {
        "w": Fraction(w, 1),
        "trace_128": q_trace(rho_128_k),
        "exp_za": q_trace_prod(rho_ab_k, ops["ZI"]),
        "exp_xa": q_trace_prod(rho_ab_k, ops["XI"]),
        "exp_zb": q_trace_prod(rho_ab_k, ops["IZ"]),
        "exp_xb": q_trace_prod(rho_ab_k, ops["IX"]),
        "s_45_sq": Fraction(1, 2) * s_tilde * s_tilde,
        "s_horodecki_sq": Fraction(4, 1) * (exp_zz * exp_zz + exp_xx * exp_xx),
        "frob_shift_sq": frobenius_diff_sq(rho_ab_k, rho_ab_0),
    }


class TestBellKY7QubitCPTPSluice(unittest.TestCase):
    def test_01_ast_zero_fp(self) -> None:
        assert_zero_fp_ast(Path(__file__))

    def test_02_128d_kraus_completeness_and_unit_trace(self) -> None:
        ops = pauli_2q()
        i128 = q_eye(128)
        zi_128 = q_kron(ops["ZI"], q_eye(32))
        k0 = q_add_scaled(q_zeros(128, 128), i128, Fraction(4, 5))
        k1 = q_add_scaled(q_zeros(128, 128), zi_128, Fraction(3, 5))
        lhs = q_add_scaled(q_matmul(q_transpose(k0), k0), q_matmul(q_transpose(k1), k1), Fraction(1, 1))
        self.assertEqual(frobenius_diff_sq(lhs, i128), Fraction(0, 1))

        proj_31 = q_zeros(32, 32)
        proj_31[31][31] = Fraction(1, 1)
        rho0 = q_kron(singlet_rho_ab(), proj_31)
        rho_out = q_add_scaled(
            q_matmul(k0, q_matmul(rho0, q_transpose(k0))),
            q_matmul(k1, q_matmul(rho0, q_transpose(k1))),
            Fraction(1, 1),
        )
        self.assertEqual(q_trace(rho_out), Fraction(1, 1))

    def test_03_popcount_w0_to_w5_and_l1_bluff_scraper(self) -> None:
        reps = [0, 1, 3, 7, 15, 31]
        exp_s45 = [Fraction(8, 1), Fraction(162, 25), Fraction(128, 25), Fraction(98, 25), Fraction(72, 25), Fraction(2, 1)]
        exp_hor = [Fraction(8, 1), Fraction(164, 25), Fraction(136, 25), Fraction(116, 25), Fraction(104, 25), Fraction(4, 1)]
        for w_idx, k_gamma in enumerate(reps):
            res = evaluate_7qubit_popcount_channel(k_gamma)
            self.assertEqual(res["trace_128"], Fraction(1, 1))
            self.assertEqual(res["exp_za"], Fraction(0, 1))
            self.assertEqual(res["exp_zb"], Fraction(0, 1))
            self.assertEqual(res["s_45_sq"], exp_s45[w_idx])
            self.assertEqual(res["s_horodecki_sq"], exp_hor[w_idx])
            self.assertEqual(res["frob_shift_sq"], Fraction(w_idx * w_idx, 50))
        self.assertLess(exp_s45[3], Fraction(4, 1))
        self.assertGreater(exp_hor[3], Fraction(4, 1))

    def test_04_closed_involution_null_shift_and_wal(self) -> None:
        ops = pauli_2q()
        rho_ab_0 = singlet_rho_ab()
        x_bit0 = q_zeros(32, 32)
        for idx in range(32):
            x_bit0[idx][idx ^ 1] = Fraction(1, 1)
        u_inv = q_kron(ops["ZI"], x_bit0)
        self.assertEqual(frobenius_diff_sq(q_matmul(u_inv, u_inv), q_eye(128)), Fraction(0, 1))

        out_states: List[QMat] = []
        for k_gamma in (0, 31):
            proj = q_zeros(32, 32)
            proj[k_gamma][k_gamma] = Fraction(1, 1)
            rho_init = q_kron(rho_ab_0, proj)
            rho_mid = q_matmul(u_inv, q_matmul(rho_init, q_transpose(u_inv)))
            rho_closed = q_matmul(u_inv, q_matmul(rho_mid, q_transpose(u_inv)))
            out_states.append(partial_trace_aux_128_to_4(rho_closed))
        self.assertEqual(frobenius_diff_sq(out_states[0], out_states[1]), Fraction(0, 1))

        wal = MiniWal()
        wal.append("HOLD", "QM_CLOSED_INVOLUTION_NULL", {"s1_sq": 8, "s2_sq": 8, "xi_qm": 0})
        wal.append("OPEN", "REPLICATED_WITNESS_GATE", {"s1_sq": 8}, w_ext="W_L01_BELL_KY")
        self.assertTrue(wal.verify())

    def test_05_c11_rtl_and_post_synth_xor_zero_parity(self) -> None:
        if not shutil.which("gcc"):
            self.skipTest("gcc unavailable")
        with tempfile.TemporaryDirectory() as tmp:
            tdir = Path(tmp)
            c_bin = tdir / "bell_ky_c11"
            subprocess.run(
                [
                    "gcc", "-std=c11", "-O2", "-mgeneral-regs-only",
                    "-Wall", "-Wextra", "-Werror", "-pedantic", "-Wconversion", "-Wsign-conversion",
                    str(HERE / "test_bell_ky_sluice_c11.c"), "-o", str(c_bin),
                ],
                check=True,
            )
            disasm = subprocess.check_output(["objdump", "-d", str(c_bin)], text=True)
            for forbidden in ("%xmm", "%ymm", "%st(", "cvtsi2sd", "cvtsi2ss", "mulsd", "addsd"):
                self.assertNotIn(forbidden, disasm)
            c_out = subprocess.check_output([str(c_bin)], text=True).strip().splitlines()
            self.assertEqual(len(c_out), 22)

            if shutil.which("iverilog") and shutil.which("vvp"):
                rtl_vvp = tdir / "bell_ky_rtl.vvp"
                subprocess.run(
                    [
                        "iverilog", "-g2012", "-Wall", "-o", str(rtl_vvp),
                        str(HERE / "bell_ky_sluice.sv"), str(HERE / "tb_bell_ky_sluice.sv"),
                    ],
                    check=True,
                )
                rtl_out = [ln for ln in subprocess.check_output(["vvp", "-N", str(rtl_vvp)], text=True).splitlines() if ln.startswith("V")]
                self.assertEqual(c_out, rtl_out)

                cells_sim = Path("/usr/share/yosys/ice40/cells_sim.v")
                if shutil.which("yosys") and cells_sim.exists():
                    synth_v = tdir / "bell_ky_synth.v"
                    subprocess.run(
                        [
                            "yosys", "-q", "-p",
                            f"read_verilog -sv {HERE / 'bell_ky_sluice.sv'}; synth_ice40 -top bell_ky_sluice; write_verilog -noattr {synth_v}",
                        ],
                        check=True,
                    )
                    ps_vvp = tdir / "bell_ky_ps.vvp"
                    subprocess.run(
                        [
                            "iverilog", "-g2012", "-DNO_ICE40_DEFAULT_ASSIGNMENTS", "-o", str(ps_vvp),
                            str(cells_sim), str(synth_v), str(HERE / "tb_bell_ky_sluice.sv"),
                        ],
                        check=True,
                    )
                    ps_out = [ln for ln in subprocess.check_output(["vvp", "-N", str(ps_vvp)], text=True).splitlines() if ln.startswith("V")]
                    self.assertEqual(c_out, ps_out)

    def test_06_cptp_boundary_extremes_and_1lsb_drift_rejection(self) -> None:
        ops = pauli_2q()
        proj_0 = q_zeros(32, 32)
        proj_0[0][0] = Fraction(1, 1)
        rho0 = q_kron(singlet_rho_ab(), proj_0)
        zi_128 = q_kron(ops["ZI"], q_eye(32))
        rho_pz1 = q_matmul(zi_128, q_matmul(rho0, zi_128))
        self.assertEqual(q_trace(rho_pz1), Fraction(1, 1))
        rho_ab_pz1 = partial_trace_aux_128_to_4(rho_pz1)
        exp_zz = q_trace_prod(rho_ab_pz1, ops["ZZ"])
        exp_xx = q_trace_prod(rho_ab_pz1, ops["XX"])
        self.assertEqual(exp_zz + exp_xx, Fraction(0, 1))
        self.assertEqual(Fraction(4, 1) * (exp_zz * exp_zz + exp_xx * exp_xx), Fraction(8, 1))

        eps = Fraction(1, 1 << 40)
        rho_bad_cp = q_add_scaled(q_add_scaled(rho_pz1, rho0, -eps), rho_pz1, eps)
        self.assertEqual(q_trace(rho_bad_cp), Fraction(1, 1))
        singlet_fid = q_trace_prod(partial_trace_aux_128_to_4(rho_bad_cp), singlet_rho_ab())
        self.assertEqual(singlet_fid, -eps)
        self.assertLess(singlet_fid, Fraction(0, 1))

        i128 = q_eye(128)
        self.assertGreater(frobenius_diff_sq(q_add_scaled(i128, i128, eps), i128), Fraction(0, 1))


if __name__ == "__main__":
    unittest.main(verbosity=2)
