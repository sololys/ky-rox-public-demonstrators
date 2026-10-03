# Brahman.1 Fail-Closed Demonstrator

Source: [`run_demo.py`](https://github.com/sololys/ky-rox-public-demonstrators/blob/main/run_demo.py)  
Execution: `python3 run_demo.py`  
Target Audience: Independent third-party evaluators, security researchers, and distributed systems engineers.

---

## 🎯 Architectural Intent

In decentralized edge topologies operating in remote maritime environments or high-interference industrial plants, network partitioning (radio shadow) is an inevitability. Conventional distributed systems resolve split-brain states using **Last-Write-Wins (LWW)** or heuristic consensus—both of which overwrite valid physical events or rely on vulnerable external clock synchronizations.

**Brahman.1** enforces deterministic causal reconciliation using an append-only cryptographic directed acyclic graph (Merkle DAG) combined with a fail-closed hardware consequence gate.

---

## 🔬 The 4 Verification Phases

### FASE 1: Shared Canonical History ($k = 1..3$)
Both nodes begin with an identical synchronized history. Each event is committed to a local Write-Ahead Log (WAL) and cryptographically linked via SHA-256 hash chains.
```text
  [Felles Seq 1] Hash: 1cd4d8b58a30059a... (Begge noder synkronisert)
  [Felles Seq 2] Hash: c7571e1bfbe89590... (Begge noder synkronisert)
  [Felles Seq 3] Hash: d698f64a88ac61c1... (Begge noder synkronisert)
```

### FASE 2: Disconnected Divergence (Radio Shadow)
Both nodes lose mutual connectivity. Each node continues logging legitimate local events to its append-only ledger without overwriting or invalidating the other node's history.
* **Node A:** Records events $k = 4..5$.
* **Node B:** Records separate events $k = 4..5$.
```text
  [Node A Seq 4..5] Lokale hendelser committet til WAL. Head Hash: 332fb53d7bbc2b4b...
  [Node B Seq 4..5] Lokale hendelser committet til WAL. Head Hash: a653f7b1a82a1e9b...
```

### FASE 3: Geofence Reconnection (Ancestry Handshake & Merkle LCA)
Upon re-establishing contact, neither node accepts the other's state blindly. The consequence gate is held in stasis (`GATE::HOLD`, symbolic 0.00 V). The nodes execute a binary logarithmic search ($\mathcal{O}(\log N)$) to locate their **Lowest Common Ancestor (LCA)**:
* Common ancestor identified at $k_{\text{LCA}} = 3$ in exactly 2 round-trips.
* Both branch lineages are verified as authentic descendants of $k_{\text{LCA}}$.
* A bilateral **Signed Merge** transaction is minted and signed with Ed25519 keys.
* Gate state transitions: `GATE::HOLD (0.00 V)` $\longrightarrow$ `GATE::OPEN (5.00 V)`.
```text
  [Merkle LCA Søk] Siste felles forfader funnet: Sekvens k_LCA = 3 på 2 binærsøk-runder!
  [Status]         LEGITIMATE_SPLIT_BRAIN_RESOLVED
  [Porttilstand]   GATE::HOLD (symbolsk 0.00 V) -> GATE::OPEN (symbolsk 5.00 V via Signed Merge)
  [Signed Merge]   Bilateral sammenslåing forseglet med hash: b9742b6e03a2350f...
```

### FASE 4: Adversarial Attack Rejection (Fork Forgery)
A compromised or malicious node attempts to inject an illegitimate, tampered branch ($R_{\text{fork}} > 0$) with falsified parents or invalid Ed25519 signatures.
* The ancestry verification detects hash mismatch and signature corruption.
* The gate immediately clamps to `GATE::KILL (0.00 V)`.
* Game-theoretic asymmetry: The attacker's net utility is strictly negative ($\Delta U_{\text{cheat}} < 0$), proving that cheating is strictly dominated.
```text
  [Angrep Status]  FORK_FORGERY_DETECTED
  [Porttilstand]   GATE::KILL (symbolsk 0.00 V)
  [Avvisningsgrunn]ATTACK_SIGNATURE_INVALID: CORRUPTED_PARENT_HASH_AND_TAMPERED_ED25519
  [Spillteori]     Angriperens Nyttefunksjon: ΔU_cheat = -1000000075.0 < 0
```
