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


FINDER_K_GAMMA = 0x7F415D417F
MIN_QUIET_GAMMA = 4
MAX_DIST_MM = 20_000
MAX_TOF_PS = 133_425
SI_C_M_PER_S = 299_792_458
TWO_E9_PS_MM = 2_000_000_000


def require_strict_int(v: object, name: str) -> int:
    if isinstance(v, bool) or not isinstance(v, int):
        raise TypeError(f"{name} must be exact int")
    return v


def require_strict_bool(v: object, name: str) -> bool:
    if not isinstance(v, bool):
        raise TypeError(f"{name} must be exact bool")
    return v


@dataclass(frozen=True)
class ZPhi:
    """Exact element A + B*phi in Z[phi], where phi^2 = phi + 1."""

    a: int
    b: int

    def __post_init__(self) -> None:
        require_strict_int(self.a, "ZPhi.a")
        require_strict_int(self.b, "ZPhi.b")

    def __add__(self, other: ZPhi) -> ZPhi:
        return ZPhi(self.a + other.a, self.b + other.b)

    def __sub__(self, other: ZPhi) -> ZPhi:
        return ZPhi(self.a - other.a, self.b - other.b)

    def __mul__(self, other: ZPhi) -> ZPhi:
        bb = self.b * other.b
        return ZPhi(self.a * other.a + bb, self.a * other.b + self.b * other.a + bb)

    def is_non_negative(self) -> bool:
        u = 2 * self.a + self.b
        b = self.b
        if u >= 0 and b >= 0:
            return True
        if u < 0 and b <= 0:
            return False
        if u >= 0 and b < 0:
            return (u * u) >= (5 * b * b)
        return (5 * b * b) >= (u * u)


PHI = ZPhi(0, 1)
PHI_INV = ZPhi(-1, 1)


def exact_two_h_phi(q_proj: int, p_mom: int, k_defect: int, b_barrier: int, c_care: int) -> ZPhi:
    h0_2 = ZPhi(q_proj * q_proj + p_mom * p_mom + 2 * c_care, 0)
    k_term = ZPhi(2 * k_defect * k_defect, 0) * PHI
    b_term = ZPhi(2 * b_barrier, 0) * PHI_INV
    return h0_2 + k_term + b_term


@dataclass(frozen=True)
class ZeroFpOmniState:
    state_id: str
    seq_epoch: int
    q_pos: int
    p_mom: int
    lambda_spec: int
    pi_risk: int
    r_dot: int
    dist_mm: int
    tof_ps: int
    committed: bool


@dataclass(frozen=True)
class ZeroFpOmniQR:
    finder_nw: int
    finder_ne: int
    finder_sw: int
    quiet_zone: int
    s_phase_16: int
    r_mask_16: int
    m_rx_16: int
    prev_hash: str
    payload_jcs: str
    witness_seal: str


def encode_omni_qr_zero_fp(
    st: ZeroFpOmniState,
    prev_hash: str,
    s_phase_16: int = 0x05A5,
    r_mask_16: int = 0xF00F,
    quiet_zone: int = 4,
) -> ZeroFpOmniQR:
    payload_jcs = json.dumps(
        {
            "committed": require_strict_bool(st.committed, "committed"),
            "dist_mm": require_strict_int(st.dist_mm, "dist_mm"),
            "lambda_spec": require_strict_int(st.lambda_spec, "lambda_spec"),
            "p_mom": require_strict_int(st.p_mom, "p_mom"),
            "pi_risk": require_strict_int(st.pi_risk, "pi_risk"),
            "q_pos": require_strict_int(st.q_pos, "q_pos"),
            "r_dot": require_strict_int(st.r_dot, "r_dot"),
            "seq_epoch": require_strict_int(st.seq_epoch, "seq_epoch"),
            "state_id": st.state_id,
            "tof_ps": require_strict_int(st.tof_ps, "tof_ps"),
        },
        sort_keys=True,
        separators=(",", ":"),
    )
    m_rx = (s_phase_16 & 0xFFFF) ^ (r_mask_16 & 0xFFFF)
    seal_pre = f"OMNI-QR-Z0|{FINDER_K_GAMMA:010X}|{quiet_zone}|{m_rx:04X}|{prev_hash}|{payload_jcs}"
    seal = hashlib.sha256(seal_pre.encode("utf-8")).hexdigest()
    return ZeroFpOmniQR(
        finder_nw=FINDER_K_GAMMA,
        finder_ne=FINDER_K_GAMMA,
        finder_sw=FINDER_K_GAMMA,
        quiet_zone=quiet_zone,
        s_phase_16=s_phase_16 & 0xFFFF,
        r_mask_16=r_mask_16 & 0xFFFF,
        m_rx_16=m_rx,
        prev_hash=prev_hash,
        payload_jcs=payload_jcs,
        witness_seal=seal,
    )


def validate_omni_qr_zero_fp(
    qr: ZeroFpOmniQR,
    expected_prev_hash: str,
    tau_risk: int = 200,
    delta_r: int = 500,
    witness_ext: str = "",
) -> Tuple[str, Optional[ZeroFpOmniState], str]:
    if qr.finder_nw != FINDER_K_GAMMA or qr.finder_ne != FINDER_K_GAMMA or qr.finder_sw != FINDER_K_GAMMA:
        return "KILL", None, "OMNI_QR_FINDER_K_GAMMA_CORRUPTED"
    if qr.quiet_zone < MIN_QUIET_GAMMA:
        return "KILL", None, "OMNI_QR_QUIET_ZONE_GAMMA_VIOLATED"
    if ((qr.m_rx_16 ^ qr.r_mask_16) & 0xFFFF) != qr.s_phase_16:
        return "KILL", None, "OMNI_QR_WIRE_INVOLUTION_FAILED"

    expected_pre = f"OMNI-QR-Z0|{FINDER_K_GAMMA:010X}|{qr.quiet_zone}|{qr.m_rx_16:04X}|{qr.prev_hash}|{qr.payload_jcs}"
    if qr.prev_hash != expected_prev_hash or qr.witness_seal != hashlib.sha256(expected_pre.encode("utf-8")).hexdigest():
        return "KILL", None, "RC-701_OMNI_QR_WITNESS_SEAL_MISMATCH"

    raw = json.loads(qr.payload_jcs)
    st = ZeroFpOmniState(**raw)
    if (
        st.dist_mm <= 0
        or st.dist_mm > MAX_DIST_MM
        or st.tof_ps <= 0
        or st.tof_ps > MAX_TOF_PS
        or (TWO_E9_PS_MM * st.dist_mm > SI_C_M_PER_S * st.tof_ps)
        or st.lambda_spec > 0
    ):
        return "KILL", None, "OMNI_QR_SPACELIKE_OR_SPECTRAL_KILL"
    if st.pi_risk >= tau_risk or st.r_dot > delta_r or not st.committed or not witness_ext.strip():
        return "HOLD", st, "OMNI_QR_HOLD_UNWITNESSED_OR_RISK"
    return "OPEN", st, "OMNI_QR_VALIDATED_AKUERISAAVOQ"


class TestOmniCrash3ConjunctiveSluice(unittest.TestCase):
    def test_01_ast_zero_fp(self) -> None:
        assert_zero_fp_ast(Path(__file__))

    def test_02_z_phi_golden_ring_identities_and_hamiltonian(self) -> None:
        self.assertEqual(PHI * PHI, ZPhi(1, 1))
        self.assertEqual(PHI * PHI_INV, ZPhi(1, 0))
        h2 = exact_two_h_phi(480, 80, 15, 100, 250)
        self.assertEqual(h2, ZPhi(237100, 650))
        self.assertTrue(h2.is_non_negative())
        self.assertTrue(ZPhi(-8, 5).is_non_negative())
        self.assertFalse(ZPhi(-9, 5).is_non_negative())

    def test_03_omni_qr_zero_fp_and_wal_seal(self) -> None:
        st = ZeroFpOmniState(
            state_id="millennium_node_01",
            seq_epoch=1,
            q_pos=480,
            p_mom=80,
            lambda_spec=-250,
            pi_risk=50,
            r_dot=100,
            dist_mm=12000,
            tof_ps=80100,
            committed=True,
        )
        qr = encode_omni_qr_zero_fp(st, prev_hash="0" * 64)
        phase, dec, reason = validate_omni_qr_zero_fp(qr, expected_prev_hash="0" * 64, witness_ext="L01-WIT-OMNI")
        self.assertEqual(phase, "OPEN")
        self.assertEqual(dec, st)

        qr_flip = ZeroFpOmniQR(
            finder_nw=qr.finder_nw,
            finder_ne=qr.finder_ne,
            finder_sw=qr.finder_sw,
            quiet_zone=qr.quiet_zone,
            s_phase_16=qr.s_phase_16,
            r_mask_16=qr.r_mask_16,
            m_rx_16=qr.m_rx_16 ^ 1,
            prev_hash=qr.prev_hash,
            payload_jcs=qr.payload_jcs,
            witness_seal=qr.witness_seal,
        )
        p_bad, _, r_bad = validate_omni_qr_zero_fp(qr_flip, expected_prev_hash="0" * 64, witness_ext="L01-WIT-OMNI")
        self.assertEqual(p_bad, "KILL")
        self.assertEqual(r_bad, "OMNI_QR_WIRE_INVOLUTION_FAILED")

        wal = MiniWal()
        wal.append("OPEN", reason, {"qr_seal": qr.witness_seal, "h_phi_a": 237100, "h_phi_b": 650}, w_ext="L01-WIT-OMNI")
        self.assertTrue(wal.verify())

    def test_04_c11_rtl_and_post_synth_xor_zero_parity(self) -> None:
        if not shutil.which("gcc"):
            self.skipTest("gcc unavailable")
        with tempfile.TemporaryDirectory() as tmp:
            tdir = Path(tmp)
            c_bin = tdir / "omni_crash3_c11"
            subprocess.run(
                [
                    "gcc", "-std=c11", "-O2", "-mgeneral-regs-only",
                    "-Wall", "-Wextra", "-Werror", "-pedantic", "-Wconversion", "-Wsign-conversion",
                    str(HERE / "test_omni_crash3_c11.c"), "-o", str(c_bin),
                ],
                check=True,
            )
            disasm = subprocess.check_output(["objdump", "-d", str(c_bin)], text=True)
            for forbidden in ("%xmm", "%ymm", "%st(", "cvtsi2sd", "cvtsi2ss", "mulsd", "addsd"):
                self.assertNotIn(forbidden, disasm)
            c_out = subprocess.check_output([str(c_bin)], text=True).strip().splitlines()
            self.assertEqual(len(c_out), 12)

            if shutil.which("iverilog") and shutil.which("vvp"):
                rtl_vvp = tdir / "omni_crash3_rtl.vvp"
                subprocess.run(
                    [
                        "iverilog", "-g2012", "-Wall", "-o", str(rtl_vvp),
                        str(HERE / "omni_crash3_sluice.sv"), str(HERE / "tb_omni_crash3_sluice.sv"),
                    ],
                    check=True,
                )
                rtl_out = [ln for ln in subprocess.check_output(["vvp", str(rtl_vvp)], text=True).splitlines() if ln.startswith("V")]
                self.assertEqual(c_out, rtl_out)

                cells_sim = Path("/usr/share/yosys/ice40/cells_sim.v")
                if shutil.which("yosys") and cells_sim.exists():
                    synth_v = tdir / "omni_crash3_synth.v"
                    subprocess.run(
                        [
                            "yosys", "-q", "-p",
                            f"read_verilog -sv {HERE / 'omni_crash3_sluice.sv'}; synth_ice40 -top omni_crash3_sluice; write_verilog -noattr {synth_v}",
                        ],
                        check=True,
                    )
                    ps_vvp = tdir / "omni_crash3_ps.vvp"
                    subprocess.run(
                        [
                            "iverilog", "-g2012", "-DNO_ICE40_DEFAULT_ASSIGNMENTS", "-o", str(ps_vvp),
                            str(cells_sim), str(synth_v), str(HERE / "tb_omni_crash3_sluice.sv"),
                        ],
                        check=True,
                    )
                    ps_out = [ln for ln in subprocess.check_output(["vvp", str(ps_vvp)], text=True).splitlines() if ln.startswith("V")]
                    self.assertEqual(c_out, ps_out)


if __name__ == "__main__":
    unittest.main(verbosity=2)
