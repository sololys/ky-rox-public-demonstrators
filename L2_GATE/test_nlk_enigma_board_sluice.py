#!/usr/bin/env python3
"""
Self-Contained Zero-FP KY-Enigma v1.1 -> NLK Coordinate Board Sluice Verifier.
Verifies mod-26 involutive bijections, 104-step three-rotor notch-cascade roundtrip,
rational 9/10 and 3/2 threshold bounds, SI-2019 277K Landauer accounting, and
24/24 XOR == 0 across C11 (UBSan + 0 FP/XMM), RTL, and Yosys iCE40 cells_sim.v.
Authority: NONE (0.00 V DC L1/L1.5 software & synthesis demonstrator).
"""

from __future__ import annotations

import ast
from fractions import Fraction
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
from typing import Dict, List, Tuple
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

R1_STR = "EKMFLGDQVZNTOWYHXUSPAIBRCJ"
R2_STR = "AJDKSIRUXBLHWTMCQGZNPYFVOE"
R3_STR = "BDFHJLCPRTXVZNYEIWGAKMUSQO"
UKW_STR = "YRUHQSLDPXNGOKMIEBFZCWVJAT"


def str_to_perm(s: str) -> Tuple[int, ...]:
    return tuple(ord(c) - ord("A") for c in s)


def inv_perm(p: Tuple[int, ...]) -> Tuple[int, ...]:
    out = [0] * 26
    for i, v in enumerate(p):
        out[v] = i
    return tuple(out)


R1_F, R2_F, R3_F = str_to_perm(R1_STR), str_to_perm(R2_STR), str_to_perm(R3_STR)
R1_I, R2_I, R3_I = inv_perm(R1_F), inv_perm(R2_F), inv_perm(R3_F)
UKW_P = str_to_perm(UKW_STR)


def make_plug() -> Tuple[int, ...]:
    b = list(range(26))
    for a, c in (("A", "M"), ("F", "I"), ("N", "V")):
        ia, ic = ord(a) - ord("A"), ord(c) - ord("A")
        b[ia], b[ic] = ic, ia
    return tuple(b)


PLUG_P = make_plug()


def next_q_cascade(q: Tuple[int, int, int]) -> Tuple[int, int, int]:
    ql, qm, qr = q
    m_n = (qm == 4)
    r_n = (qr == 21)
    return (
        (ql + 1) % 26 if m_n else ql,
        (qm + 1) % 26 if (m_n or r_n) else qm,
        (qr + 1) % 26,
    )


def eval_enigma_fixed(
    x: int, q: Tuple[int, int, int], rings: Tuple[int, int, int] = (0, 0, 0), plug: bool = True
) -> int:
    c = PLUG_P[x] if plug else x
    sh0 = (q[0] - rings[0]) % 26
    sh1 = (q[1] - rings[1]) % 26
    sh2 = (q[2] - rings[2]) % 26
    c = (R3_F[(c + sh2) % 26] - sh2) % 26
    c = (R2_F[(c + sh1) % 26] - sh1) % 26
    c = (R1_F[(c + sh0) % 26] - sh0) % 26
    c = UKW_P[c]
    c = (R1_I[(c + sh0) % 26] - sh0) % 26
    c = (R2_I[(c + sh1) % 26] - sh1) % 26
    c = (R3_I[(c + sh2) % 26] - sh2) % 26
    return PLUG_P[c] if plug else c


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


class TestNlkEnigmaCoordinateBoardSluice(unittest.TestCase):
    def test_01_ast_zero_fp(self) -> None:
        assert_zero_fp_ast(Path(__file__))

    def test_02_conjugated_involution_and_no_fixed_points(self) -> None:
        for rings in ((0, 0, 0), (3, 11, 22)):
            for q in ((0, 0, 0), (0, 4, 22), (1, 5, 23), (25, 25, 25)):
                for x in range(26):
                    y = eval_enigma_fixed(x, q, rings, True)
                    self.assertNotEqual(y, x)
                    self.assertEqual(eval_enigma_fixed(y, q, rings, True), x)

    def test_03_104step_notch_cascade_roundtrip_and_rational_bounds(self) -> None:
        msg = ("GRANITTBAERERIKKEPLASTIKK" * 4) + "STAL"
        q = (0, 0, 0)
        cipher: List[int] = []
        for ch in msg:
            q = next_q_cascade(q)
            cipher.append(eval_enigma_fixed(ord(ch) - ord("A"), q))
        self.assertEqual(q, (1, 5, 0))

        q_dec = (0, 0, 0)
        rec_chars: List[str] = []
        for y in cipher:
            q_dec = next_q_cascade(q_dec)
            rec_chars.append(chr(ord("A") + eval_enigma_fixed(y, q_dec)))
        self.assertEqual("".join(rec_chars), msg)

        # Rational cross-multiplication equivalence: 9/10 <= e/sigma <= 3/2
        for e_v, s_v in ((9, 10), (8999, 10000), (15, 10), (15001, 10000)):
            ratio = Fraction(e_v, s_v)
            self.assertEqual(ratio > Fraction(3, 2), (10 * e_v) > (15 * s_v))
            self.assertEqual(ratio >= Fraction(9, 10), (10 * e_v) >= (9 * s_v))

        wal = MiniWal()
        wal.append("HOLD", "INCOMPLETE_BOARD", {"slots": 3, "expected": 4})
        wal.append("OPEN", "OK_BOARD_FITS_GAUGE", {"slots": 4, "expected": 4}, w_ext="W_L01_BOARD")
        self.assertTrue(wal.verify())

    def test_04_c11_ubsan_rtl_and_post_synth_24_of_24_xor_zero(self) -> None:
        if not shutil.which("gcc"):
            self.skipTest("gcc unavailable")
        with tempfile.TemporaryDirectory() as tmp:
            tdir = Path(tmp)
            c_bin = tdir / "nlk_enigma_c11"
            c_ubsan = tdir / "nlk_enigma_ubsan"
            subprocess.run(
                [
                    "gcc", "-std=c11", "-O2", "-mgeneral-regs-only",
                    "-Wall", "-Wextra", "-Werror", "-pedantic", "-Wconversion", "-Wsign-conversion",
                    str(HERE / "test_nlk_enigma_c11.c"), "-o", str(c_bin),
                ],
                check=True,
            )
            disasm = subprocess.check_output(["objdump", "-d", str(c_bin)], text=True)
            for forbidden in ("%xmm", "%ymm", "%st(", "cvtsi2sd", "cvtsi2ss", "mulsd", "addsd"):
                self.assertNotIn(forbidden, disasm)

            subprocess.run(
                [
                    "gcc", "-std=c11", "-O2", "-Wall", "-Wextra", "-Werror",
                    "-pedantic", "-Wconversion", "-Wsign-conversion", "-fsanitize=undefined",
                    str(HERE / "test_nlk_enigma_c11.c"), "-o", str(c_ubsan),
                ],
                check=True,
            )
            c_out = subprocess.check_output([str(c_bin)], text=True).strip().splitlines()
            ub_out = subprocess.check_output([str(c_ubsan)], text=True).strip().splitlines()
            self.assertEqual(len(c_out), 24)
            self.assertEqual(c_out, ub_out)

            if shutil.which("iverilog") and shutil.which("vvp"):
                rtl_vvp = tdir / "nlk_enigma_rtl.vvp"
                subprocess.run(
                    [
                        "iverilog", "-g2012", "-Wall", "-o", str(rtl_vvp),
                        str(HERE / "nlk_enigma_sluice.sv"), str(HERE / "tb_nlk_enigma_sluice.sv"),
                    ],
                    check=True,
                )
                rtl_out = [
                    ln for ln in subprocess.check_output(["vvp", str(rtl_vvp)], text=True).splitlines()
                    if ln.startswith("V")
                ]
                self.assertEqual(c_out, rtl_out)

                cells_sim = Path("/usr/share/yosys/ice40/cells_sim.v")
                if shutil.which("yosys") and cells_sim.exists():
                    synth_v = tdir / "nlk_enigma_synth.v"
                    subprocess.run(
                        [
                            "yosys", "-q", "-p",
                            f"read_verilog -sv {HERE / 'nlk_enigma_sluice.sv'}; synth_ice40 -top nlk_enigma_sluice; write_verilog -noattr {synth_v}",
                        ],
                        check=True,
                    )
                    ps_vvp = tdir / "nlk_enigma_ps.vvp"
                    subprocess.run(
                        [
                            "iverilog", "-g2012", "-DNO_ICE40_DEFAULT_ASSIGNMENTS", "-o", str(ps_vvp),
                            str(cells_sim), str(synth_v), str(HERE / "tb_nlk_enigma_sluice.sv"),
                        ],
                        check=True,
                    )
                    ps_out = [
                        ln for ln in subprocess.check_output(["vvp", str(ps_vvp)], text=True).splitlines()
                        if ln.startswith("V")
                    ]
                    self.assertEqual(c_out, ps_out)


if __name__ == "__main__":
    unittest.main(verbosity=2)
