from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any

@dataclass
class RegistryValidationResult:
    ok: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def summary(self):
        lines = [f"RegistryValidationResult(ok={self.ok})"]
        if self.errors:
            lines.append("Errors:")
            lines.extend(f"  - {e}" for e in self.errors)
        if self.warnings:
            lines.append("Warnings:")
            lines.extend(f"  - {w}" for w in self.warnings)
        if self.metadata:
            lines.append(f"Metadata: {self.metadata}")
        return "\n".join(lines)

def validate_term_registry(registry, dimension=None, require_full_m=True, require_full_v=True):
    errors, warnings = [], []
    dim = dimension or registry.dimension

    for key, terms in registry.m_terms.items():
        if not terms:
            errors.append(f"M{key} has no Pauli terms.")
            continue
        n = terms[0].n_qubits
        if any(t.n_qubits != n for t in terms):
            errors.append(f"M{key} contains inconsistent qubit counts.")
        for t in terms:
            if abs(t.coeff.imag) > 1e-12:
                warnings.append(f"M{key} term {t.name} has imaginary coefficient {t.coeff.imag}.")

    for key, terms in registry.v_terms.items():
        if not terms:
            errors.append(f"V{key} has no Pauli terms.")
            continue
        n = terms[0].n_qubits
        if any(t.n_qubits != n for t in terms):
            errors.append(f"V{key} contains inconsistent qubit counts.")
        for t in terms:
            if abs(t.coeff.imag) > 1e-12:
                warnings.append(f"V{key} term {t.name} has imaginary coefficient {t.coeff.imag}.")

    if require_full_m:
        for i in range(dim):
            for j in range(dim):
                if (i, j) not in registry.m_terms:
                    errors.append(f"Missing M entry {(i, j)}.")
    if require_full_v:
        for i in range(dim):
            if i not in registry.v_terms:
                errors.append(f"Missing V entry {i}.")

    return RegistryValidationResult(
        ok=len(errors) == 0,
        errors=errors,
        warnings=warnings,
        metadata={"dimension": dim, "M_entries": len(registry.m_terms), "V_entries": len(registry.v_terms)},
    )

def compare_m_entry_term_signatures(registry, i, j):
    a = registry.m_terms.get((i, j), [])
    b = registry.m_terms.get((j, i), [])
    sig_a = sorted((t.pauli, round(t.coeff.real, 12), round(t.coeff.imag, 12)) for t in a)
    sig_b = sorted((t.pauli, round(t.coeff.real, 12), round(t.coeff.imag, 12)) for t in b)
    return sig_a == sig_b, sig_a, sig_b

def m_symmetry_diagnostics(registry, dimension=None):
    dim = dimension or registry.dimension
    out = {}
    for i in range(dim):
        for j in range(i + 1, dim):
            same, sig_ij, sig_ji = compare_m_entry_term_signatures(registry, i, j)
            out[(i, j)] = {"symmetric_term_signature": same, "M_ij_signature": sig_ij, "M_ji_signature": sig_ji}
    return out
