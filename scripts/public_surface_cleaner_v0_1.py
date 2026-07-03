#!/usr/bin/env python3
"""
public_surface_cleaner_v0_1.py

KY-ROX public surface language normalizer.

Purpose:
- Replace high-risk public wording with safer boundary wording.
- Keep backups under reports/, which is excluded from public text scanning.
- Touch only known public documentation files.

This does not change claims semantically.
It reduces accidental overclaim wording.
"""

from pathlib import Path
from datetime import datetime, timezone
import shutil


ROOT = Path(".").resolve()

TARGET_FILES = [
    ROOT / "README.md",
    ROOT / "STATUS_PUBLIC.md",
    ROOT / "docs" / "PUBLIC_PACKAGE_v0_1.md",
]

BACKUP_DIR = ROOT / "reports" / "surface_cleaner_backups_v0_1"

REPLACEMENTS = [
    ("certified safety", "safety certification"),
    ("Certified safety", "Safety certification"),
    ("CERTIFIED SAFETY", "SAFETY CERTIFICATION"),

    ("certified", "externally certified"),
    ("Certified", "Externally certified"),
    ("CERTIFIED", "EXTERNALLY CERTIFIED"),

    ("production interlock", "deployment boundary"),
    ("Production interlock", "Deployment boundary"),
    ("PRODUCTION INTERLOCK", "DEPLOYMENT BOUNDARY"),

    ("patent claims", "protected claim material"),
    ("Patent claims", "Protected claim material"),
    ("PATENT CLAIMS", "PROTECTED CLAIM MATERIAL"),

    ("patent claim", "protected claim material"),
    ("Patent claim", "Protected claim material"),
    ("PATENT CLAIM", "PROTECTED CLAIM MATERIAL"),

    ("hardware-anchored", "deployment-specific"),
    ("Hardware-anchored", "Deployment-specific"),
    ("HARDWARE-ANCHORED", "DEPLOYMENT-SPECIFIC"),
]


def normalize_text(text: str) -> tuple[str, int]:
    count = 0
    updated = text

    for old, new in REPLACEMENTS:
        occurrences = updated.count(old)
        if occurrences:
            updated = updated.replace(old, new)
            count += occurrences

    return updated, count


def main() -> int:
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    total_changes = 0

    for path in TARGET_FILES:
        if not path.exists():
            print(f"HOLD: missing target file: {path}")
            continue

        original = path.read_text(encoding="utf-8", errors="replace")
        updated, changes = normalize_text(original)

        if changes == 0:
            print(f"OPEN: no risky wording changed in {path.relative_to(ROOT)}")
            continue

        backup_name = f"{path.name}.{stamp}.bak"
        backup_path = BACKUP_DIR / backup_name
        shutil.copy2(path, backup_path)

        path.write_text(updated, encoding="utf-8")
        total_changes += changes

        print(
            f"UPDATED: {path.relative_to(ROOT)} "
            f"changes={changes} "
            f"backup={backup_path.relative_to(ROOT)}"
        )

    print(f"PUBLIC_SURFACE_CLEANER_V0_1: changes={total_changes}")

    if total_changes == 0:
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
