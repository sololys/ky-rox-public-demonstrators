import time
import hashlib
import json

class FinanceWitnessLog:
    def __init__(self):
        self.records = {}
        self.events = []
        self.last_event_hash = "0000000000000000000000000000000000000000000000000000000000000000"

    def write_record(self, tx_id, state, gate_status, admissibility, audit, reproducible, fail_code=None):
        """ Skriver transaksjonsstatus til arkivet [cite: 131-140] """
        self.records[tx_id] = {
            "object_id": tx_id,
            "lifecycle_state": state,
            "gate_status": gate_status,
            "admissibility_flag": admissibility,
            "audit_pass": audit,
            "reproducible": reproducible,
            "failure_code": fail_code
        }

    def log_event(self, tx_id, operation, result, reason="SUCCESS"):
        """ Hash-lenker finanshendelsen permanent [cite: 141-149] """
        event_id = len(self.events) + 1
        timestamp = int(time.time())
        
        event_data = f"{event_id}:{tx_id}:{self.last_event_hash}:{operation}:{result}:{timestamp}"
        sha = hashlib.sha256()
        sha.update(event_data.encode('utf-8'))
        current_hash = sha.hexdigest()

        self.events.append({
            "event_id": event_id,
            "object_id": tx_id,
            "prev_hash": self.last_event_hash,
            "event_hash": current_hash,
            "operation": operation,
            "result": result,
            "reason_code": reason,
            "timestamp": timestamp
        })
        self.last_event_hash = current_hash

class KYFinanceEngine:
    def __init__(self):
        self.witness = FinanceWitnessLog()
        self.max_limit = 500000  # Maksgrense for automatisk godkjenning uten manuell audit

    def Phi(self, raw_tx):
        """ Proposals-generatoren """
        raw_tx["state"] = "ESTIMATE"
        return raw_tx

    def Pi_K(self, tx):
        """ Strukturerer og validerer transaksjonsintegritet mot forretningsregler """
        tx["state"] = "STRUCT"
        tx["admissibility_flag"] = True
        tx["audit_pass"] = True
        tx["reproducible"] = True
        
        # Sjekk om beløpet krever utvidet manuell/ekstern audit
        if tx["amount"] > self.max_limit and not tx.get("has_compliance_signature", False):
            tx["audit_pass"] = False  # Markeres som ikke godkjent audit
            
        # Sjekk mot mistenkelig oppførsel (Admissibility)
        if tx["amount"] <= 0:
            tx["admissibility_flag"] = False
            
        tx["state"] = "VIABILITY"
        return tx

    def Omega(self, tx):
        """ Porten som nekter computational momentum å flytte penger ved en feil """
        if not tx["admissibility_flag"]:
            return "KILL"  # [cite: 116-120, 532-533]
        if not tx["audit_pass"]:
            return "HOLD"  # [cite: 123-124, 536]
        return "OPEN"  # [cite: 126, 536]

    def process_transaction(self, tx_id, raw_data):
        print(f"\n--- PROPOSING TRANSACTION {tx_id}: {raw_data['amount']} NOK ---")
        
        # x_{t+1} = Omega(Pi_K(Phi(x_t)))
        candidate = self.Phi(raw_data)
        structured = self.Pi_K(candidate)
        decision = self.Omega(structured)

        if decision == "OPEN":
            structured["state"] = "COMMITTED"  # [cite: 105, 510]
            self.witness.write_record(tx_id, "COMMITTED", "OPEN", True, True, True)
            self.witness.log_event(tx_id, "TRANSFER_EXECUTE", "SUCCESS")
            print(f"✅ TRANSACTION OPENED & COMMITTED: Beløp overført.")
        elif decision == "HOLD":
            structured["state"] = "VIABILITY"
            self.witness.write_record(tx_id, "VIABILITY", "HOLD", True, False, True, "MANUAL_AUDIT_REQUIRED")
            self.witness.log_event(tx_id, "SUSPEND_TRANSACTION", "HELD", "AUDIT_REQUIRED")
            print(f"⏳ TRANSACTION HELD: Beløpet overstiger grensen. Venter på compliance-signatur.")
        elif decision == "KILL":
            structured["state"] = "KILL"
            self.witness.write_record(tx_id, "KILL", "KILL", False, False, True, "INVALID_VALUE")
            self.witness.log_event(tx_id, "TERMINATE_TRANSACTION", "REJECTED", "ADMISSIBILITY_BREACH")
            print(f"❌ TRANSACTION KILLED: Ulovlig verdi avvist av porten.")

if __name__ == "__main__":
    engine = KYFinanceEngine()
    
    # Transaksjon 1: Normal overføring innenfor grenser
    engine.process_transaction("TX_901", {"amount": 25000})
    
    # Transaksjon 2: Stor overføring som krever manuell audit (Faller til HOLD) [cite: 123-124]
    engine.process_transaction("TX_902", {"amount": 1200000})
    
    # Transaksjon 3: Ulovlig beløp (Brutalt drept)
    engine.process_transaction("TX_903", {"amount": -500})
    
    # Skriv ut tidslinjen
    print("\n--- FINANCE RUNTIME GOVERNANCE LOG ---")
    print(json.dumps(engine.witness.events, indent=2))
