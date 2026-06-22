# CPS Derivative Gate v0.1

Status: SOFTWARE SIMULATION / DETERMINISTIC MICROTEST / PASS

## Purpose

Compare ordinary threshold gating against KY-ROX derivative gating in the same simulated CPS grid-overload event.

## Claim level

This is a deterministic software simulation only.
It is not physical validation.

## Result

KY-ROX derivative gate entered HOLD at 8.7s.
KY-ROX derivative gate entered KILL at 8.9s.
Baseline threshold gate entered KILL at 9.6s.

Lead time before baseline threshold kill: 0.7s.
Irreversibility accumulator saved at KY-ROX kill: 0.468273.

## Core observation

Derivative gating detects irreversible escalation before ordinary accumulated-threshold gating in the same simulated CPS event.

## Boundary

This artifact demonstrates simulated gate behavior.
It does not prove physical safety, hardware enforcement, or real-world CPS certification.
