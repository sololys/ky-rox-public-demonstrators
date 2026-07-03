#!/usr/bin/env python3
import json
import hashlib
import math
from datetime import datetime

class KerrProjectionGate:
    def __init__(self, M=1.0, a=0.5):
        self.M = M
        self.a = a
        if self.a <= self.M:
            self.r_plus = self.M + math.sqrt(self.M**2 - self.a**2)
        else:
            self.r_plus = None
            
        self.prev_witness_hash = "sha256:857e716dd5a5386758c8d2b65cedc0f3"

    def evaluate_trajectory(self, r, theta, a_current, telemetry):
        if a_current > self.M:
            return "KILL", "KILL_NAKED_SINGULARITY: Overspin a > M. Horizon structure collapsed."

        r_plus_current = self.M + math.sqrt(self.M**2 - a_current**2) if a_current <= self.M else 0
        r_ergosphere = self.M + math.sqrt(self.M**2 - (a_current**2) * (math.cos(theta)**2))
        
        delta_K = telemetry.get("delta_K", 0.0)
        if telemetry.get("causal_class", -1) == 1 or delta_K > 0.05:
            return "KILL", "KILL_METRIC_VIOLATION: Invariant breakdown."

        if r <= r_plus_current:
            return "COMMIT", f"COMMIT_HORIZON_CROSSING: Passed r_+ ({r_plus_current:.2f}). Locked into history fiber."

        if r_plus_current < r <= r_ergosphere:
            return "TRAP", f"TRAP_ERGOSPHERE_ENTRAINMENT: Inside ergosfære boundary ({r_ergosphere:.2f}). Frame-dragging locked."

        return "OPEN", "OPEN_SUSTAINED_ORBIT: Trajectory forward-invariant admissible outside ergosfære."

    def generate_witness_post(self, verdict, reason, r, theta):
        event = {
            "gate": "E-TOR:KERR_PROJECTION",
            "verdict": verdict,
            "reason_code": reason.split(":")[0],
            "coordinates": {"r": r, "theta": theta},
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "prev_hash": self.prev_witness_hash
        }
        canonical = json.dumps(event, sort_keys=True)
        self.prev_witness_hash = f"sha256:{hashlib.sha256(canonical.encode()).hexdigest()}"
        return event

def run_simulation():
    # Én felles port-instans for hele kjøringen sikrer ubrutt hashkjede
    gate = KerrProjectionGate(M=1.0)
    
    cases = {
        "CASE_1: OPEN_SUSTAINED_ORBIT": {
            "a": 0.4, "r": 4.0, "theta": math.pi/2, "telemetry": {"delta_K": 0.001, "causal_class": -1}
        },
        "CASE_2: TRAP_ERGOSPHERE_ZONE": {
            "a": 0.8, "r": 1.7, "theta": math.pi/2, "telemetry": {"delta_K": 0.01, "causal_class": -1} # r=1.7 er i TRAP
        },
        "CASE_3: KILL_NAKED_SINGULARITY": {
            "a": 1.2, "r": 2.0, "theta": math.pi/2, "telemetry": {"delta_K": 0.0, "causal_class": -1}
        },
        "CASE_4: COMMIT_HORIZON_CROSSING": {
            "a": 0.5, "r": 1.1, "theta": math.pi/2, "telemetry": {"delta_K": 0.002, "causal_class": -1}
        }
    }

    print("="*80)
    print("KY-ROX KERR GATING — RUNTIME RUN: sequential_chain_v0.2")
    print("="*80)

    for name, config in cases.items():
        print(f"\n[EXECUTE] {name}")
        verdict, reason = gate.evaluate_trajectory(config["r"], config["theta"], config["a"], config["telemetry"])
        witness = gate.generate_witness_post(verdict, reason, config["r"], config["theta"])
        
        print(f"  VERDICT     : {verdict}")
        print(f"  REASON      : {reason}")
        print(f"  WITNESS HASH: {gate.prev_witness_hash}")
        print(f"  PREV HASH   : {witness['prev_hash']}")
        print("-" * 60)
    print("="*80)

if __name__ == "__main__":
    run_simulation()
