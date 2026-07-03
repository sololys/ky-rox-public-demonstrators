#!/usr/bin/env python3
import json
import hashlib
import math
from datetime import datetime

class ThreeBodyAdmissibilityGate:
    def __init__(self, epsilon=0.01, d_crash=0.1):
        self.epsilon = epsilon      # Maksimalt tillatt energidrift (1%)
        self.d_crash = d_crash      # Fysisk kollisjonsgrense
        self.prev_witness_hash = "sha256:7ad3c5580c1af4e12629b1f0ef9c8da3"

    def evaluate_system(self, telemetry):
        """
        Kjerneoperator: E-TOR Three-Body Gate
        Sjekker om den kaotiske generatoren leverer en fysisk realiserbar bane.
        """
        delta_E = telemetry.get("delta_E", 0.0)      # Målt energidrift
        min_distance = telemetry.get("min_dist", 1.0) # Korteste avstand mellom legemer
        is_resonance = telemetry.get("is_resonance", False)
        
        # 1. Kollisjonssjekk (Hard materiell kollaps)
        if min_distance <= self.d_crash:
            return "KILL", f"KILL_COLLISION_CRISIS: Inter-body distance ({min_distance:.3f}) <= d_crash ({self.d_crash})."

        # 2. Energikonservering (Noether-brudd)
        if delta_E > self.epsilon:
            return "HOLD", f"HOLD_ENERGY_DRIFT: Energy variance ({delta_E:.4f}) exceeds threshold ({self.epsilon}). Regularization required."

        # 3. Resonans-ruting (Lagrange eller stabile periodiske løkker)
        if is_resonance:
            return "TRAP", "TRAP_RESONANCE_LOCK: Trajectory entrained in a stable, closed coordinate loop."

        return "OPEN", "OPEN_SUSTAINED_ORBIT: Trajectory satisfies total invariant conservation."

    def generate_witness_record(self, case_id, verdict, reason, telemetry):
        event = {
            "gate": "E-TOR:THREE_BODY_ADMISSIBILITY",
            "case_id": case_id,
            "verdict": verdict,
            "reason_code": reason.split(":")[0],
            "telemetry_hash": hashlib.sha256(str(telemetry).encode()).hexdigest(),
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "prev_hash": self.prev_witness_hash
        }
        canonical = json.dumps(event, sort_keys=True)
        self.prev_witness_hash = f"sha256:{hashlib.sha256(canonical.encode()).hexdigest()}"
        return event

def run_simulation():
    gate = ThreeBodyAdmissibilityGate()
    
    cases = {
        "CASE_1: LAGRANGE_L4_ORBIT": {
            "delta_E": 0.0002, "min_dist": 1.414, "is_resonance": True
        },
        "CASE_2: CHAOTIC_EJECTION_DRIFT": {
            "delta_E": 0.0450, "min_dist": 0.850, "is_resonance": False # delta_E > 0.01
        },
        "CASE_3: BINARY_COLLISION_EVENT": {
            "delta_E": 0.0010, "min_dist": 0.042, "is_resonance": False # min_dist <= 0.1
        },
        "CASE_4: nominal_stable_trajectory": {
            "delta_E": 0.0030, "min_dist": 2.110, "is_resonance": False
        }
    }

    print("="*80)
    print("KY-ROX THREE-BODY GATING — RUNTIME RUN: three_body_admissibility_gate_v0_1")
    print("="*80)

    for name, telemetry in cases.items():
        print(f"\n[EXECUTE] Evaluating {name}...")
        verdict, reason = gate.evaluate_system(telemetry)
        witness = gate.generate_witness_record(name, verdict, reason, telemetry)
        
        print(f"  VERDICT     : {verdict}")
        print(f"  REASON      : {reason}")
        print(f"  WITNESS HASH: {gate.prev_witness_hash}")
        print(f"  PREV HASH   : {witness['prev_hash']}")
        print("-" * 60)
    print("="*80)

if __name__ == "__main__":
    run_simulation()
