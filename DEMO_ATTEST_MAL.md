# 📜 UAVHENGIG FAGLIG ATTESTASJON
### *Tredjepartsverifikasjon av Deterministisk Fail-Closed Portvakt (Brahman.1)*

> **Formål:** Denne attesten dokumenterer **uavhengig attestert evidens for demonstratorens observerte programvareadferd på evaluators oppgitte miljø**. Den dokumenterer én lokal reproduksjon av L1-demonstratoren, og etablerer ikke generell korrekthet, produksjonsegnethet, fysisk forrigling eller fysisk immunitet utenfor den spesifikke testmodellen. Koden inneholder **ingen kjemiske eller fysiske påstander**; porttilstandene angis som **symbolsk 0.00 V / 5.00 V** i programvare.

---

### 1. Testprosedyre (Kjøres i terminal på lokal maskin)

```bash
# 1. Naviger til rotmappen
cd /sti/til/monorepo

# 2. Kjør den uavhengige demonstratoren
python3 run_demo.py
```

*Forventet kjøretid:* `< 0.2 sekunder`  
*Avhengigheter:* Kun standard `python3` med kryptografimodul (`pip install cryptography`).

---

### 2. Verifikasjonspunkter (Kryss av ved observasjon)

| Punkt | Invariant som testes | Forventet Utfall i Terminal | Verifisert? |
| :---: | :--- | :--- | :---: |
| **1** | **Avvisning av Last-Write-Wins (LWW)** | Begge noder opererer i radioskygge. Ingen data overskrives eller slettes basert på klokkeslett. | [ ] JA |
| **2** | **Logaritmisk Merkle-LCA Søk** | Siste felles forfader lokaliseres deterministisk i $\mathcal{O}(\log N)$ runder uten full overføring. | [ ] JA |
| **3** | **Fail-Closed Forrigling (HOLD ➔ OPEN)** | Legitim divergens låser porten til `GATE::HOLD (symbolsk 0.00 V)` inntil bilateral signert sammenslåing fullføres (`symbolsk 5.00 V`). | [ ] JA |
| **4** | **Manipulasjonsavvisning (KILL)** | Ugyldig eller korrumpert input gir `GATE::KILL` (symbolsk `0.00 V`) og demonstratoren observerer `0 bytes` skrevet. | [ ] JA |

---

### 3. Evaluators Erklæring & Signatur

Jeg bekrefter herved at jeg har klonet kildekoden, kjørt skriptet `run_demo.py` på mitt eget system, og observert at de fire ovennevnte fail-closed-mekanismene ble eksekvert deterministisk som beskrevet.

* **Fullt navn:** __________________________________________________
* **Stilling / Rolle:** __________________________________________________
* **Organisasjon / Selskap:** __________________________________________________
* **Dato for verifikasjon:** __________________________________________________
* **Operativsystem & Python-versjon:** __________________________________________________
* **Samlet Konklusjon:** `[  ] BESTÅTT (100% Fail-Closed Integritet)   [  ] IKKE BESTÅTT`

**Evaluators faglige merknad (hva demonstrasjonen faktisk viser):**
> __________________________________________________________________________________________  
> __________________________________________________________________________________________  
> __________________________________________________________________________________________  

**Signatur:** ______________________________________
