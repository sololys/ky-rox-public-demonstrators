from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import math
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple


EPISTEMIC_BOUNDARY = "INSPIRED_BY != IMPLEMENTS != PROVES"

GATE_OPEN = "GATE::OPEN"
GATE_HOLD = "GATE::HOLD"
GATE_KILL = "GATE::KILL"

VOLTAGE_OPEN_VDC = 5.00
VOLTAGE_HOLD_VDC = 0.00
VOLTAGE_KILL_VDC = 0.00

MAX_CHEMICAL_VALENCE: Dict[str, int] = {
    "H": 1,
    "C": 4,
    "N": 4,
    "O": 2,
    "S": 6,
    "P": 5,
    "Fe": 6,
    "Mo": 6,
}


@dataclass(frozen=True)
class MolecularGraph:
    name: str
    atom_symbols: Tuple[str, ...]
    edges: Tuple[Tuple[int, int], ...]
    description: str = ""

    @property
    def num_vertices(self) -> int:
        return len(self.atom_symbols)

    @property
    def num_edges(self) -> int:
        return len(self.edges)

    def degrees(self) -> Tuple[int, ...]:
        deg = [0] * self.num_vertices
        for u, v in self.edges:
            if 0 <= u < self.num_vertices and 0 <= v < self.num_vertices and u != v:
                deg[u] += 1
                deg[v] += 1
        return tuple(deg)

    def adjacency_list(self) -> Dict[int, List[int]]:
        adj: Dict[int, List[int]] = {i: [] for i in range(self.num_vertices)}
        for u, v in self.edges:
            if 0 <= u < self.num_vertices and 0 <= v < self.num_vertices and u != v:
                if v not in adj[u]:
                    adj[u].append(v)
                if u not in adj[v]:
                    adj[v].append(u)
        for i in adj:
            adj[i].sort()
        return adj


@dataclass(frozen=True)
class MPolynomialAnalysis:
    graph_name: str
    num_vertices: int
    num_edges: int
    degree_sequence: Tuple[int, ...]
    edge_partitions_m_ij: Dict[str, int]
    symbolic_polynomial: str
    first_zagreb_m1: float
    second_zagreb_m2: float
    randic_index_r: float
    harmonic_index_h: float
    sdd_index: float
    operator_consistency_verified: bool


def compute_edge_degree_partitions(graph: MolecularGraph) -> Dict[Tuple[int, int], int]:
    degs = graph.degrees()
    partitions: Dict[Tuple[int, int], int] = {}
    for u, v in graph.edges:
        if u == v or u < 0 or v < 0 or u >= graph.num_vertices or v >= graph.num_vertices:
            continue
        du, dv = degs[u], degs[v]
        pair = (min(du, dv), max(du, dv))
        partitions[pair] = partitions.get(pair, 0) + 1
    return dict(sorted(partitions.items()))


def format_mpolynomial_symbolic(partitions: Dict[Tuple[int, int], int]) -> str:
    if not partitions:
        return "0"
    terms: List[str] = []
    for (i, j), coeff in sorted(partitions.items()):
        if coeff == 0:
            continue
        c_str = f"{coeff}*" if coeff != 1 else ""
        terms.append(f"{c_str}x^{i}*y^{j}")
    return " + ".join(terms) if terms else "0"


def apply_mpolynomial_operator(
    partitions: Dict[Tuple[int, int], int],
    monomial_transform: Callable[[int, int], float],
) -> float:
    total = 0.0
    for (i, j), m_ij in partitions.items():
        if i > 0 and j > 0:
            total += float(m_ij) * float(monomial_transform(i, j))
    return total


def analyze_mpolynomial(graph: MolecularGraph) -> MPolynomialAnalysis:
    degs = graph.degrees()
    partitions = compute_edge_degree_partitions(graph)
    symbolic = format_mpolynomial_symbolic(partitions)

    m1 = apply_mpolynomial_operator(partitions, lambda i, j: float(i + j))
    m2 = apply_mpolynomial_operator(partitions, lambda i, j: float(i * j))
    randic = apply_mpolynomial_operator(partitions, lambda i, j: 1.0 / math.sqrt(float(i * j)))
    harmonic = apply_mpolynomial_operator(partitions, lambda i, j: 2.0 / float(i + j))
    sdd = apply_mpolynomial_operator(partitions, lambda i, j: float(i * i + j * j) / float(i * j))

    vertex_sq_sum = float(sum(d * d for d in degs))
    edge_count_sum = sum(partitions.values())
    consistency_ok = abs(m1 - vertex_sq_sum) <= 1e-12 and edge_count_sum == graph.num_edges
    str_partitions = {f"{i},{j}": count for (i, j), count in partitions.items()}

    return MPolynomialAnalysis(
        graph_name=graph.name,
        num_vertices=graph.num_vertices,
        num_edges=graph.num_edges,
        degree_sequence=tuple(sorted(degs)),
        edge_partitions_m_ij=str_partitions,
        symbolic_polynomial=symbolic,
        first_zagreb_m1=round(m1, 6),
        second_zagreb_m2=round(m2, 6),
        randic_index_r=round(randic, 6),
        harmonic_index_h=round(harmonic, 6),
        sdd_index=round(sdd, 6),
        operator_consistency_verified=consistency_ok,
    )


def compute_1wl_signature(graph: MolecularGraph, iterations: int = 4) -> Tuple[str, ...]:
    adj = graph.adjacency_list()
    degs = graph.degrees()
    colors: List[str] = [f"d{degs[v]}" for v in range(graph.num_vertices)]

    for _ in range(iterations):
        next_colors: List[str] = []
        for v in range(graph.num_vertices):
            neighbor_multisets = sorted(colors[nb] for nb in adj[v])
            raw_sig = f"{colors[v]}|({','.join(neighbor_multisets)})"
            digest = hashlib.sha256(raw_sig.encode("utf-8")).hexdigest()[:12]
            next_colors.append(digest)
        colors = next_colors

    return tuple(sorted(colors))


def count_connected_components(graph: MolecularGraph) -> int:
    if graph.num_vertices == 0:
        return 0
    adj = graph.adjacency_list()
    visited = set()
    components = 0
    for start in range(graph.num_vertices):
        if start in visited:
            continue
        components += 1
        stack = [start]
        visited.add(start)
        while stack:
            curr = stack.pop()
            for nb in adj[curr]:
                if nb not in visited:
                    visited.add(nb)
                    stack.append(nb)
    return components


def count_chordless_cycles_up_to_6(graph: MolecularGraph) -> Dict[int, int]:
    adj = graph.adjacency_list()
    n = graph.num_vertices
    cycle_counts = {3: 0, 4: 0, 5: 0, 6: 0}
    seen_cycles = set()

    def dfs(start: int, current: int, path: List[int]) -> None:
        depth = len(path)
        for nb in adj[current]:
            if nb == start and depth >= 3:
                if depth in cycle_counts:
                    canon = tuple(sorted(path))
                    if canon not in seen_cycles:
                        seen_cycles.add(canon)
                        cycle_counts[depth] += 1
            elif nb > start and nb not in path and depth < 6:
                dfs(start, nb, path + [nb])

    for v in range(n):
        dfs(v, v, [v])

    return cycle_counts


@dataclass(frozen=True)
class MolecularGateVerdict:
    graph_name: str
    gate_state: str
    voltage_vdc: float
    soft_gnn_would_pass: bool
    mpolynomial: MPolynomialAnalysis
    connected_components: int
    cyclomatic_number_beta1: int
    ring_motifs_c3_to_c6: Dict[int, int]
    valence_violations: Tuple[str, ...]
    reasons: Tuple[str, ...]
    witness_sha256: str


def evaluate_molecular_consequence_gate(
    graph: MolecularGraph,
    reference_1wl_peer: Optional[MolecularGraph] = None,
    require_higher_order_witness_on_1wl_collision: bool = True,
) -> MolecularGateVerdict:
    degs = graph.degrees()
    mpoly = analyze_mpolynomial(graph)
    components = count_connected_components(graph)
    beta1 = graph.num_edges - graph.num_vertices + components
    rings = count_chordless_cycles_up_to_6(graph)

    valence_violations: List[str] = []
    adj = graph.adjacency_list()
    for idx, (sym, deg) in enumerate(zip(graph.atom_symbols, degs)):
        max_v = MAX_CHEMICAL_VALENCE.get(sym, 4)
        if sym == "C" and deg == 6:
            nb_syms = [graph.atom_symbols[nb] for nb in adj[idx]]
            if all(s in ("Fe", "Mo") for s in nb_syms):
                max_v = 6
        if deg < 1:
            valence_violations.append(f"Atom #{idx} ({sym}) is isolated (degree 0)")
        elif deg > max_v:
            valence_violations.append(
                f"Atom #{idx} ({sym}) violates valence bound: degree {deg} > max {max_v}"
            )

    reasons: List[str] = []
    soft_gnn_would_pass = graph.num_vertices > 0 and graph.num_edges > 0

    if valence_violations:
        reasons.extend(valence_violations)
        reasons.append("Pi_K CROWBAR: Soft GNN embedding rejected due to illegal chemical coordination")
        return _seal_verdict(
            graph, GATE_KILL, VOLTAGE_KILL_VDC, soft_gnn_would_pass,
            mpoly, components, beta1, rings, valence_violations, reasons,
        )

    if components != 1:
        reasons.append(f"Pi_K CROWBAR: Disconnected ghost graph (beta_0={components} > 1)")
        return _seal_verdict(
            graph, GATE_KILL, VOLTAGE_KILL_VDC, soft_gnn_would_pass,
            mpoly, components, beta1, rings, valence_violations, reasons,
        )

    if not mpoly.operator_consistency_verified:
        reasons.append("Pi_K CROWBAR: M-polynomial operator mismatch against vertex degree squares")
        return _seal_verdict(
            graph, GATE_KILL, VOLTAGE_KILL_VDC, soft_gnn_would_pass,
            mpoly, components, beta1, rings, valence_violations, reasons,
        )

    if reference_1wl_peer is not None:
        sig_self = compute_1wl_signature(graph)
        sig_peer = compute_1wl_signature(reference_1wl_peer)
        mpoly_peer = analyze_mpolynomial(reference_1wl_peer)
        if (
            sig_self == sig_peer
            and mpoly.edge_partitions_m_ij == mpoly_peer.edge_partitions_m_ij
            and require_higher_order_witness_on_1wl_collision
        ):
            reasons.append(
                f"1-WL & M-Polynomial collision against '{reference_1wl_peer.name}': "
                f"both share M(G;x,y) = {mpoly.symbolic_polynomial}."
            )
            return _seal_verdict(
                graph, GATE_HOLD, VOLTAGE_HOLD_VDC, soft_gnn_would_pass,
                mpoly, components, beta1, rings, valence_violations, reasons,
            )

    reasons.append(
        f"Pi_K PASS: Valence, connectivity (beta_0=1, beta_1={beta1}) and M-polynomial ({mpoly.symbolic_polynomial}) verified"
    )
    return _seal_verdict(
        graph, GATE_OPEN, VOLTAGE_OPEN_VDC, soft_gnn_would_pass,
        mpoly, components, beta1, rings, valence_violations, reasons,
    )


def _seal_verdict(
    graph: MolecularGraph,
    gate_state: str,
    voltage_vdc: float,
    soft_gnn_would_pass: bool,
    mpoly: MPolynomialAnalysis,
    components: int,
    beta1: int,
    rings: Dict[int, int],
    valence_violations: List[str],
    reasons: List[str],
) -> MolecularGateVerdict:
    payload = {
        "graph_name": graph.name,
        "gate_state": gate_state,
        "voltage_vdc": voltage_vdc,
        "symbolic_polynomial": mpoly.symbolic_polynomial,
        "m1": mpoly.first_zagreb_m1,
        "m2": mpoly.second_zagreb_m2,
        "randic": mpoly.randic_index_r,
        "harmonic": mpoly.harmonic_index_h,
        "components": components,
        "rings": rings,
    }
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    witness_hash = hashlib.sha256(b"MPOLY-PI-K/v1.0:" + raw).hexdigest()
    return MolecularGateVerdict(
        graph_name=graph.name,
        gate_state=gate_state,
        voltage_vdc=voltage_vdc,
        soft_gnn_would_pass=soft_gnn_would_pass,
        mpolynomial=mpoly,
        connected_components=components,
        cyclomatic_number_beta1=beta1,
        ring_motifs_c3_to_c6=rings,
        valence_violations=tuple(valence_violations),
        reasons=tuple(reasons),
        witness_sha256=witness_hash,
    )


def build_canonical_molecular_library() -> Dict[str, MolecularGraph]:
    return {
        "n_butane": MolecularGraph(
            name="n-Butane (Linear C4 Skeleton)",
            atom_symbols=("C", "C", "C", "C"),
            edges=((0, 1), (1, 2), (2, 3)),
        ),
        "isobutane": MolecularGraph(
            name="Isobutane (Branched C4 Skeleton)",
            atom_symbols=("C", "C", "C", "C"),
            edges=((0, 1), (0, 2), (0, 3)),
        ),
        "decalin": MolecularGraph(
            name="Decalin (Fused Bicyclic C10H18)",
            atom_symbols=("C",) * 10,
            edges=(
                (0, 1), (1, 2), (2, 3), (3, 4), (4, 5), (0, 5),
                (4, 6), (6, 7), (7, 8), (8, 9), (5, 9),
            ),
        ),
        "bicyclopentyl": MolecularGraph(
            name="Bicyclopentyl (Bridge-Linked C10H18)",
            atom_symbols=("C",) * 10,
            edges=(
                (0, 1), (1, 2), (2, 3), (3, 4), (0, 4),
                (4, 5),
                (5, 6), (6, 7), (7, 8), (8, 9), (5, 9),
            ),
        ),
        "benzene_c6": MolecularGraph(
            name="Benzene Carbon Ring (C6)",
            atom_symbols=("C",) * 6,
            edges=((0, 1), (1, 2), (2, 3), (3, 4), (4, 5), (0, 5)),
        ),
        "disjoint_2x_c3": MolecularGraph(
            name="Disjoint 2x Cyclopropane Ghost (2x C3)",
            atom_symbols=("C",) * 6,
            edges=((0, 1), (1, 2), (0, 2), (3, 4), (4, 5), (3, 5)),
        ),
        "texas_carbon_hallucination": MolecularGraph(
            name="GNN Hallucination: Pentavalent Carbon (CH5 / C-C5)",
            atom_symbols=("C", "C", "C", "C", "C", "C"),
            edges=((0, 1), (0, 2), (0, 3), (0, 4), (0, 5)),
        ),
        "femos_cofactor_fe7mos9c": MolecularGraph(
            name="FeMo-Cofactor Core Cluster ([Fe7MoS9C] with Interstitial mu6-Carbide)",
            atom_symbols=(
                "Fe", "Fe", "Fe", "Fe", "Fe", "Fe", "Fe", "Mo",
                "S", "S", "S", "S", "S", "S", "S", "S", "S", "C",
            ),
            edges=(
                (0, 8), (0, 9), (0, 10),
                (1, 8), (2, 8), (2, 9), (3, 9), (1, 10), (3, 10),
                (1, 11), (4, 11), (2, 12), (5, 12), (3, 13), (6, 13),
                (4, 14), (5, 14), (5, 15), (6, 15), (4, 16), (6, 16),
                (7, 14), (7, 15), (7, 16),
                (1, 17), (2, 17), (3, 17), (4, 17), (5, 17), (6, 17),
            ),
        ),
    }


def main() -> None:
    fixture = json.loads(Path(__file__).with_name("FIXTURE.json").read_text(encoding="utf-8"))
    lib = build_canonical_molecular_library()
    femos = lib[fixture["primary_graph"]]
    decalin = lib[fixture["collision_pair"][0]]
    bicyclopentyl = lib[fixture["collision_pair"][1]]
    texas = lib[fixture["hallucination_graph"]]

    v_femos = evaluate_molecular_consequence_gate(femos)
    v_coll = evaluate_molecular_consequence_gate(decalin, reference_1wl_peer=bicyclopentyl)
    v_texas = evaluate_molecular_consequence_gate(texas)

    out: Dict[str, Any] = {
        "claim": "Bounded algebraic graph invariant and consequence gate evaluation only",
        "claim_status": "HOLD",
        "collision_1wl_gate": v_coll.gate_state,
        "collision_polynomial": v_coll.mpolynomial.symbolic_polynomial,
        "epistemic_boundary": EPISTEMIC_BOUNDARY,
        "femos_first_zagreb_m1": v_femos.mpolynomial.first_zagreb_m1,
        "femos_gate": v_femos.gate_state,
        "femos_polynomial": v_femos.mpolynomial.symbolic_polynomial,
        "femos_second_zagreb_m2": v_femos.mpolynomial.second_zagreb_m2,
        "hallucination_gate": v_texas.gate_state,
        "operational_authority": "NONE",
        "physical_authority": "NONE",
    }
    print(json.dumps(out, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
