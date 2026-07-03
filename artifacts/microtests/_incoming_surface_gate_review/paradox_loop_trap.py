#!/usr/bin/env python3
import json
import hashlib
import uuid
from datetime import datetime

class ParadoxResonatorTrap:
    def __init__(self):
        self.shadow_registry = {}
        self.theta_PR = 0.54  # Kritisk terskel for ontologisk kollaps (LZ-PR-054)
        self.prev_witness_hash = "sha256:9a5dd7480c1c845adddd8757293894a1"

    def execute_secured_route(self, actor_id, payload, t_trigger, loop_cycles=0):
        """
        Integrert Core: TrapCore + Paradoks-Resonator (PR)
        Sikrer speilrommet mot utmattelse eller uendelige løkker.
        """
        candidate_id = f"cand_{uuid.uuid4().hex[:8]}"
        
        if t_trigger == 1:
            # Beregn entropi-gradienten basert på antall løkkekall i speilrommet
            grad_h = min(loop_cycles * 0.09, 1.0)
            
            session_data = {
                "actor_id": actor_id,
                "payload": payload,
                "grad_h": grad_h,
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }
            
            # PARADOKS-RESONATOR SIKRING: Sjekk mot den kritiske terskelen 0.54
            if grad_h >= self.theta_PR:
                verdict = "TRAP:TERMINAL_ISOLATION"
                reason = f"PR_CRIT_REACHED: grad_h ({grad_h:.2f}) >= {self.theta_PR}. Frakobling og dissipasjon iverksatt."
                client_response = {
                    "local_ACK": True,
                    "status": "TERMINATED",
                    "msg": "Session isolated due to emerging dissonance."
                }
            else:
                verdict = "TRAP:RESONATE"
                reason = f"PR_ABSORB_LOOP: Selvmotsigelse vibrerer trygt i lukket fasedomene. grad_h = {grad_h:.2f}."
                client_response = {
                    "local_ACK": True,
                    "status": "SUCCESS",
                    "msg": "Operation completed."
                }
            
            self.shadow_registry[candidate_id] = session_data
            witness = self.generate_witness_event(candidate_id, verdict, reason, session_data)
            return verdict, reason, client_response, witness
            
        return "PASS", "G_public granted.", {"local_ACK": False, "status": "FORWARDED"}, {}

    def generate_witness_event(self, candidate_id, verdict, reason, data):
        event = {
            "candidate_id": candidate_id,
            "verdict": verdict,
            "reason_code": reason.split(":")[0],
            "context_hash": hashlib.sha256(str(data).encode()).hexdigest(),
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "prev_hash": self.prev_witness_hash
        }
        event_hash = hashlib.sha256(json.dumps(event, sort_keys=True).encode()).hexdigest()
        event["witness_hash"] = f"sha256:{event_hash}"
        self.prev_witness_hash = event["witness_hash"]
        return event

if __name__ == "__main__":
    pr_trap = ParadoxResonatorTrap()
    
    test_cases = {
        "CASE_1: NORMAL_ACTOR": {"t": 0, "cycles": 0, "payload": {"action": "READ"}},
        "CASE_2: CONTROLLED_PARADOX_LOOP": {"t": 1, "cycles": 4, "payload": {"loop": "IF P THEN NOT P"}},
        "CASE_3: INFINITE_LOOP_CRISIS": {"t": 1, "cycles": 8, "payload": {"loop": "WHILE TRUE DO STACK_OVERFLOW"}}
    }
    
    print("="*80)
    print("KY-ROX — PARADOX RESONATOR & TRAP INTEGRATION RUNTIME")
    print("="*80)
    
    for name, config in test_cases.items():
        print(f"\n[EXECUTE] {name}")
        verd, reas, client_resp, wit = pr_trap.execute_secured_route(
            actor_id="actor_node_x",
            payload=config["payload"],
            t_trigger=config["t"],
            loop_cycles=config["cycles"]
        )
        print(f"  VERDICT     : {verd}")
        print(f"  REASON      : {reas}")
        print(f"  CLIENT FEEDBACK: {json.dumps(client_resp)}")
        if wit:
            print(f"  WITNESS HASH: {wit.get('witness_hash')}")
    print("="*80)
