from __future__ import annotations

from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any
import csv
import itertools
import json
import math
import re
import time
import uuid
import numpy as np


@dataclass
class PauliTerm:
    coefficient: complex
    pauli_string: str
    label: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def normalized_string(self) -> str:
        s = self.pauli_string.upper().replace(" ", "")
        if not s:
            raise ValueError("Pauli string cannot be empty.")
        if any(ch not in "IXYZ" for ch in s):
            raise ValueError(f"Invalid Pauli string: {self.pauli_string}")
        return s

    @property
    def n_qubits(self) -> int:
        return len(self.normalized_string())

    def summary(self) -> str:
        return f"PauliTerm(coeff={self.coefficient}, pauli='{self.normalized_string()}', label={self.label})"


@dataclass
class PauliComponent:
    name: str
    quantity: str
    indices: list[int]
    terms: list[PauliTerm]
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def n_qubits(self) -> int:
        return max((t.n_qubits for t in self.terms), default=0)

    def summary(self) -> str:
        return (
            "PauliComponent\n"
            f"  name: {self.name}\n"
            f"  quantity: {self.quantity}\n"
            f"  indices: {self.indices}\n"
            f"  terms: {len(self.terms)}\n"
            f"  n_qubits: {self.n_qubits}"
        )


@dataclass
class CommutingGroup:
    group_id: str
    terms: list[PauliTerm]
    measurement_basis: str
    metadata: dict[str, Any] = field(default_factory=dict)

    def summary(self) -> str:
        return f"CommutingGroup(id={self.group_id}, terms={len(self.terms)}, basis={self.measurement_basis})"


@dataclass
class MeasurementCircuitSpec:
    circuit_id: str
    group_id: str
    n_qubits: int
    measurement_basis: str
    basis_rotations: list[tuple[int, str]]
    terms: list[PauliTerm]
    circuit_type: str = "basis_rotation_measurement"
    metadata: dict[str, Any] = field(default_factory=dict)

    def summary(self) -> str:
        return (
            "MeasurementCircuitSpec\n"
            f"  circuit_id: {self.circuit_id}\n"
            f"  group_id: {self.group_id}\n"
            f"  n_qubits: {self.n_qubits}\n"
            f"  basis: {self.measurement_basis}\n"
            f"  rotations: {self.basis_rotations}\n"
            f"  terms: {len(self.terms)}"
        )


@dataclass
class HadamardTestSpec:
    circuit_id: str
    pauli_term: PauliTerm
    ancilla_qubit: int
    system_qubits: list[int]
    phase: float = 0.0
    measure_real_part: bool = True
    metadata: dict[str, Any] = field(default_factory=dict)

    def summary(self) -> str:
        part = "real" if self.measure_real_part else "imag"
        return (
            "HadamardTestSpec\n"
            f"  circuit_id: {self.circuit_id}\n"
            f"  term: {self.pauli_term.summary()}\n"
            f"  ancilla: {self.ancilla_qubit}\n"
            f"  system_qubits: {self.system_qubits}\n"
            f"  phase: {self.phase}\n"
            f"  part: {part}"
        )


@dataclass
class PauliCompilationResult:
    component: PauliComponent
    groups: list[CommutingGroup]
    measurement_circuits: list[MeasurementCircuitSpec]
    hadamard_tests: list[HadamardTestSpec]
    artifacts: dict[str, str] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)

    def summary(self) -> str:
        return (
            "PauliCompilationResult\n"
            f"  component: {self.component.name}\n"
            f"  terms: {len(self.component.terms)}\n"
            f"  groups: {len(self.groups)}\n"
            f"  measurement_circuits: {len(self.measurement_circuits)}\n"
            f"  hadamard_tests: {len(self.hadamard_tests)}\n"
            f"  artifacts: {len(self.artifacts)}\n"
            f"  warnings: {self.warnings}"
        )


def parse_complex(value) -> complex:
    if isinstance(value, complex):
        return value
    if isinstance(value, (int, float)):
        return complex(value)
    if isinstance(value, list) and len(value) == 2:
        return complex(float(value[0]), float(value[1]))
    text = str(value).strip().replace("i", "j")
    return complex(text)


def pauli_term_from_dict(data: dict[str, Any]) -> PauliTerm:
    coeff = data.get("coefficient", data.get("coeff", 1.0))
    pauli = data.get("pauli_string", data.get("pauli", data.get("string", "I")))
    return PauliTerm(
        coefficient=parse_complex(coeff),
        pauli_string=str(pauli),
        label=data.get("label"),
        metadata=dict(data.get("metadata", {})),
    )


def pauli_component_from_dict(data: dict[str, Any]) -> PauliComponent:
    terms = [pauli_term_from_dict(t) for t in data.get("terms", [])]
    return PauliComponent(
        name=str(data.get("name", "unnamed_component")),
        quantity=str(data.get("quantity", "unknown")),
        indices=list(data.get("indices", [])),
        terms=terms,
        metadata=dict(data.get("metadata", {})),
    )


def load_pauli_components_from_registry(path) -> list[PauliComponent]:
    path = Path(path)
    data = json.loads(path.read_text(encoding="utf-8"))
    raw_components = data if isinstance(data, list) else data.get("components", [])
    return [pauli_component_from_dict(c) for c in raw_components]


def pauli_commutes(a: str, b: str) -> bool:
    a = a.upper().replace(" ", "")
    b = b.upper().replace(" ", "")
    if len(a) != len(b):
        raise ValueError("Pauli strings must have the same length.")
    anti = 0
    for x, y in zip(a, b):
        if x == "I" or y == "I" or x == y:
            continue
        anti += 1
    return anti % 2 == 0


def can_share_single_qubit_measurement_basis(a: str, b: str) -> bool:
    """True when a and b can be measured in one product basis without entangling rotations."""
    a = a.upper().replace(" ", "")
    b = b.upper().replace(" ", "")
    if len(a) != len(b):
        raise ValueError("Pauli strings must have the same length.")
    for x, y in zip(a, b):
        if x != "I" and y != "I" and x != y:
            return False
    return True


def merge_measurement_basis(strings: list[str]) -> str:
    if not strings:
        return ""
    n = len(strings[0])
    basis = ["I"] * n
    for s in strings:
        s = s.upper().replace(" ", "")
        if len(s) != n:
            raise ValueError("All Pauli strings must have same length.")
        for i, ch in enumerate(s):
            if ch == "I":
                continue
            if basis[i] == "I":
                basis[i] = ch
            elif basis[i] != ch:
                raise ValueError("Strings do not share a single-qubit measurement basis.")
    return "".join(basis)


def group_commuting_terms_greedy(terms: list[PauliTerm], product_basis_only: bool = True) -> list[CommutingGroup]:
    groups: list[list[PauliTerm]] = []
    for term in terms:
        placed = False
        for group in groups:
            if product_basis_only:
                ok = all(can_share_single_qubit_measurement_basis(term.normalized_string(), g.normalized_string()) for g in group)
            else:
                ok = all(pauli_commutes(term.normalized_string(), g.normalized_string()) for g in group)
            if ok:
                group.append(term)
                placed = True
                break
        if not placed:
            groups.append([term])

    out = []
    for group in groups:
        try:
            basis = merge_measurement_basis([t.normalized_string() for t in group])
        except Exception:
            # For general commuting but non-product-basis groups, keep first as scaffold basis.
            basis = group[0].normalized_string()
        out.append(
            CommutingGroup(
                group_id=str(uuid.uuid4()),
                terms=group,
                measurement_basis=basis,
                metadata={"product_basis_only": product_basis_only},
            )
        )
    return out


def basis_rotations_for_pauli_basis(basis: str) -> list[tuple[int, str]]:
    rotations = []
    for i, ch in enumerate(basis.upper()):
        if ch == "X":
            rotations.append((i, "H"))
        elif ch == "Y":
            rotations.append((i, "SdgH"))
        elif ch in {"Z", "I"}:
            pass
        else:
            raise ValueError(f"Invalid basis character: {ch}")
    return rotations


def measurement_circuit_spec_from_group(group: CommutingGroup) -> MeasurementCircuitSpec:
    basis = group.measurement_basis
    return MeasurementCircuitSpec(
        circuit_id=str(uuid.uuid4()),
        group_id=group.group_id,
        n_qubits=len(basis),
        measurement_basis=basis,
        basis_rotations=basis_rotations_for_pauli_basis(basis),
        terms=group.terms,
        metadata={"created_at_unix": time.time()},
    )


def measurement_spec_to_qiskit(spec: MeasurementCircuitSpec):
    try:
        from qiskit import QuantumCircuit
    except Exception as exc:
        raise ImportError("Qiskit is not installed. Install with: python -m pip install qiskit") from exc

    qc = QuantumCircuit(spec.n_qubits, spec.n_qubits)
    # Placeholder state preparation is left to caller. This circuit only appends measurement rotations.
    for q, rot in spec.basis_rotations:
        if rot == "H":
            qc.h(q)
        elif rot == "SdgH":
            qc.sdg(q)
            qc.h(q)
        else:
            raise ValueError(f"Unknown rotation: {rot}")
    qc.measure(range(spec.n_qubits), range(spec.n_qubits))
    return qc


def make_hadamard_test_specs(terms: list[PauliTerm], phase: float = 0.0) -> list[HadamardTestSpec]:
    specs = []
    for term in terms:
        n = term.n_qubits
        specs.append(
            HadamardTestSpec(
                circuit_id=str(uuid.uuid4()),
                pauli_term=term,
                ancilla_qubit=0,
                system_qubits=list(range(1, n + 1)),
                phase=phase,
                measure_real_part=True,
                metadata={"n_system_qubits": n},
            )
        )
    return specs


def hadamard_test_spec_to_qiskit(spec: HadamardTestSpec):
    try:
        from qiskit import QuantumCircuit
    except Exception as exc:
        raise ImportError("Qiskit is not installed. Install with: python -m pip install qiskit") from exc

    n_total = 1 + len(spec.system_qubits)
    qc = QuantumCircuit(n_total, 1)
    anc = spec.ancilla_qubit
    qc.h(anc)
    if abs(spec.phase) > 1e-15:
        qc.p(spec.phase, anc)

    pauli = spec.pauli_term.normalized_string()
    for idx, p in enumerate(pauli):
        q = idx + 1
        if p == "X":
            qc.cx(anc, q)
        elif p == "Y":
            qc.sdg(q)
            qc.cx(anc, q)
            qc.s(q)
        elif p == "Z":
            qc.cz(anc, q)
        elif p == "I":
            pass
        else:
            raise ValueError(f"Invalid Pauli character: {p}")

    if not spec.measure_real_part:
        qc.sdg(anc)
    qc.h(anc)
    qc.measure(anc, 0)
    return qc


def bitstring_eigenvalue_for_pauli(bitstring: str, pauli: str, measurement_basis: str | None = None) -> int:
    """Eigenvalue from measured bitstring after basis rotation."""
    bitstring = str(bitstring).replace(" ", "")
    pauli = pauli.upper().replace(" ", "")
    if len(bitstring) != len(pauli):
        # Qiskit often reverses bit order in displayed strings; handle outside if needed.
        raise ValueError("Bitstring and Pauli string lengths differ.")
    eigen = 1
    for b, p in zip(bitstring, pauli):
        if p == "I":
            continue
        if b == "1":
            eigen *= -1
    return eigen


def expectation_from_counts_for_pauli(counts: dict[str, int], pauli: str, reverse_bitstrings: bool = False) -> float:
    shots = sum(int(v) for v in counts.values())
    if shots <= 0:
        raise ValueError("Counts are empty.")
    total = 0.0
    for bitstring, count in counts.items():
        b = str(bitstring).replace(" ", "")
        if reverse_bitstrings:
            b = b[::-1]
        total += int(count) * bitstring_eigenvalue_for_pauli(b, pauli)
    return total / shots


def component_expectation_from_group_counts(
    component: PauliComponent,
    group_counts: dict[str, dict[str, int]],
    reverse_bitstrings: bool = False,
) -> complex:
    total = 0.0 + 0.0j
    # group_counts maps group_id or measurement_basis to counts.
    for term in component.terms:
        found_counts = None
        for key, counts in group_counts.items():
            # key can be basis; usable if basis can measure term.
            try:
                if can_share_single_qubit_measurement_basis(term.normalized_string(), str(key)):
                    found_counts = counts
                    break
            except Exception:
                pass
        if found_counts is None:
            raise KeyError(f"No counts provided for term {term.normalized_string()}")
        total += term.coefficient * expectation_from_counts_for_pauli(found_counts, term.normalized_string(), reverse_bitstrings=reverse_bitstrings)
    return total


def ancilla_expectation_from_counts(counts: dict[str, int]) -> float:
    shots = sum(int(v) for v in counts.values())
    if shots <= 0:
        raise ValueError("Counts are empty.")
    zero = int(counts.get("0", 0))
    one = int(counts.get("1", 0))
    return (zero - one) / shots


def compile_pauli_component(component: PauliComponent, product_basis_only: bool = True) -> PauliCompilationResult:
    warnings = []
    if not component.terms:
        warnings.append("Component contains no Pauli terms.")

    groups = group_commuting_terms_greedy(component.terms, product_basis_only=product_basis_only)
    measurement_specs = [measurement_circuit_spec_from_group(g) for g in groups]
    hadamard_specs = make_hadamard_test_specs(component.terms)
    return PauliCompilationResult(
        component=component,
        groups=groups,
        measurement_circuits=measurement_specs,
        hadamard_tests=hadamard_specs,
        warnings=warnings,
    )


def compile_registry_components(registry_path, output_dir, max_components: int | None = None) -> list[PauliCompilationResult]:
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    components = load_pauli_components_from_registry(registry_path)
    if max_components is not None:
        components = components[:max_components]

    results = []
    for component in components:
        result = compile_pauli_component(component)
        component_dir = output_dir / component.name
        component_dir.mkdir(parents=True, exist_ok=True)
        result.artifacts["component_json"] = str(export_pauli_component_json(component, component_dir / "component.json"))
        result.artifacts["groups_json"] = str(export_commuting_groups_json(result.groups, component_dir / "commuting_groups.json"))
        result.artifacts["measurement_circuits_json"] = str(export_measurement_specs_json(result.measurement_circuits, component_dir / "measurement_circuits.json"))
        result.artifacts["hadamard_tests_json"] = str(export_hadamard_specs_json(result.hadamard_tests, component_dir / "hadamard_tests.json"))
        result.artifacts["report"] = str(make_pauli_compilation_report(result, component_dir / "pauli_compilation_report.md"))
        results.append(result)

    manifest = {
        "package": "AZM-QOS v3.4 Pauli compiler",
        "registry_path": str(registry_path),
        "components": [r.component.name for r in results],
        "results": [
            {
                "component": r.component.name,
                "terms": len(r.component.terms),
                "groups": len(r.groups),
                "measurement_circuits": len(r.measurement_circuits),
                "hadamard_tests": len(r.hadamard_tests),
                "artifacts": r.artifacts,
            }
            for r in results
        ],
    }
    manifest_path = output_dir / "pauli_compilation_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, default=_json_default), encoding="utf-8")
    return results


def export_pauli_component_json(component: PauliComponent, path):
    path = Path(path)
    path.write_text(json.dumps(asdict(component), indent=2, default=_json_default), encoding="utf-8")
    return path


def export_commuting_groups_json(groups: list[CommutingGroup], path):
    path = Path(path)
    path.write_text(json.dumps([asdict(g) for g in groups], indent=2, default=_json_default), encoding="utf-8")
    return path


def export_measurement_specs_json(specs: list[MeasurementCircuitSpec], path):
    path = Path(path)
    path.write_text(json.dumps([asdict(s) for s in specs], indent=2, default=_json_default), encoding="utf-8")
    return path


def export_hadamard_specs_json(specs: list[HadamardTestSpec], path):
    path = Path(path)
    path.write_text(json.dumps([asdict(s) for s in specs], indent=2, default=_json_default), encoding="utf-8")
    return path


def make_pauli_compilation_report(result: PauliCompilationResult, output_path):
    output_path = Path(output_path)
    lines = [
        "# AZM-QOS v3.4 Pauli Compilation Report",
        "",
        "## Component",
        "",
        "```text",
        result.component.summary(),
        "```",
        "",
        "## Commuting groups",
        "",
    ]
    for group in result.groups:
        lines.extend(["```text", group.summary(), "```", ""])
    lines.extend(["## Measurement circuits", ""])
    for spec in result.measurement_circuits:
        lines.extend(["```text", spec.summary(), "```", ""])
    lines.extend(["## Hadamard-test scaffolds", ""])
    for spec in result.hadamard_tests:
        lines.extend(["```text", spec.summary(), "```", ""])
    if result.warnings:
        lines.extend(["## Warnings", ""])
        for warning in result.warnings:
            lines.append(f"- {warning}")
        lines.append("")
    lines.extend([
        "## Scientific note",
        "",
        "This compiler creates Pauli-measurement and Hadamard-test scaffolds. Final END/VQS production should attach the exact state-preparation circuit for each term/component.",
        "",
    ])
    output_path.write_text("\n".join(lines), encoding="utf-8")
    return output_path


def make_pauli_compile_demo(output_dir):
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    component = PauliComponent(
        name="demo_Mbb_00",
        quantity="M",
        indices=[0, 0],
        terms=[
            PauliTerm(0.5, "ZI", label="t0"),
            PauliTerm(-0.25, "IZ", label="t1"),
            PauliTerm(0.125, "ZZ", label="t2"),
            PauliTerm(0.1, "XX", label="t3"),
            PauliTerm(0.05, "YY", label="t4"),
        ],
        metadata={"component_family": "Mbb", "source": "demo"},
    )
    result = compile_pauli_component(component)
    result.artifacts["component_json"] = str(export_pauli_component_json(component, output_dir / "component.json"))
    result.artifacts["groups_json"] = str(export_commuting_groups_json(result.groups, output_dir / "commuting_groups.json"))
    result.artifacts["measurement_circuits_json"] = str(export_measurement_specs_json(result.measurement_circuits, output_dir / "measurement_circuits.json"))
    result.artifacts["hadamard_tests_json"] = str(export_hadamard_specs_json(result.hadamard_tests, output_dir / "hadamard_tests.json"))
    result.artifacts["report"] = str(make_pauli_compilation_report(result, output_dir / "pauli_compilation_report.md"))
    manifest = {
        "summary": result.summary(),
        "artifacts": result.artifacts,
    }
    manifest_path = output_dir / "pauli_compile_demo_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, default=_json_default), encoding="utf-8")
    result.artifacts["manifest"] = str(manifest_path)
    return result


def _json_default(obj):
    if isinstance(obj, complex):
        return [obj.real, obj.imag]
    return str(obj)
