import time
import hashlib
import json

# ─── IMMUTABLE WITNESS STORE ───
class WitnessLog:
    def __init__(self):
        self.records = {}  # object_id -> record data [cite: 131-132]
        self.events = []   # Liste over hash-lenkede hendelser [cite: 141]
        self.last_event_hash = "0000000000000000000000000000000000000000000000000000000000000000"

    def write_record(self, object_id, node, status, failure_code=None):
        """ Lagrer den nåværende tilstanden til et objekt [cite: 131-132] """
        self.records[object_id] = {
            "object_id": object_id, # [cite: 133]
            "lifecycle_state": node.state, # [cite: 134]
            "gate_status": status, # [cite: 135]
            "admissibility_flag": node.admissibility_flag, # [cite: 136]
            "audit_pass": node.audit_pass, # [cite: 137]
            "reproducible": node.reproducible, # [cite: 138]
            "failure_code": failure_code, # [cite: 139]
            "integrity_hash": node.integrity_hash # [cite: 140]
        }

    def log_event(self, object_id, operation, result, reason_code="SUCCESS"):
        """ Genererer en ny event og lenker den kryptografisk til forrige event [cite: 141-145] """
        event_id = len(self.events) + 1 # [cite: 142]
        timestamp = int(time.time()) # [cite: 149]
        
        # Bygg datagrunnlag for hashing
        event_data = f"{event_id}:{object_id}:{self.last_event_hash}:{operation}:{result}:{timestamp}"
        sha = hashlib.sha256()
        sha.update(event_data.encode('utf-8'))
        current_hash = sha.hexdigest() # [cite: 145]

        event_entry = {
            "event_id": event_id, # [cite: 142]
            "object_id": object_id, # [cite: 143]
            "prev_hash": self.last_event_hash, # [cite: 144]
            "event_hash": current_hash, # [cite: 145]
            "operation": operation, # [cite: 146]
            "result": result, # [cite: 147]
            "reason_code": reason_code, # [cite: 148]
            "timestamp": timestamp # [cite: 149]
        }
        
        self.events.append(event_entry)
        self.last_event_hash = current_hash  # Oppdater lenken til neste blokk [cite: 144]
        return current_hash

# ─── ENGINE DEFINISJON ───
class Node:
    def __init__(self, raw_input):
        self.raw_input = raw_input
        self.state = "RAW" # [cite: 96, 483]
        self.admissibility_flag = True # [cite: 136]
        self.structure_valid = True
        self.hash_chain_valid = True
        self.reproducible = True # [cite: 138]
        self.audit_pass = True # [cite: 137]
        self.uncertainty_high = False
        self.integrity_hash = None

class KYEngine:
    def __init__(self):
        self.witness = WitnessLog()

    def Phi(self, raw_input):
        node = Node(raw_input)
        node.state = "ESTIMATE" # [cite: 97, 483]
        return node

    def Pi_K(self, node):
        node.state = "STRUCT" # [cite: 98, 483]
        if "infinite gold" in node.raw_input.lower():
            node.admissibility_flag = False # [cite: 266-272]
        
        sha = hashlib.sha256()
        sha.update(f"{node.raw_input}:{node.state}".encode('utf-8'))
        node.integrity_hash = sha.hexdigest() # [cite: 140]
        
        node.state = "VIABILITY" # [cite: 99, 483]
        return node

    def Omega(self, node):
        if not node.structure_valid or not node.hash_chain_valid or not node.admissibility_flag:
            return "KILL" # [cite: 116-120, 532-533]
        if not node.reproducible or not node.audit_pass:
            return "KILL" # [cite: 121-122, 534-535]
        return "OPEN" # [cite: 126, 536]

    def process_event(self, object_id, raw_input):
        # x_{t+1} = Omega(Pi_K(Phi(x_t))) [cite: 66, 464, 515, 579]
        candidate = self.Phi(raw_input)
        structured = self.Pi_K(candidate)
        decision = self.Omega(structured)

        if decision == "OPEN": # [cite: 151-152]
            structured.state = "COMMITTED" # [cite: 100, 483]
            self.witness.write_record(object_id, structured, "OPEN")
            self.witness.log_event(object_id, "COMMIT_FRAME", "SUCCESS")
            print(f"✅ COMMITTED: '{raw_input}' lagret i uforanderlig tidslinje.")
        else:
            structured.state = "KILL"
            self.witness.write_record(object_id, structured, "KILL", failure_code="ADMISSIBILITY_BREACH")
            self.witness.log_event(object_id, "TERMINATE_TRANSITION", "REJECTED", reason_code="RULE_VIOLATION")
            print(f"❌ KILLED: '{raw_input}' avvist. Feil logget i Witness.")

# ─── SIMULERING ───
if __name__ == "__main__":
    engine = KYEngine()
    
    # Kjør hendelser
    engine.process_event("OBJ_001", "Build a bridge of light over the gap")
    engine.process_event("OBJ_002", "Spawn infinite gold")
    
    # Print ut den uforanderlige Witness-loggen
    print("\n--- SYSTEM WITNESS EVENT LOG (CRYPTOGRAPHIC CHAIN) ---")
    print(json.dumps(engine.witness.events, indent=2))
