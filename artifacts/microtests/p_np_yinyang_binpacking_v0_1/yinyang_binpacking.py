from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class YinYangVerdict:
    status: str
    measurement_status: str
    claim_status: str
    p_equals_np_claim_status: str
    route_directory: str
    computed_total: int
    claimed_total: int
    capacity: int
    path_steps: list[dict[str, Any]]
    w_pre_hash: str
    w_post_hash: str
    physical_authority: str = "NONE"
    operational_authority: str = "NONE"
    claim: str = "VERIFY(I,C) in P demonstrated on micro-instance; P=NP remains HOLD"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def evaluate_binpacking_candidate(fixture: dict[str, Any]) -> YinYangVerdict:
    item_count = int(fixture["item_count"])
    item_size = int(fixture["item_size"])
    capacity = int(fixture["capacity"])
    claimed_total = int(fixture["claimed_total"])
    bin_limit_b = int(fixture.get("bin_limit_b", 1))
    complete_flag = bool(fixture.get("complete_flag", True))
    duplicate_flag = bool(fixture.get("duplicate_flag", False))

    w_pre_payload = {
        "bin_limit_b": bin_limit_b,
        "capacity": capacity,
        "claimed_total": claimed_total,
        "complete_flag": complete_flag,
        "duplicate_flag": duplicate_flag,
        "item_count": item_count,
        "item_size": item_size,
        "stage": "W_PRE",
    }
    w_pre_hash = hashlib.sha256(
        json.dumps(w_pre_payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()

    computed_total = item_count * item_size
    steps: list[dict[str, Any]] = []
    remaining = capacity
    for idx in range(1, item_count + 1):
        remaining -= item_size
        steps.append(
            {
                "item_index": idx,
                "item_size": item_size,
                "local_valid": remaining >= 0,
                "remaining_capacity": remaining,
                "step": idx,
            }
        )

    if duplicate_flag or computed_total != claimed_total or computed_total > capacity * bin_limit_b:
        status = "KILL"
        m_status = "KILL"
        route = "03_KILL_ARKIV/"
    elif not complete_flag:
        status = "HOLD"
        m_status = "HOLD"
        route = "02_HOLD/"
    else:
        status = "HOLD"
        m_status = "OPEN"
        route = "01_OPEN/"

    w_post_payload = {
        "computed_total": computed_total,
        "measurement_status": m_status,
        "p_equals_np_claim_status": "HOLD",
        "route": route,
        "stage": "W_POST",
        "w_pre_hash": w_pre_hash,
    }
    w_post_hash = hashlib.sha256(
        json.dumps(w_post_payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()

    return YinYangVerdict(
        status=status,
        measurement_status=m_status,
        claim_status="HOLD",
        p_equals_np_claim_status="HOLD",
        route_directory=route,
        computed_total=computed_total,
        claimed_total=claimed_total,
        capacity=capacity,
        path_steps=steps,
        w_pre_hash=w_pre_hash,
        w_post_hash=w_post_hash,
    )


def main() -> None:
    fixture = json.loads(Path(__file__).with_name("FIXTURE.json").read_text(encoding="utf-8"))
    result = evaluate_binpacking_candidate(fixture)
    print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
