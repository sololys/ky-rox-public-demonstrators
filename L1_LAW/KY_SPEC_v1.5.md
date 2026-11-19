# `KY_SPEC_v1.5.md` — KY Realization Grammar v1.5 (Locked Core)

> **Status:** LOCKED CORE (Registry A) · Locus Zero (Level 0)  
> **Epistemic Boundary (`INSPIRED_BY != IMPLEMENTS != PROVES`):** The reference implementation in [`L1_LAW/ky_v15_clean_parser.py`](ky_v15_clean_parser.py) is `L1` deterministic software (`0 float`, `0 mV DC` inside $\mathcal{F}$, `PHYSICAL_AUTHORITY = NONE`). Software hash chains are append-only cryptographic ledgers, not physical WORM hardware media.

---

## 1. Core Pipeline

> **Axiom:** *Reality is not generated. Reality is admitted.*

$$\text{pre-witness } (W_t^-) \longrightarrow \text{warrant } (J_t^-) \longrightarrow \text{commit } (D_2) \longrightarrow \text{consequence witness } (W_{t+1}^+)$$

---

## 2. Canonical Layer Stack ($D_0 \to D_3$)

| Layer | State | ASCII | Unicode | Permitted Operations & Hard Rule |
| :--- | :--- | :--- | :---: | :--- |
| **$D_0$** | `RAW` | `RAW` | `○` | Uninterpreted bit material. `Authority = 0`. |
| **$D_1$** | `CANDIDATE` | `CANDIDATE` | `∅` | Bijective symmetries only (`ROL`, `ROR`, `XOR_FROZEN`, `NOT`, `GRAY`, `LFSR_NONSINGULAR`). `AND`, `OR`, `SHL`, `SHR` trigger `KILL`. |
| **$D_{1.2}$** | `STRUCT` | `STRUCT` | `□` | Typed numeric codecs requiring exact roundtrip $\operatorname{decode}(\operatorname{encode}(v)) = v$. |
| **$D_{1.5}$** | `VIABILITY` | `VIABILITY` | `◇` | Exact rational epistemic risk $\pi_t \in \mathbb{Q}$ against $0 \le \tau_{\text{OPEN}} < \tau_{\text{KILL}}$ (zero floating-point). |
| **$D_{2^-}$** | `AUTHORIZED` | `AUTHORIZED` | `⊙` | Cryptographic `PreCommitWarrant` ($J_t^-$) at dry contact (`0 mV DC` before $W_{\text{ext}}$). |
| **$D_2$** | `REALIZED` | `REALIZED` | `●` | Point of No Return (`5000 mV` L1-simulated exclusively with verified $J_t^-$ + `!` + $W_{\text{ext}}$). |
| **$D_3$** | `WITNESSED` | `WITNESSED` | `⊞` | Witnessed history requiring `#`. Hash-chain alone is `KILL` as physical WORM; Unicode is encoding only. |
| **$\bot$** | `KILLED` | `KILLED` | `⊥` | Terminated trajectory. No outgoing transitions. |

---

## 3. Clean EBNF & Lossless 1-to-1 Symbol Map (`Unicode <-> ASCII <-> AST`)

Every glyph has **one and only one role** (`●` = `REALIZED` node only, `⊞` = `WITNESSED` node only, `!` = commit marker, `#` = witness seal marker):

```ebnf
expr           ::= validated_expr gate ;
validated_expr ::= "(" chain ")" validity_mark* audit_part? ;
chain          ::= node (flow node)* ;

node           ::= "RAW" | "CANDIDATE" | "STRUCT" | "VIABILITY"
                 | "AUTHORIZED" | "REALIZED" | "WITNESSED" | "KILLED" ;

flow           ::= "->" | "~" | "=>" | "!>" ;
validity_mark  ::= "ROX_OK" | "ROX_FAIL" | "IN_K" | "NOT_IN_K"
                 | "MASK_FROZEN" | "MASK_MUTATED"
                 | "PLASMA_OPEN" | "PLASMA_HOLD" | "PLASMA_KILL" ;
audit_part     ::= ( "!" | "#" | "READMIT" )+ ;
gate           ::= "OPEN" | "HOLD" | "KILL" ;
```

**Transition Discipline (Zero Shortcuts):**

1. Forward adjacency only: `RAW -> CANDIDATE -> STRUCT -> VIABILITY -> AUTHORIZED -> REALIZED -> WITNESSED`.
2. Pre-$D_2$ stabilization self-loop `X ~ X` (`RAW`, `CANDIDATE`, `STRUCT`, `VIABILITY`) resolves to `HOLD` (`0 mV DC`).
3. `VIABILITY -> AUTHORIZED` requires `ROX_OK`, `MASK_FROZEN`, and `PLASMA_OPEN`.
4. `AUTHORIZED -> REALIZED` requires `!` and a fresh `PreCommitWarrant` ($J_t^-$) + external witness ($W_{\text{ext}}$).
5. `REALIZED -> WITNESSED` requires `#`.
6. `HOLD -> OPEN` without explicit `READMIT` triggers `KILL` (`INVALID_DELAYED_OPEN`).
7. Any non-adjacent jump, reversal after $D_2$, or resurrection from `KILLED` triggers `KILL`.
