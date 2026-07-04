import time
import json
import random

class GKOVRSystem:
    def __init__(self, username):
        self.username = username
        self.system_mode = "Normal" # [cite: 52]
        self.stimuli_level = 1.0     # Full styrke (grafikk/lyd/tempo)
        self.history = []
        self.total_regulations = 0   # [cite: 21, 55]

    def calculate_stability_index(self, telemetry):
        """ 
        Beregner SI (0.0 - 1.0) basert på standard maskinvaredata[cite: 16, 51].
        Bruker ingen biometrikk – kun ren interaksjonsintegritet[cite: 12, 47].
        """
        # Simulert formel basert på støy i hodebevegelse og reaksjons-jitter
        jitter = telemetry["head_jitter"] * 0.6 + telemetry["reaction_delay"] * 0.4
        si = 1.0 - min(max(jitter, 0.0), 1.0)
        return round(si, 2)

    def evaluate_policy(self, si):
        """ Deterministisk policy-motor uten ML (v0.1) [cite: 48] """
        old_mode = self.system_mode
        
        if si > 0.7:
            self.system_mode = "Normal" # [cite: 17, 52]
            self.stimuli_level = 1.0    # Full oppgaveflyt [cite: 17, 52]
        elif 0.4 < si <= 0.7:
            self.system_mode = "Regulering" # [cite: 18, 52]
            self.stimuli_level = 0.5        # Demper lyd, snevrer fokus, senker tempo [cite: 18, 52]
        else:
            self.system_mode = "Kritisk" # [cite: 19, 52]
            self.stimuli_level = 0.1     # Minimal stimuli, bevare ren orientering [cite: 19, 52]

        if self.system_mode != old_mode:
            print(f"⚠️ [POLICY] Systemmodus endret: {old_mode} ➔ {self.system_mode} (SI: {si})")
            if self.system_mode in ["Regulering", "Kritisk"]:
                self.total_regulations += 1 # [cite: 21, 55]

    def run_telemetry_tick(self, tick, telemetry):
        si = self.calculate_stability_index(telemetry)
        self.evaluate_policy(si)
        
        # Logg tilstanden internt for sesjonsrapporten
        self.history.append({
            "tick": tick,
            "stability_index": si,
            "mode": self.system_mode,
            "stimuli_level": self.stimuli_level
        })

    def generate_session_report(self):
        """ Hovedproduktet: Objektiv JSON-beslutningsstøtte uten diagnose [cite: 21-22, 54] """
        total_ticks = len(self.history)
        time_in_task = total_ticks * 2 # Hvert tick er 2 sekunder i denne simuleringen
        
        report = {
            "session_meta": {
                "user_id_hash": hashlib.sha256(self.username.encode()).hexdigest()[:12],
                "architecture_version": "GKO-VR_v0.1_Baseline" # [cite: 35]
            },
            "functional_metrics": {
                "time_in_task_seconds": time_in_task, # [cite: 21, 55]
                "total_regulations_triggered": self.total_regulations, # [cite: 21, 55]
                "final_system_status": self.system_mode
            },
            "stability_trend": [h["stability_index"] for h in self.history] # [cite: 21, 55]
        }
        return json.dumps(report, indent=2)

import hashlib # Importert for anonymisering av metadata

if __name__ == "__main__":
    print("🚀 Starter GKO VR v0.1 – Scenario: Ryddig Arbeidsbord [cite: 56-57]")
    session = GKOVRSystem(username="Marius")
    
    # Simulert tidslinje: Bruker starter rolig, blir stresset/sliten, og henter seg inn igjen
    simulated_telemetry = [
        {"head_jitter": 0.1, "reaction_delay": 0.1}, # Slapp og fin flyt
        {"head_jitter": 0.15, "reaction_delay": 0.12},
        {"head_jitter": 0.45, "reaction_delay": 0.5},  # Begynnende stress/kognitiv last
        {"head_jitter": 0.75, "reaction_delay": 0.8},  # Kritisk nivå – høy ustabilitet
        {"head_jitter": 0.3, "reaction_delay": 0.2},   # Systemet har dempet stimuli, brukeren roer seg
        {"head_jitter": 0.1, "reaction_delay": 0.1}
    ]

    for index, data in enumerate(simulated_telemetry):
        print(f"\n[Tick {index + 1}] Leser standard VR-data...") # [cite: 12, 47]
        session.run_telemetry_tick(index + 1, data)
        time.sleep(0.5)

    print("\n💾 Økt ferdig. Genererer GKO_SessionReport.json... [cite: 53-54]")
    report_json = session.generate_session_report()
    
    # Lagre filen til disk
    with open("GKO_SessionReport.json", "w") as f:
        f.write(report_json)
        
    print(report_json)
