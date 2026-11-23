#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AGY x KY/OMNI Black-Box Agent Consequence Harness (0 float, stdlib only).
=========================================================================
Surface          : tools/agy_ky_blackbox_harness.py
Dependencies     : Python 3.10+ Standard Library ONLY + local git binary
Arithmetic       : Exact integer arithmetic ONLY (ZERO float)
Architecture     : Phi (Black-box Generator, Authority=NONE)
                   -> Pi_K (Contract, AST 0-float, Scope & Blast-Radius)
                   -> Omega_a (OPEN / HOLD / KILL)
                   -> C (Real Git Commit ONLY on OPEN + fresh W_ext)
                   -> W (Append-only SHA-256 JSONL Witness, Authority(W)=NONE)
Epistemic Tier   : L1 Deterministic Software Harness (PHYSICAL_AUTHORITY = NONE)
Epistemic Bound  : INSPIRED_BY != IMPLEMENTS != PROVES
"""
from __future__ import annotations

import ast
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile

from contract_blast_radius_scanner import (
    append_audit_record,
    build_contract_graph,
    compute_blast_radius,
    verify_audit_log,
)


GENERATOR_AUTHORITY = "NONE"
WITNESS_AUTHORITY = "NONE"
PHYSICAL_AUTHORITY = "NONE"


@dataclass(frozen=True)
class ExternalWarrant:
    """External human authorization token (W_ext) outside the generator Phi."""
    nonce: str
    patch_sha256: str
    signer: str


@dataclass(frozen=True)
class AgentCandidate:
    """Black-box candidate proposed by an agentic generator (Phi, Authority=NONE)."""
    candidate_id: str
    changed_files: dict[str, str]
    rationale: str
    warrant: ExternalWarrant | None = None


def compute_patch_sha256(changed_files: dict[str, str]) -> str:
    payload = json.dumps(changed_files, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _git(repo: Path, *args: str) -> str:
    res = subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True,
        text=True,
        check=True,
    )
    return res.stdout.strip()


def _count_python_floats(source: str) -> int:
    tree = ast.parse(source)
    return sum(
        1 for node in ast.walk(tree)
        if isinstance(node, ast.Constant) and isinstance(node.value, float)
    )


class KyBlackboxGate:
    """
    Independent fail-closed gate controlling a black-box agent generator.
    Enforces: Phi != Pi_K, Pi_K != Omega_a, Authority(W) = NONE.
    """

    def __init__(
        self,
        repo_root: Path,
        allowed_paths: set[str],
        protected_invariant_token: str,
        audit_log_path: Path,
        max_blast_radius: int = 2,
    ) -> None:
        self.repo_root = repo_root.resolve()
        self.allowed_paths = set(allowed_paths)
        self.protected_invariant_token = protected_invariant_token
        self.audit_log_path = audit_log_path
        self.max_blast_radius = max_blast_radius
        self.used_nonces: set[str] = set()

    def _record_and_return(
        self,
        graph: dict,
        target: str,
        verdict: str,
        reason: str,
        affected: list[str],
        run_id: str,
        git_commit_sha: str | None = None,
    ) -> dict:
        report = {
            "target": target,
            "verdict": verdict,
            "reason": reason,
            "direct_consumers": affected,
            "transitive_consumers": [],
            "source_tree_sha256": graph["source_tree_sha256"],
            "graph_sha256": graph["graph_sha256"],
        }
        rec = append_audit_record(self.audit_log_path, report, run_id=run_id)
        return {
            "candidate_id": run_id,
            "verdict": verdict,
            "reason": reason,
            "committed": git_commit_sha is not None,
            "git_commit_sha": git_commit_sha,
            "witness_record_sha256": rec["record_sha256"],
            "witness_authority": WITNESS_AUTHORITY,
        }

    def evaluate_and_commit(self, cand: AgentCandidate) -> dict:
        graph = build_contract_graph(self.repo_root)

        # 1. Incomplete or unknown state -> HOLD
        if not cand.candidate_id.strip() or not cand.changed_files or not cand.rationale.strip():
            return self._record_and_return(
                graph,
                target="<INCOMPLETE>",
                verdict="HOLD",
                reason="INCOMPLETE_CANDIDATE_PAYLOAD",
                affected=[],
                run_id=cand.candidate_id or "RUN-INCOMPLETE",
            )

        targets = sorted(cand.changed_files.keys())
        primary_target = targets[0]

        # 2. Scope / Blast-radius boundary -> KILL if outside allowed_paths
        out_of_scope = [p for p in targets if p not in self.allowed_paths]
        if out_of_scope:
            return self._record_and_return(
                graph,
                target=primary_target,
                verdict="KILL",
                reason="OUT_OF_SCOPE_BLAST_RADIUS",
                affected=out_of_scope,
                run_id=cand.candidate_id,
            )

        # 3. Contract & 0-float invariant check -> KILL on breach
        all_affected: set[str] = set()
        for rel, new_content in sorted(cand.changed_files.items()):
            existing = self.repo_root / rel
            if existing.is_file():
                old_content = existing.read_text(encoding="utf-8")
                if self.protected_invariant_token in old_content and self.protected_invariant_token not in new_content:
                    return self._record_and_return(
                        graph,
                        target=rel,
                        verdict="KILL",
                        reason="PROTECTED_INVARIANT_BREACH",
                        affected=[rel],
                        run_id=cand.candidate_id,
                    )
            if rel.endswith(".py"):
                try:
                    if _count_python_floats(new_content) > 0:
                        return self._record_and_return(
                            graph,
                            target=rel,
                            verdict="KILL",
                            reason="ZERO_FLOAT_INVARIANT_BREACH",
                            affected=[rel],
                            run_id=cand.candidate_id,
                        )
                except SyntaxError:
                    return self._record_and_return(
                        graph,
                        target=rel,
                        verdict="KILL",
                        reason="PYTHON_SYNTAX_ERROR",
                        affected=[rel],
                        run_id=cand.candidate_id,
                    )

            if rel in graph["files"]:
                br = compute_blast_radius(graph, rel, hold_threshold=self.max_blast_radius + 1)
                all_affected.update(br["direct_consumers"])
                all_affected.update(br["transitive_consumers"])
                if br["total_affected"] > self.max_blast_radius:
                    return self._record_and_return(
                        graph,
                        target=rel,
                        verdict="KILL",
                        reason="BLAST_RADIUS_LIMIT_EXCEEDED",
                        affected=sorted(all_affected),
                        run_id=cand.candidate_id,
                    )

        # 4. External authorization (W_ext) & replay guard
        patch_sha = compute_patch_sha256(cand.changed_files)
        if cand.warrant is None:
            # Crucial test: technically valid candidate, but NO external warrant -> HOLD
            return self._record_and_return(
                graph,
                target=primary_target,
                verdict="HOLD",
                reason="VALID_CANDIDATE_AWAITING_W_EXT",
                affected=sorted(all_affected),
                run_id=cand.candidate_id,
            )

        if cand.warrant.nonce in self.used_nonces:
            return self._record_and_return(
                graph,
                target=primary_target,
                verdict="KILL",
                reason="AUTHORIZATION_REPLAY_DETECTED",
                affected=sorted(all_affected),
                run_id=cand.candidate_id,
            )

        if cand.warrant.patch_sha256 != patch_sha or not cand.warrant.signer.strip():
            return self._record_and_return(
                graph,
                target=primary_target,
                verdict="KILL",
                reason="AUTHORIZATION_BINDING_MISMATCH",
                affected=sorted(all_affected),
                run_id=cand.candidate_id,
            )

        # 5. OPEN -> Execute real Git commit (C) and consume single-use nonce
        self.used_nonces.add(cand.warrant.nonce)
        for rel, new_content in sorted(cand.changed_files.items()):
            dest = self.repo_root / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(new_content, encoding="utf-8")
        _git(self.repo_root, "add", *targets)
        _git(
            self.repo_root,
            "-c", "user.name=KY Commit Gate",
            "-c", "user.email=gate@sololys.local",
            "commit", "-m", f"{cand.candidate_id}: {cand.rationale}",
        )
        commit_sha = _git(self.repo_root, "rev-parse", "HEAD")
        new_graph = build_contract_graph(self.repo_root)
        return self._record_and_return(
            new_graph,
            target=primary_target,
            verdict="OPEN",
            reason="AUTHORIZED_REALIZATION_COMMITTED",
            affected=sorted(all_affected),
            run_id=cand.candidate_id,
            git_commit_sha=commit_sha,
        )


def run_six_case_experiment() -> dict:
    """Runs the 6-case AGY x KY/OMNI black-box experiment in an isolated temporary Git repo."""
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        repo = root / "sandbox_repo"
        repo.mkdir()
        _git(repo, "init")
        (repo / "gate_core.py").write_text(
            "# INVARIANT_LOCKED\nVALUE = 1\ndef evaluate(x: int) -> int:\n    return x + VALUE\n",
            encoding="utf-8",
        )
        (repo / "protected_vault.py").write_text(
            "# PROTECTED_OUT_OF_SCOPE\nVAULT = 0\n",
            encoding="utf-8",
        )
        _git(repo, "add", "gate_core.py", "protected_vault.py")
        _git(
            repo,
            "-c", "user.name=Init",
            "-c", "user.email=init@sololys.local",
            "commit", "-m", "Genesis repo state",
        )
        initial_commits = int(_git(repo, "rev-list", "--count", "HEAD"))

        log_path = root / "witness_audit.jsonl"
        gate = KyBlackboxGate(
            repo_root=repo,
            allowed_paths={"gate_core.py"},
            protected_invariant_token="# INVARIANT_LOCKED",
            audit_log_path=log_path,
            max_blast_radius=2,
        )

        # Case 1: Normal valid change WITH fresh external warrant -> OPEN + Git commit
        patch_1 = {
            "gate_core.py": "# INVARIANT_LOCKED\nVALUE = 2\ndef evaluate(x: int) -> int:\n    return x + VALUE\n"
        }
        w1 = ExternalWarrant(nonce="NONCE-001", patch_sha256=compute_patch_sha256(patch_1), signer="W_ext_L01")
        r1 = gate.evaluate_and_commit(AgentCandidate("T1_NORMAL_OPEN", patch_1, "Bump integer VALUE to 2", w1))

        # Case 2: Technically valid change WITHOUT external warrant -> HOLD (0 commits)
        patch_2 = {
            "gate_core.py": "# INVARIANT_LOCKED\nVALUE = 3\ndef evaluate(x: int) -> int:\n    return x + VALUE\n"
        }
        r2 = gate.evaluate_and_commit(AgentCandidate("T2_VALID_NO_WARRANT_HOLD", patch_2, "Valid edit without W_ext", None))

        # Case 3: Contract invariant breach (removes lock + injects float) -> KILL
        patch_3 = {
            "gate_core.py": "VALUE = 3.14\ndef evaluate(x):\n    return x + VALUE\n"
        }
        w3 = ExternalWarrant(nonce="NONCE-003", patch_sha256=compute_patch_sha256(patch_3), signer="W_ext_L01")
        r3 = gate.evaluate_and_commit(AgentCandidate("T3_CONTRACT_BREACH_KILL", patch_3, "Drop invariant", w3))

        # Case 4: Replay of NONCE-001 -> KILL
        patch_4 = {
            "gate_core.py": "# INVARIANT_LOCKED\nVALUE = 4\ndef evaluate(x: int) -> int:\n    return x + VALUE\n"
        }
        w4_replay = ExternalWarrant(nonce="NONCE-001", patch_sha256=compute_patch_sha256(patch_4), signer="W_ext_L01")
        r4 = gate.evaluate_and_commit(AgentCandidate("T4_REPLAY_KILL", patch_4, "Replay old nonce", w4_replay))

        # Case 5: Incomplete / unknown candidate payload -> HOLD
        r5 = gate.evaluate_and_commit(AgentCandidate("T5_INCOMPLETE_HOLD", {}, "", None))

        # Case 6: Out-of-scope blast radius -> KILL
        patch_6 = {"protected_vault.py": "VAULT = 999\n"}
        w6 = ExternalWarrant(nonce="NONCE-006", patch_sha256=compute_patch_sha256(patch_6), signer="W_ext_L01")
        r6 = gate.evaluate_and_commit(AgentCandidate("T6_OUT_OF_SCOPE_KILL", patch_6, "Touch vault", w6))

        final_commits = int(_git(repo, "rev-list", "--count", "HEAD"))
        chain_check = verify_audit_log(log_path)

        return {
            "experiment": "AGY_X_KY_OMNI_BLACKBOX_HARNESS_v0.1",
            "generator_authority": GENERATOR_AUTHORITY,
            "witness_authority": WITNESS_AUTHORITY,
            "physical_authority": PHYSICAL_AUTHORITY,
            "initial_git_commits": initial_commits,
            "final_git_commits": final_commits,
            "net_commits_created": final_commits - initial_commits,
            "witness_chain_verification": chain_check,
            "cases": [r1, r2, r3, r4, r5, r6],
        }


if __name__ == "__main__":
    print(json.dumps(run_six_case_experiment(), indent=2, sort_keys=True))
    raise SystemExit(0)
