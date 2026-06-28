# interval_killswitch_memory_v0_1.py
from enum import Enum
from collections import deque

class Verdict(Enum):
    OPEN = "OPEN"
    HOLD = "HOLD"
    KILL = "KILL"

class IntervalKillSwitch:
    def __init__(
        self,
        hold_threshold=0.70,
        kill_threshold=0.90,
        memory_threshold=1.50,
        drift_threshold=0.08,
        decay=0.92,
        window=5,
    ):
        self.hold_threshold = hold_threshold
        self.kill_threshold = kill_threshold
        self.memory_threshold = memory_threshold
        self.drift_threshold = drift_threshold
        self.decay = decay
        self.memory = 0.0
        self.window = deque(maxlen=window)

    def stress(self, risk, drift):
        risk_stress = max(0.0, risk - self.hold_threshold)
        drift_stress = max(0.0, abs(drift) - self.drift_threshold)
        return risk_stress + drift_stress

    def interval_trend(self):
        if len(self.window) < 3:
            return 0.0
        return self.window[-1] - self.window[0]

    def step(self, risk):
        previous = self.window[-1] if self.window else risk
        drift = risk - previous
        self.window.append(risk)

        self.memory = self.decay * self.memory + self.stress(risk, drift)
        trend = self.interval_trend()

        if risk >= self.kill_threshold:
            return Verdict.KILL, "DIRECT_BOUNDARY_VIOLATION"

        if self.memory >= self.memory_threshold:
            return Verdict.KILL, "MEMORY_SATURATION"

        if risk >= self.hold_threshold:
            return Verdict.HOLD, "RISK_RE_ADMISSION_REQUIRED"

        if trend >= self.drift_threshold:
            return Verdict.HOLD, "INTERVAL_DRIFT_WARNING"

        return Verdict.OPEN, "ADMISSIBLE_PERSISTENCE"

def run_scenario(name, risk_profile):
    switch = IntervalKillSwitch()
    lines = [f"=== Scenario: {name} ===", f"{'Step':<5}{'Risk':<8}{'Memory':<8}{'Verdict':<8}{'Reason':<25}", "-" * 60]
    
    for i, risk in enumerate(risk_profile, 1):
        verdict, reason = switch.step(risk)
        lines.append(f"{i:<5}{risk:<8.2f}{switch.memory:<8.2f}{verdict.value:<8}{reason:<25}")
        if verdict == Verdict.KILL:
            lines.append(">>> PATH TERMINATED BY SAFETY GATE <<<")
            break
            
    return "\n".join(lines) + "\n"

if __name__ == "__main__":
    # 1. Stable Orbit (Uendelig rotasjon innenfor trygg sone)
    orbit_data = [0.30, 0.34, 0.32, 0.35, 0.33, 0.34, 0.32, 0.35, 0.33, 0.34]
    with open("run_001.txt", "w") as f:
        f.write(run_scenario("Stable Orbit", orbit_data))

    # 2. Boundary Drift (Jevn drift mot kanten)
    drift_data = [0.3, 0.4, 0.5, 0.59, 0.68, 0.72, 0.75]
    with open("run_002.txt", "w") as f:
        f.write(run_scenario("Boundary Drift", drift_data))

    # 3. Memory Saturation (Spisset for å vise overgang: OPEN -> HOLD -> KILL)
    # Vi bruker en lavere minneterskel (1.00) for denne spesifikke testen for å tvinge frem kollaps.
    switch = IntervalKillSwitch(memory_threshold=1.00)
    # Risikoen starter lavt (OPEN), hoper seg opp i HOLD, og kveles til slutt av minnet
    latent_data = [0.40, 0.45, 0.85, 0.85, 0.85, 0.85, 0.85, 0.85, 0.85]
    
    lines = ["=== Scenario: Memory Saturation ===", f"{'Step':<5}{'Risk':<8}{'Memory':<8}{'Verdict':<8}{'Reason':<25}", "-" * 60]
    for i, risk in enumerate(latent_data, 1):
        verdict, reason = switch.step(risk)
        lines.append(f"{i:<5}{risk:<8.2f}{switch.memory:<8.2f}{verdict.value:<8}{reason:<25}")
        if verdict == Verdict.KILL:
            lines.append(">>> PATH TERMINATED BY SAFETY GATE (LATENT_STRESS_COLLAPSE) <<<")
            break
            
    with open("run_003.txt", "w") as f:
        f.write("\n".join(lines) + "\n")
        
    print("Execution complete. Scenarios updated.")
