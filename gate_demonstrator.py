import time
import hashlib

# ─── FORMELT TYPESYSTEM ───
STATES = ["RAW", "ESTIMATE", "STRUCT", "VIABILITY", "COMMITTED"] # [cite: 105, 483, 510]

class Node:
    def __init__(self, raw_input):
        self.raw_input = raw_input
        self.state = "RAW" # [cite: 96, 483, 570]
        self.admissibility_flag = True # [cite: 136, 489, 533]
        self.structure_valid = True # [cite: 116, 532]
        self.hash_chain_valid = True # [cite: 118, 156]
        self.reproducible = True # [cite: 122, 155, 490]
        self.uncertainty_high = False # [cite: 123, 492, 536]
        self.integrity_hash = None # [cite: 140]

# ─── DE TRE OPERATØRENE ───

def Phi(raw_event):
    """ generator: Skaper en spekulativ kandidat-tilstand """
    print(self_clean(f"[Phi] Genererer kandidat for: '{raw_event}'")) # [cite: 70-71, 466, 610]
    node = Node(raw_event)
    node.state = "ESTIMATE" # [cite: 97, 105, 483, 510]
    return node

def Pi_K(node):
    """ projector: Tvinger tilstanden inn i en gyldig struktur """
    print("[Pi_K] Validerer datastruktur og beregner type-integritet...") # [cite: 74, 178-179]
    node.state = "STRUCT" # [cite: 98, 105, 483, 510]
    
    # Eksempel på strukturell sjekk
    if not node.raw_input or len(node.raw_input) > 100:
        node.structure_valid = False # [cite: 116, 532]
        
    # Generer en unik hash for denne tilstandens struktur
    sha = hashlib.sha256()
    sha.update(f"{node.raw_input}:{node.state}".encode('utf-8'))
    node.integrity_hash = sha.hexdigest()
    
    # Sjekk spesifikke innholdsregler (Lore / Spillbalanse)
    if "infinite gold" in node.raw_input.lower():
        print("[Pi_K] BRUDD: Forsøk på ulovlig ressurs-manipulasjon oppdaget.") # [cite: 266-271]
        node.admissibility_flag = False # [cite: 120, 533]
        
    node.state = "VIABILITY" # [cite: 99, 105, 483, 510]
    return node

def Omega(node):
    """ gate: Den endelige, ufravikelige dørvakten """
    print(f"[Omega] Evaluerer admissibility gate for hash: {node.integrity_hash[:8]}...") # [cite: 76-77, 180-181]
    
    if not node.structure_valid or not node.hash_chain_valid or not node.admissibility_flag:
        return "KILL" # [cite: 116-120, 532-533, 630-632]
    if not node.reproducible:
        return "KILL" # [cite: 122, 535, 634]
    if node.uncertainty_high:
        return "HOLD" # [cite: 124, 536, 635]
        
    return "OPEN" # [cite: 126, 536, 636]

# ─── KJØRETIDSLOOPEN ───

def execute_engine_loop(raw_input):
    print(f"\n--- INGRESS EVENT: {raw_input} ---") # [cite: 68]
    
    # 1. GENERATE
    candidate = Phi(raw_input) # [cite: 70, 84, 471, 610]
    
    # 2. PROJECT
    structured = Pi_K(candidate) # [cite: 73, 85, 471, 613]
    
    # 3. GATE
    decision = Omega(structured) # [cite: 76, 86, 471, 616]
    
    # 4. COMMIT BARE HVIS OPEN (Fail-Closed)
    if decision == "OPEN": # [cite: 87, 207, 472, 529, 621]
        structured.state = "COMMITTED" # [cite: 105, 483, 510]
        print(f"✅ COMMIT VELLYKKET: '{structured.raw_input}' er nå en del av virkeligheten.") # [cite: 88, 227, 331]
    elif decision == "HOLD": # [cite: 89, 209, 473, 530, 622]
        print(f"⏳ HOLD AKTIVERT: Tilstanden flimrer som blueprint. Venter på stabilisering.") # [cite: 228, 341, 477]
    elif decision == "KILL": # [cite: 91, 211, 473, 530, 623]
        print(f"❌ KILL TRIGGERT: Avvik oppdaget. Systemet faller til lukket tilstand (bot).") # [cite: 229, 333, 367-371]

def self_clean(text):
    return text

if __name__ == "__main__":
    # Testtilfelle 1: En lovlig handling som passerer reglene
    execute_engine_loop("Build a bridge of light over the gap") # [cite: 214, 398]
    time.sleep(1)
    
    # Testtilfelle 2: Et forsøk på systembrudd (Vil bli brutalt avvist)
    execute_engine_loop("Spawn infinite gold") # [cite: 266]
