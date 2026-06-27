# KY-Gate Admissible Learning Simulator

Denne mappen inneholder den offentlige demonstratoren for KY-Gate-arkitekturen. Simulatoren demonstrerer visuelt og operasjonelt hvordan et epistemisk adgangslag kan beskytte en maskinlæringssløyfe mot støy, uautoriserte overganger og datakontaminering.

## Arkitektur

Demonstratoren synliggjør det fundamentale skillet:

```text
Kandidat != Realisert Erfaring
```

**Det generative rommet** genererer forslag og hypoteser gjennom en streng type-progresjon:

```text
RAW -> ESTIMATE -> STRUCT
```

**Dørvakten** `Omega / Omega_Q` er en ternær adgangsport som avgjør om en kandidat skal slippes inn, settes på vent eller forkastes:

- `OPEN / QOPEN`: erfaringen er admissibel og kan skrives til Witness.
- `HOLD / QHOLD`: admissibilitet er ikke bekreftet; kandidaten suspenderes for rekalibrering.
- `KILL / QKILL`: kandidaten bryter type-, risiko- eller admissibilitetskrav og forkastes.

**Witness Ledger** arkiverer bare bekreftede og godkjente erfaringer. Uforløste kandidater, HOLD-tilstander og KILL-tilstander får ikke skrives til historien.

## Kvantebasert tilsyn `Omega_Q`

I kvantemodus opererer simulatoren i Hilbert-rommet `H`, der systemtilstanden representeres ved en tetthetsoperator `rho`. Det admissible subrommet defineres som:

```text
S_A subset H
```

Det admissible tilstandsrommet er:

```text
A = { rho in D(H) : Tr[(I - P_A)rho] <= epsilon }
```

Simulatoren overvåker residuallekkasje:

```text
r_A(rho) = Tr[(I - P_A)rho]
```

Ved moderat lekkasje settes prosessen i `QHOLD`, der operatøren kan iverksette dynamical decoupling eller rekalibrering. Ved kritisk lekkasje utløses `QKILL`, og kandidaten forkastes før den kan forurense læringshistorien.

## Kjøring

```bash
npm install
npm run dev
```

## Avhengigheter

- React v18+
- Tailwind CSS

## Status

Dette er en offentlig, interaktiv software-demonstrator. Den viser KY-Gate som konseptuell og operasjonell adgangslogikk for admissibel læring.

Den er ikke fysisk validering, ikke kvanteeksperimentell evidens, ikke sertifisert sikkerhetslogikk og ikke produksjonsklar interlock.
