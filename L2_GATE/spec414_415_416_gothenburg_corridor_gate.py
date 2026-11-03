#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SOLOLYS // SPEC-414 (77 GHz ISAC), SPEC-415 (-240m K-POD) & SPEC-416 (INFRANETT) GATE VERIFIER
Release: v1.5.0-MASTER | State Anchor: 0xABCDEF00 | Zero-Dependency L1 Reference
Enforces:
  - KY D1.2 Orthogonality (Sigma_state intersect Sigma_suffix == empty) & Bijection
  - SPEC-414: Euclidean Phase Cone, Staggered-PRF Fine-Wilf Gate, Joseph-Form EKF PSD
  - SPEC-415: 5x Async CDC Locks, 145.0 dB SPL Sabotage Clamp, 532nm/UWB ToF Coherence
  - SPEC-416: Infranett Causal Witness (W_pre 119B -> W_post 86B = 205B), Exact Rational
              Kirchhoff Conservation (Delta_R == 0/1), 1550nm Fiber OTDR Tap Detection,
              IEEE 1588v2 PTP Sync (<= 100 ns), VSG 50 Hz Grid Stability & BFT Quorum
  - Registry A (KILL) & Registry B (HOLD // 0.00 V DC)
"""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
import hashlib
import math
import struct
import zlib
from typing import Tuple

# =============================================================================
# 0x00. CONSTANTS & EPISTEMIC STATES
# =============================================================================
STATE_ANCHOR_MAGIC: bytes = b"\xAB\xCD\xEF\x00"
ROSETTA_VERSION: int = 0x0105
ROSETTA_D3_FORMAT: str = ">4sHBBQ32s32s32s32s64s"  # Exact 208 bytes
HW_FRAME_PRE_BYTES: int = 119
HW_FRAME_POST_BYTES: int = 86
HW_FRAME_TOTAL_BYTES: int = 205

# Exact binary struct layouts for Infranett W_pre (119B) and W_post (86B):
# W_pre (119B): >4sQI3BqqIiQ32s36s = 4+8+4+3+8+8+4+4+8+32+36 = 119 bytes
INFRANETT_W_PRE_FORMAT: str = ">4sQI3BqqIiQ32s36s"
# W_post (86B): >Q32s32sIIHI = 8+32+32+4+4+2+4 = 86 bytes
INFRANETT_W_POST_FORMAT: str = ">Q32s32sIIHI"

CANONICAL_GLYPH: str = "✓(○ → ∅ → □ → ◇ → ●)#! ▸"
CANONICAL_ASCII: str = "validate(raw -> estimate -> struct -> viability -> committed)#! OPEN"

# Registry State Codes
REG_PASS: int = 0x01
REG_HOLD: int = 0x02
REG_KILL: int = 0xFF


# =============================================================================
# 0x01. KY D1.2 ORTHOGONAL GRAMMAR & BIJECTION ENGINE
# =============================================================================
class KYGrammarGate:
    """Enforces Alternative A: Sigma_state intersect Sigma_suffix == empty."""

    _GLYPH_TO_ASCII_MAP = {
        "✓(": "validate(",
        "○": "raw",
        "∅": "estimate",
        "□": "struct",
        "◇": "viability",
        "●": "committed",
        "→": "->",
        ")#!": ")#!",
        "▸": "OPEN",
    }

    @classmethod
    def verify_orthogonality_and_bijection(cls, glyph_str: str) -> Tuple[int, str]:
        if ")" not in glyph_str:
            return REG_KILL, "MISSING_CLOSING_PAREN"
        _, suffix = glyph_str.split(")", 1)
        if "●" in suffix:
            return REG_KILL, "ORTHOGONALITY_VIOLATION_DOT_IN_SUFFIX"
        if not suffix.startswith("#!"):
            return REG_KILL, "INVALID_COMMIT_SUFFIX"

        ascii_str = cls.to_ascii(glyph_str)
        roundtrip_glyph = cls.from_ascii(ascii_str)
        if roundtrip_glyph != glyph_str or ascii_str != CANONICAL_ASCII:
            return REG_KILL, "D1_2_BIJECTION_FAILURE"
        return REG_PASS, ascii_str

    @classmethod
    def to_ascii(cls, glyph_str: str) -> str:
        out = glyph_str
        for g, a in cls._GLYPH_TO_ASCII_MAP.items():
            out = out.replace(g, a)
        return out

    @classmethod
    def from_ascii(cls, ascii_str: str) -> str:
        out = ascii_str
        for g, a in sorted(cls._GLYPH_TO_ASCII_MAP.items(), key=lambda x: -len(x[1])):
            out = out.replace(a, g)
        return out


# =============================================================================
# 0x02. SPEC-414 // 77 GHz ISAC RADAR & STAGGERED-PRF GATE
# =============================================================================
@dataclass(frozen=True)
class Spec414Telemetry:
    z_real: Tuple[Fraction, ...]
    z_imag: Tuple[Fraction, ...]
    w_real: Tuple[Fraction, ...]
    w_imag: Tuple[Fraction, ...]
    cos2_theta_max: Fraction
    prf_multipliers: Tuple[int, ...]
    base_clock_dt_ns: int
    target_velocity_mps: Fraction
    ekf_cov_2x2: Tuple[Tuple[Fraction, Fraction], Tuple[Fraction, Fraction]]
    ekf_trace_max: Fraction


class Spec414IsacGate:
    """Evaluates Euclidean Phase Cone, Fine-Wilf Blind Velocity, and Joseph EKF PSD."""

    WAVELENGTH_77GHZ_M: Fraction = Fraction(299_792_458, 77_000_000_000)

    @classmethod
    def evaluate(cls, t: Spec414Telemetry) -> Tuple[int, str, int]:
        if not (len(t.z_real) == len(t.z_imag) == len(t.w_real) == len(t.w_imag) > 0):
            return REG_KILL, "SPEC414_DIMENSION_MISMATCH", 0

        inner_re = sum(zr * wr + zi * wi for zr, zi, wr, wi in zip(t.z_real, t.z_imag, t.w_real, t.w_imag))
        inner_im = sum(zi * wr - zr * wi for zr, zi, wr, wi in zip(t.z_real, t.z_imag, t.w_real, t.w_imag))
        norm_inner_sq = inner_re * inner_re + inner_im * inner_im

        norm_z_sq = sum(zr * zr + zi * zi for zr, zi in zip(t.z_real, t.z_imag))
        norm_w_sq = sum(wr * wr + wi * wi for wr, wi in zip(t.w_real, t.w_imag))

        if norm_z_sq == 0 or norm_w_sq == 0:
            return REG_KILL, "SPEC414_ZERO_ENERGY_VECTOR", 0

        if norm_inner_sq < norm_z_sq * norm_w_sq * t.cos2_theta_max:
            return REG_HOLD, "SPEC414_PHASE_CONE_VIOLATION", 0

        if len(t.prf_multipliers) < 2 or any(n <= 0 for n in t.prf_multipliers):
            return REG_KILL, "SPEC414_INVALID_PRF_MULTIPLIERS", 0

        g = t.prf_multipliers[0]
        for n in t.prf_multipliers[1:]:
            g = math.gcd(g, n)
        if g != 1:
            return REG_KILL, "SPEC414_FINE_WILF_NON_COPRIME_KILL", 0

        dt_sec = Fraction(t.base_clock_dt_ns, 1_000_000_000)
        v_blind_synth = cls.WAVELENGTH_77GHZ_M / (2 * dt_sec)
        if abs(t.target_velocity_mps) >= v_blind_synth:
            return REG_KILL, "SPEC414_BLIND_VELOCITY_ALIASING_KILL", 0

        p00, p01 = t.ekf_cov_2x2[0]
        p10, p11 = t.ekf_cov_2x2[1]
        det_p = p00 * p11 - p01 * p10
        trace_p = p00 + p11

        if p01 != p10 or p00 <= 0 or det_p <= 0:
            return REG_KILL, "SPEC414_EKF_NON_PSD_KILL", 0
        if trace_p > t.ekf_trace_max:
            return REG_HOLD, "SPEC414_EKF_COVARIANCE_DRIFT_HOLD", 0

        fine_wilf_horizon = sum(t.prf_multipliers) - (len(t.prf_multipliers) - 1)
        return REG_PASS, "SPEC414_ISAC_NOMINAL", fine_wilf_horizon


# =============================================================================
# 0x03. SPEC-415 // -240m BENTHIC K-POD & 5-CDC INTERLOCK GATE
# =============================================================================
@dataclass(frozen=True)
class Spec415Telemetry:
    cdc_sync_locked: Tuple[bool, bool, bool, bool, bool]
    hydrostatic_pressure_mpa: Fraction
    acoustic_spl_db: Fraction
    range_532nm_m: Fraction
    range_uwb_m: Fraction
    max_tof_divergence_m: Fraction
    adc_timestamp_ns: int
    clk_timestamp_ns: int
    shunt_current_ua: int


class Spec415KpodGate:
    """Evaluates 5x CDC locks, 145.0 dB SPL sabotage limit, Optical/UWB ToF, and Reg B."""

    SABOTAGE_SPL_HOLD_DB: Fraction = Fraction(1450, 10)
    SABOTAGE_SPL_KILL_DB: Fraction = Fraction(1600, 10)
    MIN_PRESSURE_MPA: Fraction = Fraction(200, 100)
    MAX_PRESSURE_MPA: Fraction = Fraction(300, 100)
    MIN_SHUNT_UA: int = 500

    @classmethod
    def evaluate(cls, t: Spec415Telemetry) -> Tuple[int, str]:
        if len(t.cdc_sync_locked) != 5 or not all(t.cdc_sync_locked):
            return REG_HOLD, "SPEC415_CDC_METASTABILITY_HOLD"

        if t.acoustic_spl_db >= cls.SABOTAGE_SPL_KILL_DB:
            return REG_KILL, "SPEC415_ACOUSTIC_SHOCKWAVE_KILL"
        if t.acoustic_spl_db >= cls.SABOTAGE_SPL_HOLD_DB:
            return REG_HOLD, "SPEC415_ACOUSTIC_SABOTAGE_145DB_HOLD"

        if not (cls.MIN_PRESSURE_MPA <= t.hydrostatic_pressure_mpa <= cls.MAX_PRESSURE_MPA):
            return REG_HOLD, "SPEC415_BENTHIC_PRESSURE_OUT_OF_BOUNDS_HOLD"

        if abs(t.range_532nm_m - t.range_uwb_m) > t.max_tof_divergence_m:
            return REG_HOLD, "SPEC415_OPTICAL_UWB_TOF_DIVERGENCE_HOLD"

        if t.adc_timestamp_ns < t.clk_timestamp_ns or t.shunt_current_ua < cls.MIN_SHUNT_UA:
            return REG_HOLD, "OPEN_AS_SOFTWARE_DEMONSTRATION_0.00V_DC"

        return REG_PASS, "SPEC415_L3_HARDWARE_WITNESSED_OPEN"


# =============================================================================
# 0x04. SPEC-416 // INFRANETT CAUSAL WITNESS (W_pre -> W_post) & GRID/FIBER GATE
# =============================================================================
@dataclass(frozen=True)
class Spec416InfranettTelemetry:
    seq_c: int                                # Strictly monotonic counter C > C_hw
    committed_c_hw: int                       # Last committed hardware counter C_hw
    node_id: int                              # Infranett substation / fiber node ID
    flows_in_mw: Tuple[Fraction, ...]         # Injected nodal power/flow vectors
    flows_out_mw: Tuple[Fraction, ...]        # Extracted nodal power/flow + line loss
    fiber_attenuation_db_km: Fraction         # 1550 nm OTDR Rayleigh attenuation (<= 0.250 dB/km)
    fiber_step_loss_db: Fraction              # Local splice/bend step loss (<= 0.050 dB)
    grid_freq_hz: Fraction                    # Synchronous frequency [49.500, 50.500] Hz
    rocof_hz_per_s: Fraction                  # Rate of Change of Frequency |df/dt| <= 2.0 Hz/s
    ptp_offset_ns: int                        # IEEE 1588v2 PTP phase offset |dt| <= 100 ns
    bft_signatures_valid: int                 # Verified BFT nodal warrants
    bft_fault_tolerance_f: int                # Max Byzantine nodes f (requires >= 2f + 1)
    prev_w_post_sha256: bytes                 # 32B hash of previous committed W_post
    matrix_hash_32b: bytes                    # H(Matrix) for TOCTOU binding
    logic_hash_32b: bytes                     # H(Logic) for TOCTOU binding
    execution_hash_32b: bytes                 # H(Execution) for TOCTOU binding
    adc_timestamp_ns: int                     # Physical ADC sampling timestamp
    clk_timestamp_ns: int                     # D-Latch reference clock edge timestamp
    shunt_current_ua: int                     # Physical actuator loop current (uA)


class Spec416InfranettGate:
    """
    Evaluates SPEC-416 Infranett Critical Infrastructure invariants and compiles
    the causal witness pair (W_pre [119B] -> W_post [86B] = 205B) with TOCTOU
    interlock and Registry B (0.00 V DC rest state).
    """

    MAX_FIBER_ATTEN_DB_KM: Fraction = Fraction(250, 1000)   # 0.250 dB/km @ 1550nm
    MAX_FIBER_STEP_HOLD_DB: Fraction = Fraction(50, 1000)   # 0.050 dB micro-bend tap
    MAX_FIBER_STEP_KILL_DB: Fraction = Fraction(1000, 1000) # 1.000 dB fiber cut/clamp
    MIN_GRID_FREQ_HZ: Fraction = Fraction(495, 10)          # 49.5 Hz
    MAX_GRID_FREQ_HZ: Fraction = Fraction(505, 10)          # 50.5 Hz
    MAX_ROCOF_HZ_S: Fraction = Fraction(20, 10)             # 2.0 Hz/s
    MAX_PTP_OFFSET_NS: int = 100                            # +/- 100 ns IEEE 1588v2
    MIN_SHUNT_UA: int = 500                                 # 500 uA Registry B threshold

    @classmethod
    def evaluate_and_seal_w_pre_w_post(
        cls,
        t: Spec416InfranettTelemetry,
        in_memory_mutated_execution_hash: bytes | None = None,
    ) -> Tuple[int, str, bytes, bytes, bytes]:
        """
        Returns (gate_code, reason, w_pre_119b, w_post_86b, frame_205b).
        """
        # 1. Monotonic Anti-Replay Counter (C > C_hw)
        if t.seq_c <= t.committed_c_hw:
            return cls._pack_verdict(t, REG_KILL, "SPEC416_MONOTONIC_REPLAY_KILL", in_memory_mutated_execution_hash)

        # 2. Exact Rational Kirchhoff Conservation (Delta_R == 0/1 in Q)
        delta_r: Fraction = sum(t.flows_in_mw, Fraction(0, 1)) - sum(t.flows_out_mw, Fraction(0, 1))
        if delta_r != Fraction(0, 1):
            return cls._pack_verdict(t, REG_KILL, "SPEC416_KIRCHHOFF_IMBALANCE_KILL", in_memory_mutated_execution_hash)

        # 3. 1550 nm Optical Fiber OTDR Tap / Intrusion Detection
        if t.fiber_step_loss_db >= cls.MAX_FIBER_STEP_KILL_DB:
            return cls._pack_verdict(t, REG_KILL, "SPEC416_FIBER_SEVERED_OR_CLAMP_KILL", in_memory_mutated_execution_hash)
        if t.fiber_attenuation_db_km > cls.MAX_FIBER_ATTEN_DB_KM or t.fiber_step_loss_db > cls.MAX_FIBER_STEP_HOLD_DB:
            return cls._pack_verdict(t, REG_HOLD, "SPEC416_FIBER_OTDR_INTRUSION_HOLD", in_memory_mutated_execution_hash)

        # 4. IEEE 1588v2 PTP Coherent Timing Window (|dt_PTP| <= 100 ns)
        if abs(t.ptp_offset_ns) > cls.MAX_PTP_OFFSET_NS:
            return cls._pack_verdict(t, REG_HOLD, "SPEC416_PTP_PHASE_DRIFT_HOLD", in_memory_mutated_execution_hash)

        # 5. VSG Synchronous Grid Frequency, RoCoF & Multiplicative BFT Quorum (2f + 1)
        if abs(t.rocof_hz_per_s) > cls.MAX_ROCOF_HZ_S:
            return cls._pack_verdict(t, REG_KILL, "SPEC416_GRID_ROCOF_COLLAPSE_KILL", in_memory_mutated_execution_hash)
        if not (cls.MIN_GRID_FREQ_HZ <= t.grid_freq_hz <= cls.MAX_GRID_FREQ_HZ):
            return cls._pack_verdict(t, REG_HOLD, "SPEC416_GRID_FREQ_DEVIATION_HOLD", in_memory_mutated_execution_hash)
        required_quorum = 2 * t.bft_fault_tolerance_f + 1
        if t.bft_signatures_valid < required_quorum:
            return cls._pack_verdict(t, REG_HOLD, "SPEC416_BFT_QUORUM_INSUFFICIENT_HOLD", in_memory_mutated_execution_hash)

        # 6. TOCTOU Causal Binding Check between W_pre and W_post
        expected_exec_digest = hashlib.sha256(
            t.matrix_hash_32b + t.logic_hash_32b + t.execution_hash_32b
        ).digest()
        actual_exec_hash = (
            in_memory_mutated_execution_hash
            if in_memory_mutated_execution_hash is not None
            else t.execution_hash_32b
        )
        actual_exec_digest = hashlib.sha256(
            t.matrix_hash_32b + t.logic_hash_32b + actual_exec_hash
        ).digest()
        if actual_exec_digest != expected_exec_digest:
            return cls._pack_verdict(t, REG_KILL, "SPEC416_TOCTOU_TRANSIT_MUTATION_KILL", in_memory_mutated_execution_hash)

        # 7. Registry B: Physical D-Latch Telemetry Gate (Default Rest State = 0.00 V DC)
        if t.adc_timestamp_ns < t.clk_timestamp_ns or t.shunt_current_ua < cls.MIN_SHUNT_UA:
            return cls._pack_verdict(
                t,
                REG_HOLD,
                "OPEN_AS_SOFTWARE_DEMONSTRATION_0.00V_DC",
                in_memory_mutated_execution_hash,
            )

        return cls._pack_verdict(
            t,
            REG_PASS,
            "SPEC416_INFRANETT_L3_WITNESSED_OPEN",
            in_memory_mutated_execution_hash,
        )

    @classmethod
    def _pack_verdict(
        cls,
        t: Spec416InfranettTelemetry,
        gate_code: int,
        reason: str,
        mutated_exec_hash: bytes | None,
    ) -> Tuple[int, str, bytes, bytes, bytes]:
        delta_r: Fraction = sum(t.flows_in_mw, Fraction(0, 1)) - sum(t.flows_out_mw, Fraction(0, 1))
        atten_mdb = int(round(float(t.fiber_attenuation_db_km) * 1000))
        freq_mhz = int(round(float(t.grid_freq_hz) * 1000))

        pre_commitment_seed = hashlib.sha256(
            t.matrix_hash_32b + t.logic_hash_32b + t.execution_hash_32b
        ).digest()
        w_pre_tail_36b = pre_commitment_seed + STATE_ANCHOR_MAGIC

        w_pre_119b = struct.pack(
            INFRANETT_W_PRE_FORMAT,
            STATE_ANCHOR_MAGIC,
            t.seq_c,
            t.node_id,
            gate_code,
            t.bft_signatures_valid & 0xFF,
            t.bft_fault_tolerance_f & 0xFF,
            delta_r.numerator,
            delta_r.denominator,
            atten_mdb,
            freq_mhz,
            t.ptp_offset_ns & 0xFFFFFFFFFFFFFFFF,
            t.prev_w_post_sha256,
            w_pre_tail_36b,
        )
        assert len(w_pre_119b) == HW_FRAME_PRE_BYTES

        w_pre_sha256 = hashlib.sha256(w_pre_119b).digest()
        exec_leaf = mutated_exec_hash if mutated_exec_hash is not None else t.execution_hash_32b
        post_exec_digest = hashlib.sha256(
            w_pre_sha256 + t.matrix_hash_32b + t.logic_hash_32b + exec_leaf
        ).digest()

        adc_delta_ns = max(0, t.adc_timestamp_ns - t.clk_timestamp_ns)
        w_post_without_crc = struct.pack(
            ">Q32s32sIIH",
            t.seq_c,
            w_pre_sha256,
            post_exec_digest,
            adc_delta_ns,
            t.shunt_current_ua,
            gate_code,
        )
        crc32_val = zlib.crc32(w_pre_119b + w_post_without_crc) & 0xFFFFFFFF
        w_post_86b = struct.pack(
            INFRANETT_W_POST_FORMAT,
            t.seq_c,
            w_pre_sha256,
            post_exec_digest,
            adc_delta_ns,
            t.shunt_current_ua,
            gate_code,
            crc32_val,
        )
        assert len(w_post_86b) == HW_FRAME_POST_BYTES

        frame_205b = w_pre_119b + w_post_86b
        assert len(frame_205b) == HW_FRAME_TOTAL_BYTES
        return gate_code, reason, w_pre_119b, w_post_86b, frame_205b


# =============================================================================
# 0x05. 205B HARDWARE CAPSULE & 208B ROSETTA D3 ENVELOPE PACKER
# =============================================================================
def pack_205b_hardware_capsule(
    seq: int,
    spec414_status: int,
    spec415_status: int,
    fw_horizon: int,
    shunt_ua: int,
) -> bytes:
    """Packs exact 119B WitnessPreCommit + 86B WitnessPostCommit = 205B RTL Frame."""
    pre_header = struct.pack(
        ">4sQBBHI",
        STATE_ANCHOR_MAGIC,
        seq,
        spec414_status,
        spec415_status,
        fw_horizon,
        shunt_ua,
    )
    pre_pad = hashlib.sha256(pre_header).digest() * 4
    witness_pre_119b = (pre_header + pre_pad)[:HW_FRAME_PRE_BYTES]

    post_digest = hashlib.sha256(witness_pre_119b).digest()
    post_header = struct.pack(">Q32s", seq, post_digest)
    post_pad = hashlib.sha512(post_header).digest()
    witness_post_86b = (post_header + post_pad)[:HW_FRAME_POST_BYTES]

    frame_205b = witness_pre_119b + witness_post_86b
    assert len(frame_205b) == HW_FRAME_TOTAL_BYTES, "FATAL_205B_FRAME_SIZE_VIOLATION"
    return frame_205b


def pack_208b_rosetta_d3(
    reg_a: int,
    reg_b: int,
    monotonic_seq: int,
    prev_chain_hash: bytes,
    glyph_str: str,
    ascii_str: str,
    ed25519_pubkey_32b: bytes,
    ed25519_sig_64b: bytes,
) -> bytes:
    """Packs exact 208-byte Rosetta D3 Envelope (>4sHBBQ32s32s32s32s64s)."""
    if len(prev_chain_hash) != 32 or len(ed25519_pubkey_32b) != 32 or len(ed25519_sig_64b) != 64:
        raise ValueError("ROSETTA_D3_FIELD_WIDTH_VIOLATION")

    glyph_sha = hashlib.sha256(glyph_str.encode("utf-8")).digest()
    ascii_sha = hashlib.sha256(ascii_str.encode("utf-8")).digest()

    envelope = struct.pack(
        ROSETTA_D3_FORMAT,
        STATE_ANCHOR_MAGIC,
        ROSETTA_VERSION,
        reg_a,
        reg_b,
        monotonic_seq,
        prev_chain_hash,
        glyph_sha,
        ascii_sha,
        ed25519_pubkey_32b,
        ed25519_sig_64b,
    )
    assert len(envelope) == 208, "FATAL_208B_ROSETTA_SIZE_VIOLATION"
    return envelope
