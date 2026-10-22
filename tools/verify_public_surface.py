#!/usr/bin/env python3
"""Fail-closed verifier for the bounded public export tree."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ALLOWLIST = ROOT / ".github" / "public-paths.txt"
MAX_FILE_BYTES = 256 * 1024
DISALLOWED_SUFFIXES = {
    ".7z",
    ".bin",
    ".class",
    ".dll",
    ".docx",
    ".dylib",
    ".exe",
    ".gz",
    ".ipynb",
    ".jar",
    ".pdf",
    ".pptx",
    ".pyc",
    ".rar",
    ".so",
    ".tar",
    ".tgz",
    ".wasm",
    ".xlsx",
    ".zip",
}

MICROTESTS = (
    ("kernel_drift_observable_v0_1", "kernel_drift.py", "test_kernel_drift.py"),
    ("light_bridge_consequence_gate_v0_1", "light_bridge_gate.py", "test_light_bridge_gate.py"),
    ("euclidean_phase_cone_isac_v0_1", "euclidean_phase_cone.py", "test_euclidean_phase_cone.py"),
    ("p_np_yinyang_binpacking_v0_1", "yinyang_binpacking.py", "test_yinyang_binpacking.py"),
    ("mpolynomial_1wl_molecular_gate_v0_1", "mpolynomial_1wl_molecular_gate.py", "test_mpolynomial_1wl_molecular_gate.py"),
    ("pwr2_scrambling_collective_gate_v0_1", "pwr2_scrambling_collective_gate.py", "test_pwr2_scrambling_collective_gate.py"),
)


def git(*args: str) -> bytes:
    return subprocess.check_output(["git", "-C", str(ROOT), *args])


def tracked_files() -> list[str]:
    raw = git("ls-files", "-z")
    return sorted(item.decode("utf-8") for item in raw.split(b"\0") if item)


def allowed_files() -> list[str]:
    return sorted(
        line.strip()
        for line in ALLOWLIST.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    )


def credential_markers() -> tuple[bytes, ...]:
    values = (
        "api" + "_key",
        "client" + "_secret",
        "pass" + "word",
        "private" + "_key",
        "begin " + "private key",
        "bearer" + " ",
    )
    return tuple(value.encode("ascii") for value in values)


def main() -> int:
    findings: list[str] = []
    tracked = tracked_files()
    allowed = allowed_files()

    unknown = sorted(set(tracked) - set(allowed))
    missing = sorted(set(allowed) - set(tracked))
    findings.extend(f"unknown tracked path: {path}" for path in unknown)
    findings.extend(f"missing required path: {path}" for path in missing)

    for relative in tracked:
        path = ROOT / relative
        if path.is_symlink():
            findings.append(f"symlink prohibited: {relative}")
            continue
        if relative.startswith("bane/") and relative != "bane/BOUNDARY.md":
            findings.append(f"public BANE content prohibited: {relative}")
        if path.suffix.lower() in DISALLOWED_SUFFIXES:
            findings.append(f"archive or binary suffix prohibited: {relative}")
            continue
        data = path.read_bytes()
        if len(data) > MAX_FILE_BYTES:
            findings.append(f"file exceeds public size limit: {relative}")
        if b"\0" in data:
            findings.append(f"binary payload detected: {relative}")
            continue
        lower = data.lower()
        if any(marker in lower for marker in credential_markers()):
            findings.append(f"credential marker requires private review: {relative}")

    if findings:
        print("PUBLIC_TREE_GATE=KILL")
        for finding in sorted(set(findings)):
            print(f"- {finding}")
        return 2

    for dir_name, script_name, test_name in MICROTESTS:
        microtest_dir = ROOT / "artifacts" / "microtests" / dir_name
        script_path = microtest_dir / script_name
        expected_output_path = microtest_dir / "EXPECTED_OUTPUT.txt"

        try:
            res = subprocess.run(
                [sys.executable, str(script_path)],
                cwd=microtest_dir,
                capture_output=True,
                check=True,
            )
            actual_out = res.stdout
            expected_out = expected_output_path.read_bytes()

            if actual_out != expected_out:
                print("MICROTEST_GATE=KILL")
                print(f"- Byte mismatch against EXPECTED_OUTPUT.txt in {dir_name}")
                return 2
        except Exception as e:
            print("MICROTEST_GATE=KILL")
            print(f"- Execution failed in {dir_name}: {e}")
            return 2

        try:
            subprocess.run(
                [sys.executable, "-m", "unittest", "-v", test_name],
                cwd=microtest_dir,
                capture_output=True,
                text=True,
                check=True,
            )
        except Exception as e:
            print("MICROTEST_GATE=KILL")
            print(f"- Unit tests failed in {dir_name}: {e}")
            return 2

        try:
            subprocess.run(
                ["sha256sum", "-c", "CHECKSUMS.sha256"],
                cwd=microtest_dir,
                capture_output=True,
                text=True,
                check=True,
            )
        except Exception as e:
            print("MICROTEST_GATE=KILL")
            print(f"- CHECKSUMS.sha256 check failed in {dir_name}: {e}")
            return 2

    print("PUBLIC_TREE_GATE=PASS")
    print("MICROTEST_GATE=PASS")
    print(f"MICROTEST_SUITES_VERIFIED={len(MICROTESTS)}")
    print(f"TRACKED_FILES={len(tracked)}")
    print("SCOPE=EXACT_CHECKED_TREE_ONLY")
    print("RELEASE_GATE_STATUS=OPEN")
    print("ARTIFACT_STATUS=RELEASE_CANDIDATE")
    print("CLAIM_STATUS=HOLD")
    print("REPOSITORY_STATUS=HOLD")
    print("PHYSICAL_AUTHORITY=NONE")
    print("OPERATIONAL_AUTHORITY=NONE")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
