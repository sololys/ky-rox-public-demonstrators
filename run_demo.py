#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================================================================
SOLOLYS // EKSISTENSENS GRAMMATIKK — THE FOUR MONOLITHS VERIFIER (run_demo.py)
================================================================================
Scope: EXACT_CHECKED_TREE_ONLY
Authority: PHYSICAL_AUTHORITY=NONE // OPERATIONAL_AUTHORITY=NONE
Claim Status: HOLD (INSPIRED_BY != IMPLEMENTS != PROVES)
Dependencies: Zero external packages (Python 3.10+ standard library only)
================================================================================
"""

from __future__ import annotations

from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parent
MICROTESTS = (
    (
        "1. KONSEKVENS",
        "LightBridge Consequence Gate v0.1",
        "light_bridge_consequence_gate_v0_1",
        "light_bridge_gate.py",
        "test_light_bridge_gate.py",
    ),
    (
        "2. ROM",
        "ISAC Euclidean Phase-Cone Gate v0.1",
        "euclidean_phase_cone_isac_v0_1",
        "euclidean_phase_cone.py",
        "test_euclidean_phase_cone.py",
    ),
    (
        "3. BANE",
        "PUNKT // BANE P-NP Yin-Yang v0.1",
        "p_np_yinyang_binpacking_v0_1",
        "yinyang_binpacking.py",
        "test_yinyang_binpacking.py",
    ),
    (
        "4. RELASJON",
        "Kernel Drift Observable v0.1",
        "kernel_drift_observable_v0_1",
        "kernel_drift.py",
        "test_kernel_drift.py",
    ),
    (
        "5. MOLEKYL",
        "M-Polynomial & 1-WL Molecular Gate v0.1",
        "mpolynomial_1wl_molecular_gate_v0_1",
        "mpolynomial_1wl_molecular_gate.py",
        "test_mpolynomial_1wl_molecular_gate.py",
    ),
)


def main() -> int:
    print("=" * 78)
    print("SOLOLYS // EKSISTENSENS GRAMMATIKK — PUBLIC MONOLITHS AUDIT")
    print("GENERATION != AUTHORIZATION != WITNESSED CONSEQUENCE")
    print("=" * 78)

    total_suites = 0
    for axis, title, folder, script_name, test_name in MICROTESTS:
        mdir = ROOT / "artifacts" / "microtests" / folder
        res_out = subprocess.run(
            [sys.executable, script_name],
            cwd=mdir,
            capture_output=True,
            check=True,
        )
        expected = (mdir / "EXPECTED_OUTPUT.txt").read_bytes()
        if res_out.stdout != expected:
            print(f"[KILL] Output mismatch in {folder}")
            return 2

        subprocess.run(
            [sys.executable, "-m", "unittest", test_name],
            cwd=mdir,
            capture_output=True,
            check=True,
        )
        subprocess.run(
            ["sha256sum", "-c", "CHECKSUMS.sha256"],
            cwd=mdir,
            capture_output=True,
            check=True,
        )
        total_suites += 1
        print(f"  [PASS 6/6] {axis:<14} :: {title:<38} (SHA-256 OK)")

    print("-" * 78)
    surface_res = subprocess.run(
        [sys.executable, str(ROOT / "tools" / "verify_public_surface.py")],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    for line in surface_res.stdout.strip().splitlines():
        print(f"  {line}")
    print("=" * 78)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
