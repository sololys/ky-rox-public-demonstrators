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

    print("PUBLIC_TREE_GATE=PASS")
    print(f"TRACKED_FILES={len(tracked)}")
    print("SCOPE=EXACT_CHECKED_TREE_ONLY")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
