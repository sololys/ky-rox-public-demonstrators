import math
import cmath

# ─── 1. DISKRET RFM-CELLE (XOR-BASERT INVOLUSJON) ───
class DiscreteRFMCell:
    def __init__(self, initial_state: int, mask: int):
        self.anchor = initial_state  # Det uforanderlige Phase A-ankeret
        self.state = initial_state   # Den aktive registertilstanden (s)
        self.mask = mask
        self.phase = "A"

    def F(self, s: int) -> int:
        return s ^ self.mask

    def transition_to_phase_b(self):
        """ Flytter systemet til PHASE B via koordinatskift """
        self.state = self.F(self.state)
        self.phase = "B"

    def run_roundtrip_coherence_test(self) -> bool:
        """ Verifiserer om returbanen fra PHASE B rekonstruerer det opprinnelige ankeret """
        if self.phase == "B":
            return self.F(self.state) == self.anchor
        return self.F(self.F(self.state)) == self.anchor


# ─── 2. KONTINUERLIG RFM-CELLE (PHASOR-MINNE MED STØYTERSKEL) ───
class ReversiblePhasorMemory:
    def __init__(self, initial_angle_deg: float, epsilon: float = 0.05):
        self.epsilon = epsilon  # Isometrisk feilmargin
        self.reset_to_phase_a(initial_angle_deg)

    def reset_to_phase_a(self, angle_deg: float):
        self.theta = math.radians(angle_deg)
        self.anchor = cmath.exp(1j * self.theta)  # Opprinnelig Phase A-anker
        self.state = self.anchor
        self.phase = "A"

    def F(self, s: complex) -> complex:
        """ Involusjon i det komplekse planet: Konjugasjon """
        return s.conjugate()

    def transition_to_phase_b_with_noise(self, thermal_noise: complex):
        """ Utfører transformasjon og injiserer støy i Phase B-registeret """
        self.state = self.F(self.anchor) + thermal_noise
        self.phase = "B"

    def run_phasor_coherence_test(self) -> tuple[bool, float]:
        """ Måler avviket mellom returtilstanden og det opprinnelige ankeret """
        if self.phase == "B":
            returned_state = self.F(self.state)
            distance = abs(returned_state - self.anchor)
        else:
            distance = abs(self.F(self.F(self.state)) - self.anchor)
        
        is_coherent = distance <= self.epsilon #
        return is_coherent, round(distance, 4)


# ─── SIMULERING AV KJERNELOVENE ───
if __name__ == "__main__":
    print("─── KY-ROX: REVERSIBELT FASEMINNE (RFM) DEMONSTRATOR ───\n")

    # --- TEST 1: Perfekt diskret operasjon ---
    print("[TEST 1] Initialiserer diskret RFM-celle (Struktur: 0b101010)...")
    cell = DiscreteRFMCell(initial_state=0b101010, mask=0b111111)
    cell.transition_to_phase_b()
    
    if cell.run_roundtrip_coherence_test():
        print(" ✅ Roundtrip Coherence OK: F(F(s)) == s. Tilstanden bærer retur.\n")
    else:
        print(" ❌ SCL-X TRIGGER: Avvik detektert.\n")

    # --- TEST 2: Maskinvarefeil / Bit-flip deteksjon ---
    print("[TEST 2] Introduserer uforutsigbart avvik (Bit-flip i lagringsregister)...")
    cell.state = cell.state ^ 0b000001  # Register-korrupsjon i PHASE B
    
    print(" -> Evaluerer roundtrip etter register-korrupsjon...")
    if cell.run_roundtrip_coherence_test():
        print(" ✅ Roundtrip Coherence OK.\n")
    else:
        print(" ❌ ─── HPIS / SCL-X DUMP ───")
        print("    Entropi detektert i prøverommet! Strømmen kuttes momentant til 0 V.")
        print("    Ingen try/catch-blokk. Kun et brutt kretsløp. Systemet er låst.\n")

    # --- TEST 3: Kontinuerlig Phasor-minne under termisk støy ---
    print("[TEST 3] Initialiserer Reversible Phasor-Memory (Toleranse epsilon = 0.05)...")
    phasor = ReversiblePhasorMemory(initial_angle_deg=45.0, epsilon=0.05)
    
    # Kjøring A: Akseptabel støy
    acceptable_noise = 0.01 + 0.01j
    print(f" -> Fase-transformasjon med normal termisk støy ({acceptable_noise})...")
    phasor.transition_to_phase_b_with_noise(acceptable_noise)
    coherent, dist = phasor.run_phasor_coherence_test()
    print(f"    Topologisk avstand ||F(s_B) - s_A|| = {dist}")
    print(f"    Status: {'✅ Koherent og stabil' if coherent else '❌ Korrupt'}\n")

    # Kjøring B: Kritisk støy
    phasor.reset_to_phase_a(initial_angle_deg=45.0)
    critical_noise = 0.04 + 0.04j
    print(f" -> Fase-transformasjon med kritisk støy/kognitiv drift ({critical_noise})...")
    phasor.transition_to_phase_b_with_noise(critical_noise)
    coherent, dist = phasor.run_phasor_coherence_test()
    print(f"    Topologisk avstand ||F(s_B) - s_A|| = {dist}")
    if not coherent:
        print(" ❌ SCL-X GILJOTIN: Avstanden overstiger epsilon! Tilstanden er irreversibelt korrupt.")
