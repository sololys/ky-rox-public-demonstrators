#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MODULE: registry_b_dlatch_telemetry_protocol.py
CLASSIFICATION: KY v1.5-MASTER // Registry B (HOLD -> L3 HIL) D-Latch Telemetry Protocol
STATE ANCHOR: 0xABCDEF00
EPISTEMIC BOUNDARY: INSPIRED_BY != IMPLEMENTS != PROVES

Håndhever den deterministiske maskinvare- og telemetriprotokollen for å måle fysisk
D-Latch-spenning (74HC74 / FPGA GPIO + INA226/ADS1115 ADC) og løse ut Registry B (HOLD):
  1. Eksplisitt skille: Kommandert spenning != Målt spenning. Uten fysisk ADC-telemetri
     forblir systemet låst i REGISTRY_B_HOLD (OPEN_AS_SOFTWARE_DEMONSTRATION).
  2. Fysiske elektriske vinduer (heltalls millivolt og mikroampere – ingen IEEE-754 drift):
       - OPEN (ACTIVE_LOAD)   : V_Q in [4750, 5250] mV og I_shunt in [500, 25000] uA
       - HOLD (HIGH_Z_TIMED)  : V_Q in [0, 50] mV og |I_shunt| <= 10 uA
       - KILL (LOW_Z_CROWBAR) : V_Q in [0, 50] mV, R_crowbar <= 10 Ohm og E_snubber_nJ > 0
  3. Kausal to-fase tidsorden:
       t(W_PRE) < t(CLK_rising_edge) < t(ADC_sample) < t(W_POST)
  4. 3-punkts fysisk overgangsbevis (Rest 0.00V -> Latch 5.00V -> Reset 0.00V) bundet til
     W_PRE-nonce, monoton maskinvareteller C_hw og nøkkelstyrt HMAC-SHA256 (Registry A).
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import hmac
import struct
from typing import Dict, Optional, Tuple


# 208-byte Rosetta v1.5 / Registry B Hardware Witness Envelope (Little-Endian)
# magic(4B: 0xABCDEF00) | version(2B) | gate_code(1B) | reg_b_state(1B)
# seq_c_hw(8B) | t_w_pre_ns(8B) | t_clk_ns(8B) | t_adc_ns(8B) | t_w_post_ns(8B)
# v_pre_rest_mv(4B int32) | v_q_measured_mv(4B int32) | v_post_reset_mv(4B int32)
# i_shunt_ua(4B int32) | r_crowbar_mohm(4B uint32) | e_snubber_nj(4B uint32)
# ky_ascii_digest(32B) | w_pre_hash(32B) | prev_envelope_hash(32B) | hmac_signature(40B padded / 32B + 8B tag)
ROSETTA_ENVELOPE_FORMAT = "<IHBBQQQQQiiiIII32s32s32s32s8s"
assert struct.calcsize(ROSETTA_ENVELOPE_FORMAT) == 208, (
    f"Rosetta v1.5 envelope must be 208 bytes, got {struct.calcsize(ROSETTA_ENVELOPE_FORMAT)}"
)

LOCUS_MAGIC = 0xABCDEF00
PROTOCOL_VERSION = 0x0105  # v1.5


@dataclass(frozen=True)
class PhysicalADCSample:
    """Rå heltallsmåling fra ekstern ADC (f.eks. INA226 / ADS1115) over fysisk D-Latch-utgang Q."""
    t_w_pre_ns: int
    t_clk_edge_ns: int
    t_adc_sample_ns: int
    t_w_post_ns: int
    v_pre_rest_mv: int       # Målt spenning før klokke-flanke (skal være 0..50 mV)
    v_q_measured_mv: int     # Målt spenning på Q etter klokke-flanke
    v_post_reset_mv: int     # Målt spenning etter CLR_N / crowbar reset (0..50 mV)
    i_shunt_ua: int          # Målt strøm gjennom lastshunt i mikroampere
    r_crowbar_mohm: int      # Målt utgangsimpedans mot jord ved KILL i milliohm
    e_snubber_nj: int        # Målt avledet energi i snubber/dump-motstand i nanojoule


@dataclass(frozen=True)
class RegistryBTelemetryVerdict:
    registry_b_status: str       # 'HOLD_SOFTWARE_DEMO_ONLY' | 'OPEN_L3_SILICON_WITNESSED' | 'KILL_INTERLOCK_MISMATCH' | 'KILL_CAUSAL_TIMING' | 'KILL_IMPEDANCE_FAULT'
    claim_classification: str    # 'OPEN_AS_SOFTWARE_DEMONSTRATION' | 'L3_SILICON_D_LATCH_WITNESSED' | 'FAIL_CLOSED_KILL'
    commanded_gate: str          # 'OPEN' | 'HOLD' | 'KILL'
    commanded_voltage_mv: int    # 5000 eller 0 mV
    measured_voltage_mv: Optional[int]
    measured_current_ua: Optional[int]
    impedance_verified: str      # 'UNMEASURED' | 'ACTIVE_LOAD' | 'HIGH_Z_TIMED' | 'LOW_Z_CROWBAR' | 'IMPEDANCE_BREACH'
    rosetta_envelope_208b: Optional[bytes]
    envelope_sha256: str
    reason: str


class RegistryBDLatchTelemetryVerifier:
    """
    Deterministisk protokollmotor for å løse ut Registry B (HOLD) ved fysisk
    D-Latch-spenningsmåling, eller tvinge systemet til HOLD/KILL ved fravær eller avvik.
    """

    # Elektriske grenseverdier i heltalls millivolt, mikroampere og milliohm
    V_OPEN_MIN_MV = 4750       # 4.75 V DC
    V_OPEN_MAX_MV = 5250       # 5.25 V DC
    I_OPEN_MIN_UA = 500        # 0.50 mA minimum reell laststrøm (avviser flytende pin)
    I_OPEN_MAX_UA = 25000      # 25.0 mA maksimum (74HC74 / FPGA I/O grense)

    V_ZERO_MAX_MV = 50         # <= 0.05 V DC (50 mV) for både HOLD og KILL
    I_HOLD_MAX_UA = 10         # <= 10 uA lekkasjestrøm i High-Z HOLD
    R_CROWBAR_MAX_MOHM = 10000 # <= 10.0 Ohm (10 000 mOhm) lavimpedant jording i KILL

    SETTLE_MIN_NS = 20         # Minimum 20 ns propagasjons- og settle-tid etter CLK-flanke
    SETTLE_MAX_NS = 5_000_000  # Maksimum 5 ms vindu før vaktbikkje-avbrudd

    def __init__(self, hmac_key: bytes = b"LOCUS_ZERO_0xABCDEF00_REGISTRY_B_KEY") -> None:
        self._hmac_key = hmac_key
        self.committed_c_hw: int = 0
        self.prev_envelope_hash: bytes = hashlib.sha256(b"REGISTRY_B_GENESIS_0xABCDEF00").digest()

    def evaluate_telemetry(
        self,
        seq_c_hw: int,
        commanded_gate: str,
        ky_canonical_ascii: str,
        w_pre_hash: bytes,
        adc_sample: Optional[PhysicalADCSample],
    ) -> RegistryBTelemetryVerdict:
        """
        Evaluerer om Registry B (HOLD) kan løses ut eller må forbli i HOLD / gå i KILL.
        """
        cmd_mv = 5000 if commanded_gate == "OPEN" else 0

        # 1. Kriterium 1: Uten fysisk ADC-måling er Registry B låst til HOLD (aldri fysisk OPEN)
        if adc_sample is None:
            return RegistryBTelemetryVerdict(
                registry_b_status="HOLD_SOFTWARE_DEMO_ONLY",
                claim_classification="OPEN_AS_SOFTWARE_DEMONSTRATION",
                commanded_gate=commanded_gate,
                commanded_voltage_mv=cmd_mv,
                measured_voltage_mv=None,
                measured_current_ua=None,
                impedance_verified="UNMEASURED",
                rosetta_envelope_208b=None,
                envelope_sha256="0" * 64,
                reason="Registry B (HOLD): No physical ADC telemetry attached; locked to OPEN_AS_SOFTWARE_DEMONSTRATION (0xABCDEF00).",
            )

        # 2. Monoton maskinvareteller C_hw (forhindrer replay av eldre telemetrilogger)
        if seq_c_hw <= self.committed_c_hw:
            return self._fail_kill(
                status="KILL_INTERLOCK_MISMATCH",
                commanded_gate=commanded_gate,
                cmd_mv=cmd_mv,
                adc=adc_sample,
                impedance="IMPEDANCE_BREACH",
                reason=f"Monotonic hardware counter replay: seq_c_hw={seq_c_hw} <= committed={self.committed_c_hw}",
            )

        # 3. Kriterium 3: Kausal tidsorden t(W_PRE) < t(CLK) < t(ADC) < t(W_POST)
        settle_ns = adc_sample.t_adc_sample_ns - adc_sample.t_clk_edge_ns
        if not (
            adc_sample.t_w_pre_ns < adc_sample.t_clk_edge_ns
            and self.SETTLE_MIN_NS <= settle_ns <= self.SETTLE_MAX_NS
            and adc_sample.t_adc_sample_ns < adc_sample.t_w_post_ns
        ):
            return self._fail_kill(
                status="KILL_CAUSAL_TIMING",
                commanded_gate=commanded_gate,
                cmd_mv=cmd_mv,
                adc=adc_sample,
                impedance="IMPEDANCE_BREACH",
                reason=f"Causal timing breach: require t_w_pre < t_clk < t_adc < t_w_post with settle in [20ns, 5ms] (got settle={settle_ns}ns)",
            )

        # 4. Sjekk at hvilespenning før klokke og etter reset er <= 50 mV (0.00 V DC baseline)
        if not (0 <= adc_sample.v_pre_rest_mv <= self.V_ZERO_MAX_MV and 0 <= adc_sample.v_post_reset_mv <= self.V_ZERO_MAX_MV):
            return self._fail_kill(
                status="KILL_IMPEDANCE_FAULT",
                commanded_gate=commanded_gate,
                cmd_mv=cmd_mv,
                adc=adc_sample,
                impedance="IMPEDANCE_BREACH",
                reason=f"Baseline 0.00V breach: v_pre_rest={adc_sample.v_pre_rest_mv}mV, v_post_reset={adc_sample.v_post_reset_mv}mV",
            )

        # 5. Kriterium 2: Evaluer fysisk spenning og impedans mot kommandert portdom
        if commanded_gate == "OPEN":
            v_ok = self.V_OPEN_MIN_MV <= adc_sample.v_q_measured_mv <= self.V_OPEN_MAX_MV
            i_ok = self.I_OPEN_MIN_UA <= adc_sample.i_shunt_ua <= self.I_OPEN_MAX_UA
            if not v_ok:
                return self._fail_kill(
                    status="KILL_INTERLOCK_MISMATCH",
                    commanded_gate=commanded_gate,
                    cmd_mv=cmd_mv,
                    adc=adc_sample,
                    impedance="IMPEDANCE_BREACH",
                    reason=f"INTERLOCK_MISMATCH: d_k=OPEN (5000mV), but measured V_Q={adc_sample.v_q_measured_mv}mV outside [4750, 5250]mV",
                )
            if not i_ok:
                return self._fail_kill(
                    status="KILL_IMPEDANCE_FAULT",
                    commanded_gate=commanded_gate,
                    cmd_mv=cmd_mv,
                    adc=adc_sample,
                    impedance="IMPEDANCE_BREACH",
                    reason=f"Floating/open-load fault: measured I_shunt={adc_sample.i_shunt_ua}uA outside [500, 25000]uA",
                )
            impedance_state = "ACTIVE_LOAD"
            gate_code = 0x01

        elif commanded_gate == "HOLD":
            v_ok = 0 <= adc_sample.v_q_measured_mv <= self.V_ZERO_MAX_MV
            i_ok = abs(adc_sample.i_shunt_ua) <= self.I_HOLD_MAX_UA
            if not (v_ok and i_ok):
                return self._fail_kill(
                    status="KILL_IMPEDANCE_FAULT",
                    commanded_gate=commanded_gate,
                    cmd_mv=cmd_mv,
                    adc=adc_sample,
                    impedance="IMPEDANCE_BREACH",
                    reason=f"HOLD High-Z breach: V_Q={adc_sample.v_q_measured_mv}mV, I_shunt={adc_sample.i_shunt_ua}uA",
                )
            impedance_state = "HIGH_Z_TIMED"
            gate_code = 0x02

        elif commanded_gate == "KILL":
            v_ok = 0 <= adc_sample.v_q_measured_mv <= self.V_ZERO_MAX_MV
            r_ok = 0 < adc_sample.r_crowbar_mohm <= self.R_CROWBAR_MAX_MOHM
            e_ok = adc_sample.e_snubber_nj > 0
            if not (v_ok and r_ok and e_ok):
                return self._fail_kill(
                    status="KILL_IMPEDANCE_FAULT",
                    commanded_gate=commanded_gate,
                    cmd_mv=cmd_mv,
                    adc=adc_sample,
                    impedance="IMPEDANCE_BREACH",
                    reason=(
                        f"KILL Low-Z crowbar/Landauer breach: V_Q={adc_sample.v_q_measured_mv}mV, "
                        f"R_crowbar={adc_sample.r_crowbar_mohm}mOhm, E_snubber={adc_sample.e_snubber_nj}nJ"
                    ),
                )
            impedance_state = "LOW_Z_CROWBAR"
            gate_code = 0x03

        else:
            return self._fail_kill(
                status="KILL_INTERLOCK_MISMATCH",
                commanded_gate=commanded_gate,
                cmd_mv=cmd_mv,
                adc=adc_sample,
                impedance="IMPEDANCE_BREACH",
                reason=f"Unknown commanded_gate: {commanded_gate}",
            )

        # 6. Kriterium 5: Pakk og signer 208-byte Rosetta v1.5 Hardware Witness Envelope (Registry A + B)
        ky_digest = hashlib.sha256(ky_canonical_ascii.encode("utf-8")).digest()
        reg_b_state = 0x01  # L3_SILICON_WITNESSED

        unsigned_prefix = struct.pack(
            "<IHBBQQQQQiiiIII32s32s32s",
            LOCUS_MAGIC,
            PROTOCOL_VERSION,
            gate_code,
            reg_b_state,
            seq_c_hw,
            adc_sample.t_w_pre_ns,
            adc_sample.t_clk_edge_ns,
            adc_sample.t_adc_sample_ns,
            adc_sample.t_w_post_ns,
            adc_sample.v_pre_rest_mv,
            adc_sample.v_q_measured_mv,
            adc_sample.v_post_reset_mv,
            adc_sample.i_shunt_ua,
            adc_sample.r_crowbar_mohm,
            adc_sample.e_snubber_nj,
            ky_digest,
            w_pre_hash,
            self.prev_envelope_hash,
        )
        mac_32 = hmac.new(self._hmac_key, unsigned_prefix, hashlib.sha256).digest()
        envelope_208b = unsigned_prefix + mac_32 + b"ROSETTA1"
        assert len(envelope_208b) == 208

        env_hash = hashlib.sha256(envelope_208b).digest()
        self.prev_envelope_hash = env_hash
        self.committed_c_hw = seq_c_hw

        return RegistryBTelemetryVerdict(
            registry_b_status="OPEN_L3_SILICON_WITNESSED",
            claim_classification="L3_SILICON_D_LATCH_WITNESSED",
            commanded_gate=commanded_gate,
            commanded_voltage_mv=cmd_mv,
            measured_voltage_mv=adc_sample.v_q_measured_mv,
            measured_current_ua=adc_sample.i_shunt_ua,
            impedance_verified=impedance_state,
            rosetta_envelope_208b=envelope_208b,
            envelope_sha256=env_hash.hex(),
            reason=f"Registry B resolved for seq={seq_c_hw}: physical ADC matches {commanded_gate} ({impedance_state}) in 208B Rosetta envelope.",
        )

    @staticmethod
    def _fail_kill(
        status: str,
        commanded_gate: str,
        cmd_mv: int,
        adc: PhysicalADCSample,
        impedance: str,
        reason: str,
    ) -> RegistryBTelemetryVerdict:
        return RegistryBTelemetryVerdict(
            registry_b_status=status,
            claim_classification="FAIL_CLOSED_KILL",
            commanded_gate=commanded_gate,
            commanded_voltage_mv=cmd_mv,
            measured_voltage_mv=adc.v_q_measured_mv,
            measured_current_ua=adc.i_shunt_ua,
            impedance_verified=impedance,
            rosetta_envelope_208b=None,
            envelope_sha256="0" * 64,
            reason=reason,
        )
