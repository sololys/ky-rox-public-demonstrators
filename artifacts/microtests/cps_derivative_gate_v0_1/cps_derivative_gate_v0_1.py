#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CPS Derivative Gate v0.1

Purpose:
    Compare ordinary threshold gating against KY-ROX derivative gating
    in the same simulated CPS grid-overload event.

Claim level:
    Software simulation / deterministic microtest.
    Not physical validation.

Core test:
    Same disturbance.
    Same irreversible stress accumulator R(t).
    Baseline gate stops only when R >= R_LIMIT.
    KY-ROX gate reacts when dR/dt >= DELTA_R for DWELL ticks.

Pass condition:
    derivative HOLD occurs before baseline KILL,
    and derivative KILL occurs before baseline KILL.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import sin


DT = 0.1
MAX_STEPS = 220

R_LIMIT = 3.0
DELTA_R = 0.65
DWELL_TICKS = 3


@dataclass(frozen=True)
class Event:
    name: str
    t: float
    R: float
    dRdt: float


def disturbance_dRdt(t: float) -> float:
    """
    Deterministic grid-overload disturbance.

    It starts as low reversible stress, becomes a rising overload,
    then enters a fast irreversible slope.
    """
    if t < 4.0:
        return 0.12 + 0.015 * sin(2.0 * t)

    if t < 8.0:
        return 0.18 + 0.09 * (t - 4.0) + 0.015 * sin(2.0 * t)

    return 0.54 + 0.16 * (t - 8.0) + 0.02 * sin(3.0 * t)


def run_case() -> list[Event]:
    baseline_R = 0.0
    derivative_R = 0.0

    baseline_killed = False
    derivative_killed = False

    derivative_dwell = 0
    derivative_hold_seen = False

    events: list[Event] = []

    for step in range(MAX_STEPS):
        t = round(step * DT, 10)
        dRdt = disturbance_dRdt(t)

        if not baseline_killed:
            baseline_R += dRdt * DT

            if baseline_R >= R_LIMIT:
                baseline_killed = True
                events.append(Event("BASELINE_THRESHOLD_KILL", t, baseline_R, dRdt))

        if not derivative_killed:
            derivative_R += dRdt * DT

            if dRdt >= DELTA_R:
                derivative_dwell += 1

                if not derivative_hold_seen:
                    derivative_hold_seen = True
                    events.append(Event("KYROX_DERIVATIVE_HOLD", t, derivative_R, dRdt))

                if derivative_dwell >= DWELL_TICKS:
                    derivative_killed = True
                    events.append(Event("KYROX_DERIVATIVE_KILL", t, derivative_R, dRdt))
            else:
                derivative_dwell = 0

        if baseline_killed and derivative_killed:
            break

    return events


def event_by_name(events: list[Event], name: str) -> Event:
    for event in events:
        if event.name == name:
            return event
    raise RuntimeError(f"Missing expected event: {name}")


def main() -> int:
    events = run_case()

    baseline = event_by_name(events, "BASELINE_THRESHOLD_KILL")
    hold = event_by_name(events, "KYROX_DERIVATIVE_HOLD")
    kill = event_by_name(events, "KYROX_DERIVATIVE_KILL")

    lead_hold = baseline.t - hold.t
    lead_kill = baseline.t - kill.t
    R_saved_at_kill = R_LIMIT - kill.R

    passed = (
        hold.t < baseline.t
        and kill.t < baseline.t
        and kill.R < R_LIMIT
        and lead_hold > 0.0
        and lead_kill > 0.0
    )

    print("=== CPS DERIVATIVE GATE v0.1 ===")
    print("CASE: GRID_OVERLOAD")
    print("CLAIM_LEVEL: SOFTWARE_SIMULATION_ONLY")
    print("SAME_EVENT: YES")
    print("BASELINE: KILL when R >= R_LIMIT")
    print("KYROX: HOLD/KILL when dRdt >= DELTA_R with dwell")
    print("")

    for event in events:
        print(
            f"{event.name}: "
            f"t={event.t:.1f}s "
            f"R={event.R:.6f} "
            f"dRdt={event.dRdt:.6f}"
        )

    print("")
    print(f"LEAD_TIME_HOLD_SECONDS={lead_hold:.1f}")
    print(f"LEAD_TIME_KILL_SECONDS={lead_kill:.1f}")
    print(f"R_SAVED_AT_KYROX_KILL={R_saved_at_kill:.6f}")
    print(f"RESULT={'PASS' if passed else 'FAIL'}")

    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
