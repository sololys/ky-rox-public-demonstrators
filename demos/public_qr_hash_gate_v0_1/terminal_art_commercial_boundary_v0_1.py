#!/usr/bin/env python3
"""Commercial Boundary Terminal Artifact v0.1.

Terminal art generated from CLAIM_BOUNDARY.md.

Run:
  python3 terminal_art_commercial_boundary_v0_1.py
  python3 terminal_art_commercial_boundary_v0_1.py --frames 8
  python3 terminal_art_commercial_boundary_v0_1.py --plain

Principle:
  persistence without recurrence.
"""

from __future__ import annotations

import argparse
import hashlib
import math
import re
import time
from collections import Counter
from pathlib import Path


RESET = "\033[0m"
DIM = "\033[2m"
BOLD = "\033[1m"

PALETTE = [
    236, 237, 238, 239, 240, 242, 244, 246,
    28, 34, 40, 46, 82, 118, 154, 190,
    220, 214, 208, 202, 196, 129, 93, 57,
    39, 45, 51, 87, 123, 159, 195, 231,
]

GLYPH_RAMP = " ··:;░▒▓█"
FRACTURE = "╱╲╳╴╵╶╷┃━┼╂"
SPARKS = "◇◆✧✦*+"
GATES = "OHK"
PRIMES = (2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31)
PHI = (1 + 5 ** 0.5) / 2


def esc(code: str, enabled: bool) -> str:
    return f"\033[{code}m" if enabled else ""


def load_source() -> str:
    here = Path(__file__).resolve().parent
    source = here / "CLAIM_BOUNDARY.md"
    return source.read_text(encoding="utf-8")


def shannon_entropy(text: str) -> float:
    counts = Counter(text)
    total = len(text) or 1
    return -sum((count / total) * math.log2(count / total) for count in counts.values())


def profile(text: str) -> dict[str, object]:
    lines = text.splitlines()
    words = re.findall(r"[A-Za-zÀ-ÖØ-öø-ÿ0-9_/-]+", text)
    word_lengths = [len(word) for word in words] or [1]
    line_lengths = [len(line) for line in lines] or [1]
    punctuation = sum(1 for ch in text if ch in ".,;:!?/|=-_`()[]{}")
    whitespace = sum(1 for ch in text if ch.isspace())
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
    gate_counts = {token: len(re.findall(rf"\b{token}\b", text)) for token in ("OPEN", "HOLD", "KILL")}

    return {
        "sha256": digest,
        "chars": len(text),
        "lines": len(lines),
        "nonempty_lines": sum(1 for line in lines if line.strip()),
        "words": len(words),
        "unique_words": len({word.lower() for word in words}),
        "mean_word_len": sum(word_lengths) / len(word_lengths),
        "mean_line_len": sum(line_lengths) / len(line_lengths),
        "longest_line": max(line_lengths),
        "entropy": shannon_entropy(text),
        "punctuation": punctuation,
        "whitespace": whitespace,
        "gate_counts": gate_counts,
        "word_lengths": word_lengths,
        "line_lengths": line_lengths,
    }


def rule_from_digest(digest: str) -> int:
    base = int(digest[:2], 16)
    # Keep the automaton in a turbulent but legible band.
    return 73 + (base % 55)


def next_cellular_row(row: list[int], rule: int, salt: int) -> list[int]:
    out: list[int] = []
    width = len(row)
    for i in range(width):
        left = row[(i - 1) % width]
        mid = row[i]
        right = row[(i + 1) % width]
        pattern = (left << 2) | (mid << 1) | right
        bit = (rule >> pattern) & 1
        if (i * 17 + salt * 29) % 47 == 0:
            bit ^= 1
        out.append(bit)
    return out


def initial_row(digest: str, width: int) -> list[int]:
    bits = "".join(f"{byte:08b}" for byte in bytes.fromhex(digest))
    return [int(bits[(i * 7 + i * i) % len(bits)]) for i in range(width)]


def colorize(glyph: str, color_index: int, ansi: bool) -> str:
    if not ansi:
        return glyph
    color = PALETTE[color_index % len(PALETTE)]
    return f"\033[38;5;{color}m{glyph}{RESET}"


def glyph_for(value: float, ca: int, x: int, y: int, frame: int, prof: dict[str, object]) -> str:
    line_lengths = prof["line_lengths"]  # type: ignore[assignment]
    word_lengths = prof["word_lengths"]  # type: ignore[assignment]
    digest = prof["sha256"]  # type: ignore[assignment]
    char_seed = int(digest[(x + y + frame) % 64], 16)

    if (x * 31 + y * 17 + frame * 13) % 211 == 0:
        return "å"
    if (x + y * 3 + frame) % (29 + char_seed) == 0:
        return GATES[(x + y + frame) % len(GATES)]
    if ca and value > 0.78:
        return FRACTURE[(x * 5 + y * 7 + frame) % len(FRACTURE)]
    if value > 0.91:
        return SPARKS[(x + y + frame) % len(SPARKS)]
    if value < 0.12:
        return " "
    density_index = int(value * (len(GLYPH_RAMP) - 1))
    # Word and line rhythms perturb the ramp so the document profile becomes visible.
    rhythm = (line_lengths[y % len(line_lengths)] + word_lengths[(x + y) % len(word_lengths)]) % 3
    return GLYPH_RAMP[min(len(GLYPH_RAMP) - 1, density_index + rhythm)]


def render_field(text: str, frame: int, ansi: bool) -> list[str]:
    prof = profile(text)
    digest = prof["sha256"]  # type: ignore[assignment]
    entropy = float(prof["entropy"])
    punctuation = int(prof["punctuation"])
    chars = int(prof["chars"])
    words = int(prof["words"])

    width = 89
    height = 31
    rule = rule_from_digest(digest)
    row = initial_row(digest, width)

    # Advance cellular state by frame using prime salts; this avoids simple recurrence.
    for salt in range(frame % 97):
        row = next_cellular_row(row, rule, salt)

    out: list[str] = []
    for y in range(height):
        row = next_cellular_row(row, rule, y + frame)
        line_chars: list[str] = []
        for x in range(width):
            wave = math.sin((x * 0.1618 + y * 0.2718 + frame * 0.101) * PHI)
            spiral = math.sin(((x - width / 2) ** 2 + (y - height / 2) ** 2) * 0.013 + entropy)
            drift = math.sin((x * PRIMES[y % len(PRIMES)] + y * PRIMES[x % len(PRIMES)] + frame * 23) / (17 + entropy))
            hash_nibble = int(str(digest)[(x * 3 + y * 5 + frame) % 64], 16) / 15
            value = (wave + spiral + drift) / 6 + 0.5
            value = (value * 0.72) + (hash_nibble * 0.28)
            value += ((punctuation + x * y + words + chars) % 17) / 100
            value = max(0.0, min(1.0, value))
            glyph = glyph_for(value, row[x], x, y, frame, prof)
            color_index = int(value * (len(PALETTE) - 1)) + row[x] * 5 + y + frame
            line_chars.append(colorize(glyph, color_index, ansi))
        out.append("".join(line_chars))
    return out


def print_profile(text: str, ansi: bool) -> None:
    prof = profile(text)
    gate_counts = prof["gate_counts"]  # type: ignore[assignment]
    digest = prof["sha256"]  # type: ignore[assignment]
    rule = rule_from_digest(str(digest))
    title = "MATHEMATICAL PROFILE // COMMERCIAL CLAIM BOUNDARY"
    print(f"{esc('38;5;51', ansi)}{BOLD if ansi else ''}{title}{RESET if ansi else ''}")
    print(f"source=CLAIM_BOUNDARY.md")
    print(f"sha256={digest}")
    print(
        "lines={lines} nonempty={nonempty_lines} chars={chars} words={words} unique={unique_words}".format(**prof)
    )
    print(
        "mean_word_len={:.2f} mean_line_len={:.2f} longest_line={} entropy={:.4f}".format(
            float(prof["mean_word_len"]),
            float(prof["mean_line_len"]),
            int(prof["longest_line"]),
            float(prof["entropy"]),
        )
    )
    print(f"punctuation={prof['punctuation']} whitespace={prof['whitespace']} gates={gate_counts}")
    print(f"lattice=89x31 rule={rule} phase=phi cellular_salt=prime/xor")
    print()


def print_translation_note(ansi: bool) -> None:
    title = "TRANSLATION NOTE"
    print(f"\n{esc('38;5;190', ansi)}{BOLD if ansi else ''}{title}{RESET if ansi else ''}")
    print("Line lengths bend the horizontal pressure.")
    print("Word lengths perturb glyph density.")
    print("OPEN/HOLD/KILL become sparse gate sparks, not labels.")
    print("The document hash seeds a cellular field, then prime-salted drift prevents closed recurrence.")
    print("FINAL_SEAL=TERMINAL_ARTIFACT_COMMERCIAL_BOUNDARY_V0_1")


def main() -> int:
    parser = argparse.ArgumentParser(description="Render terminal art from commercial claim-boundary structure.")
    parser.add_argument("--frames", type=int, default=1, help="Number of frames to render.")
    parser.add_argument("--loop", action="store_true", help="Continue rendering until interrupted.")
    parser.add_argument("--plain", action="store_true", help="Disable ANSI colors.")
    parser.add_argument("--no-sleep", action="store_true", help="Do not pause between frames.")
    args = parser.parse_args()

    text = load_source()
    ansi = not args.plain
    print_profile(text, ansi)

    frame = 0
    try:
        while True:
            if args.frames > 1 or args.loop:
                print(f"{esc('38;5;244', ansi)}FRAME={frame:04d} // persistence_without_recurrence{RESET if ansi else ''}")
            print(f"{esc('38;5;240', ansi)}┌{'─' * 89}┐{RESET if ansi else ''}")
            for line in render_field(text, frame, ansi):
                print(f"{esc('38;5;240', ansi)}│{RESET if ansi else ''}{line}{esc('38;5;240', ansi)}│{RESET if ansi else ''}")
            print(f"{esc('38;5;240', ansi)}└{'─' * 89}┘{RESET if ansi else ''}")
            frame += 1
            if not args.loop and frame >= args.frames:
                break
            if not args.no_sleep:
                time.sleep(0.12)
        print_translation_note(ansi)
    except KeyboardInterrupt:
        print("\nDECISION=HOLD")
        print("REASON=INTERRUPTED_BY_OPERATOR")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
