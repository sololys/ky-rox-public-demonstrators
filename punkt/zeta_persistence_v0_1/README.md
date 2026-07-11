# ζβ // Persistence Without Recurrence v0.1

`zeta_persistence.py` is a deterministic animated terminal artwork derived from
a mathematical document fingerprint:

| Signal | Value | Visual role |
|---|---:|---|
| Pages | 71 | spatial twist modulus |
| Main sections | 8 | angular flow zones |
| Appendices | 2 | counter-rotating palettes |
| Equations | 190 | interference and rupture frequencies |

The terminal field combines a Sine-beta-inspired puncture lattice, a diagonal
Dirac-like spine, a breathing determinant shell, and prime-weighted spectral
interference. The upper and lower half-planes use asymmetric color fields.

Its frame phase is

$$
t_n = n\varphi^{-1} + \frac{\log(1+n)}{19}
      + \frac{0.071(n^2 \bmod 71)}{71}.
$$

The irrational and logarithmic components prevent the complete rendered state
from being governed by a finite modular clock. Local motifs may return without
requiring identical global frames.

## Run

```bash
python3 zeta_persistence.py
```

Stop with `Ctrl+C`. The program uses only the Python standard library. Set
`NO_COLOR=1` for monochrome output.

## Verify

```bash
python3 -m unittest -v
python3 probe.py
diff -u EXPECTED_OUTPUT.txt <(python3 probe.py)
sha256sum -c CHECKSUMS.sha256
```

The probe fixes the terminal to `80 × 24` before hashing frames 0 and 1.

## Status

`DETERMINISTIC TERMINAL ART / PUBLIC DEMONSTRATOR / NO EXTERNAL ACTUATION`

This artifact is a generative visualization, not a numerical experiment, proof
of a spectral theorem, random process, or production decision system. See
`SURFACE.md`.
