#!/usr/bin/env python3
import json
import hashlib
import uuid
from datetime import datetime

class StandaloneTrapCore:
    def __init__(self):
        # Isolert lager for fangede sesjoner (G_shadow)
        self.shadow_registry = {}

    def execute_route(self, actor_id, payload, t_trigger):
        """
        Ren TRAP-operator isolert fra Sosionomos.
        T(a) = 1 => route(c) = G_shadow
        """
        candidate_id = f"cand_{uuid.uuid4().hex[:8]}"
        
        if t_trigger == 1:
            # EKSTRAKSJON: Fanget i speilrommet
            session_id = f"shadow_sess_{uuid.uuid4().hex[:6]}"
            self.shadow_registry[candidate_id] = {
                "actor_id": actor_id,
                "session_id": session_id,
                "payload": payload,
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }
            
            # local_ACK != public_consequence
            return {
                "verdict": "TRAP",
                "routing": f"G_shadow_isolated_env",
                "client_response": {
                    "local_ACK": True,
                    "status": "SUCCESS",
                    "msg": "Operation completed.",
                    "receipt_hash": hashlib.sha256(json.dumps(payload).encode()).hexdigest()
                }
            }
        
        # Hvis T(a) = 0, slipper kandidaten gjennom til vanlig ekstern prosessering
        return {
            "verdict": "PASS",
            "routing": "G_public",
            "client_response": {"local_ACK": False, "status": "FORWARDED"}
        }

if __name__ == "__main__":
    trap_core = StandaloneTrapCore()
    
    print("="*80)
    print("KY-ROX — EXTRACTED TRAP CORE RUNTIME")
    print("="*80)
    
    # Test 1: Normal aktør (Slipper igjennom for ekstern validering)
    print("[RUN] Processing normal actor...")
    res_normal = trap_core.execute_route("user_123", {"action": "PAY", "amount": 100}, t_trigger=0)
    print(f"  Verdict: {res_normal['verdict']} -> Routed to: {res_normal['routing']}")
    
    print("-" * 60)
    
    # Test 2: Adversariell bot (Isoleres fullstendig, får falsk suksess-kvittering)
    print("[RUN] Processing malicious bot...")
    res_bot = trap_core.execute_route("bot_net_99", {"action": "SPAM_ATTACK", "payload": "xyz"}, t_trigger=1)
    print(f"  Verdict: {res_bot['verdict']} -> Routed to: {res_bot['routing']}")
    print(f"  Faked Client Feedback: {json.dumps(res_bot['client_response'])}")
    print("="*80)
