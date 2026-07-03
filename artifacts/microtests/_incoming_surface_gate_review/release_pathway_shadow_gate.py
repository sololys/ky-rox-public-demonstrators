#!/usr/bin/env python3
import json
import hashlib
from datetime import datetime

class ReleasePathwayShadowGate:
    def __init__(self):
        # Konfigurasjon og terskler (Formelle gaten-betingelser)
        self.R_allowed = ["RADIO_XRAY", "FINANCIAL_LEDGER_ROUTE", "AUTHORIZED_API_VENT"]
        self.M_min = 0.85   # Minimum midtbåndsundertrykkelse (85%)
        self.S_max = 0.05   # Maksimalt tillatt timing-avvik/drift (5%)
        self.prev_witness_hash = "sha256:d813fa2a9bc4f30b91e9f45687bdedcb"

    def evaluate_gate(self, candidate_id, telemetry):
        """
        Kjerneoperator: E-TOR Consequence Gate
        OPEN iff R(c_t) in R_allowed AND M(c_t) >= M_min AND S_T(c_t) <= S_max AND W == READY
        """
        pathway = telemetry.get("R")
        suppression = telemetry.get("M")
        drift = telemetry.get("S_T")
        witness_ready = telemetry.get("W_READY", False)
        energy_present = telemetry.get("ENERGY_PRESENT", False)

        # 1. Integritets- og lekkasjesjekk (Harde KILL-kriterier)
        if suppression < self.M_min:
            return "KILL", "KILL_MIDDLE_BAND_LEAKAGE: Core energy leaking into unauthorized spectrum."

        # 2. Adversariell eller feilet ruting (TRAP/HOLD-kriterier)
        if pathway not in self.R_allowed:
            if energy_present:
                return "HOLD", "HOLD_ENERGY_NO_PATHWAY: High energy detected but no authorized release pathway found."
            return "HOLD", "UNMAPPED_ROUTE: No valid channel target."

        # 3. Timing-stabilitet
        if drift > self.S_max:
            return "HOLD", "HOLD_TIMING_DRIFT: Clock drift/jitter exceeds stable boundaries."

        # 4. Forseglingsklarhet (Witness Barrier)
        if not witness_ready:
            return "HOLD", "WITNESS_UNAVAILABLE: Gate cannot guarantee immutable proof."

        # Dersom alle betingelser er tilfredsstilt
        return "OPEN", "OPEN_ALLOWED_DUAL_RELEASE: Geometry validates routing pathway."

    def generate_witness_record(self, candidate_id, verdict, reason, telemetry):
        """Kryptografisk append-only beviskjording"""
        event = {
            "candidate_id": candidate_id,
            "verdict": verdict,
            "reason_code": reason.split(":")[0],
            "context_hash": hashlib.sha256(str(telemetry).encode('utf-8')).hexdigest(),
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "prev_hash": self.prev_witness_hash
        }
        
        canonical_event = json.dumps(event, sort_keys=True)
        event_hash = hashlib.sha256(canonical_event.encode('utf-8')).hexdigest()
        event["witness_hash"] = f"sha256:{event_hash}"
        
        # Roter kjede-ankeret lokalt for neste tidssteg
        self.prev_witness_hash = event["witness_hash"]
        return event

def run_demonstrator():
    gate = ReleasePathwayShadowGate()
    
    # Definerte test-cases i henhold til spesifikasjon
    test_cases = {
        "CASE_1: OPEN_ALLOWED_DUAL_RELEASE": {
            "ENERGY_PRESENT": True,
            "R": "RADIO_XRAY",
            "M": 0.98,        # God margin over M_min (0.85)
            "S_T": 0.01,      # Stabil timing godt under S_max (0.05)
            "W_READY": True
        },
        "CASE_2: HOLD_ENERGY_NO_PATHWAY": {
            "ENERGY_PRESENT": True,
            "R": "BROADBAND_PHOTOSPHERIC_LEAK", # Ikke en godkjent rute
            "M": 0.90,
            "S_T": 0.02,
            "W_READY": True
        },
        "CASE_3: KILL_MIDDLE_BAND_LEAKAGE": {
            "ENERGY_PRESENT": True,
            "R": "RADIO_XRAY",
            "M": 0.42,        # Kritisk lekkasje i uautorisert bånd (0.42 < 0.85)
            "S_T": 0.01,
            "W_READY": True
        },
        "CASE_4: HOLD_TIMING_DRIFT": {
            "ENERGY_PRESENT": True,
            "R": "RADIO_XRAY",
            "M": 0.95,
            "S_T": 0.14,      # Jitter/Drift er for høy (0.14 > 0.05)
            "W_READY": True
        }
    }

    print("="*80)
    print("KY-ROX CONSEQUENCE GATE — RUNTIME RUN: release_pathway_shadow_gate_v0_1")
    print("="*80)

    for case_name, telemetry in test_cases.items():
        print(f"\n[EXECUTE] Evaluates {case_name}...")
        candidate_id = f"cand_{hashlib.md5(case_name.encode()).hexdigest()[:8]}"
        
        # Kjør port-evaluering
        verdict, reason = gate.evaluate_gate(candidate_id, telemetry)
        
        # Generer uforanderlig vitnespor
        witness_record = gate.generate_witness_record(candidate_id, verdict, reason, telemetry)
        
        print(f"  VERDICT     : {verdict}")
        print(f"  REASON      : {reason}")
        print(f"  WITNESS HASH: {witness_record['witness_hash']}")
        print(f"  PREV HASH   : {witness_record['prev_hash']}")
        print("-" * 60)

if __name__ == "__main__":
    run_demonstrator()
