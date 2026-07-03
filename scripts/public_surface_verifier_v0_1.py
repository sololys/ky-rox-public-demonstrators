#!/usr/bin/env python3
"""
public_surface_verifier_v0_1.py

KY-ROX public surface verifier.

Purpose:
- Verify that the public demonstrator repository is structurally presentable.
- Detect obvious hygiene failures.
- Detect risky wording that should be reviewed before public release.
- Produce a compact report.

This is not a security scanner.
This is not a patent review.
This is not a formal proof checker.
It is a public-surface hygiene gate.
"""

from pathlib import Path
from datetime import datetime, timezone
import hashlib
import os
import subprocess
import sys


ROOT = Path(".").resolve()
REPORT_DIR = ROOT / "reports"
REPORT_PATH = REPORT_DIR / "PUBLIC_SURFACE_REPORT.md"


REQUIRED_ROOT_FILES = [
    "README.md",
    "CLAIM_LEVELS.md",
]


KILL_PATTERNS = [
    "__pycache__",
    ".pyc",
    ".pyo",
    ".DS_Store",
    "node_modules",
    ".env",
    "id_rsa",
    "id_ed25519",
]


HOLD_TERMS = [
    "patent claim",
    "production interlock",
    "certified safety",
    "guaranteed safe",
    "proven physical",
    "hardware-anchored",
    "classified",
    "secret",
    "private key",
    "API_KEY",
    "TOKEN",
    "PASSWORD",
]


STRONG_CLAIM_TERMS = [
    "undisputable proof",
    "ubestridelig bevis",
    "absolute proof",
    "100% safe",
    "physically validated",
    "production ready",
    "certified",
]


TEXT_EXTENSIONS = {
    ".md",
    ".txt",
    ".py",
    ".rs",
    ".toml",
    ".json",
    ".yaml",
    ".yml",
    ".tex",
}


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def git_status_short() -> str:
    try:
        result = subprocess.run(
            ["git", "status", "--short"],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        if result.returncode != 0:
            return f"GIT_STATUS_ERROR: {result.stderr.strip()}"
        return result.stdout.strip()
    except FileNotFoundError:
        return "GIT_NOT_AVAILABLE"


def should_scan_text(path: Path) -> bool:
    return path.suffix.lower() in TEXT_EXTENSIONS and path.is_file()


def read_text_safely(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except Exception as exc:
        return f"<<READ_ERROR: {exc}>>"


def collect_files():
    ignored_dirs = {".git", ".venv", "venv", "env"}
    files = []

    for dirpath, dirnames, filenames in os.walk(ROOT):
        current = Path(dirpath)

        dirnames[:] = [
            d for d in dirnames
            if d not in ignored_dirs
        ]

        for name in filenames:
            path = current / name
            rel = path.relative_to(ROOT)
            files.append(rel)

    return sorted(files, key=lambda p: str(p))


def verdict_from_findings(kill_findings, hold_findings):
    if kill_findings:
        return "KILL"
    if hold_findings:
        return "HOLD"
    return "OPEN"


def main() -> int:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)

    all_files = collect_files()

    kill_findings = []
    hold_findings = []
    open_findings = []

    for required in REQUIRED_ROOT_FILES:
        if (ROOT / required).exists():
            open_findings.append(f"Required root file present: `{required}`")
        else:
            hold_findings.append(f"Missing required root file: `{required}`")

    for rel in all_files:
        rel_str = str(rel)

        for pattern in KILL_PATTERNS:
            if pattern in rel_str:
                kill_findings.append(f"Forbidden hygiene artifact found: `{rel_str}`")

    manifest_files = [p for p in all_files if p.name.upper() == "MANIFEST.SHA256"]
    runlogs = [p for p in all_files if "run" in p.name.lower() or "RUNLOG" in p.name.upper()]

    if manifest_files:
        open_findings.append(f"Manifest files found: {len(manifest_files)}")
    else:
        hold_findings.append("No `MANIFEST.sha256` files found.")

    if runlogs:
        open_findings.append(f"Runlog-like files found: {len(runlogs)}")
    else:
        hold_findings.append("No runlog-like files found.")

    for rel in all_files:
        path = ROOT / rel

        if not should_scan_text(path):
            continue

        text = read_text_safely(path)
        lower = text.lower()

        for term in HOLD_TERMS:
            if term.lower() in lower:
                hold_findings.append(f"Review term `{term}` found in `{rel}`")

        for term in STRONG_CLAIM_TERMS:
            if term.lower() in lower:
                hold_findings.append(f"Strong claim term `{term}` found in `{rel}`")

    git_status = git_status_short()
    if git_status == "":
        open_findings.append("Git working tree appears clean.")
    elif git_status == "GIT_NOT_AVAILABLE":
        hold_findings.append("Git not available; working tree cleanliness not checked.")
    else:
        hold_findings.append("Git working tree is not clean or could not be checked.")

    verdict = verdict_from_findings(kill_findings, hold_findings)

    now = datetime.now(timezone.utc).isoformat()

    report = []
    report.append("# Public Surface Report")
    report.append("")
    report.append(f"- Generated UTC: `{now}`")
    report.append(f"- Root: `{ROOT}`")
    report.append(f"- Verdict: **{verdict}**")
    report.append("")
    report.append("---")
    report.append("")
    report.append("## OPEN Findings")
    report.append("")
    if open_findings:
        for item in open_findings:
            report.append(f"- {item}")
    else:
        report.append("- None.")
    report.append("")
    report.append("## HOLD Findings")
    report.append("")
    if hold_findings:
        for item in hold_findings:
            report.append(f"- {item}")
    else:
        report.append("- None.")
    report.append("")
    report.append("## KILL Findings")
    report.append("")
    if kill_findings:
        for item in kill_findings:
            report.append(f"- {item}")
    else:
        report.append("- None.")
    report.append("")
    report.append("---")
    report.append("")
    report.append("## Git Status")
    report.append("")
    report.append("```")
    report.append(git_status if git_status else "CLEAN")
    report.append("```")
    report.append("")
    report.append("## Manifest Hashes")
    report.append("")
    if manifest_files:
        for rel in manifest_files:
            digest = sha256_file(ROOT / rel)
            report.append(f"- `{rel}` — `sha256:{digest}`")
    else:
        report.append("- None.")
    report.append("")

    REPORT_PATH.write_text("\n".join(report), encoding="utf-8")

    print(f"PUBLIC_SURFACE_VERIFIER_V0_1: {verdict}")
    print(f"REPORT={REPORT_PATH}")

    if verdict == "KILL":
        return 2
    if verdict == "HOLD":
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
