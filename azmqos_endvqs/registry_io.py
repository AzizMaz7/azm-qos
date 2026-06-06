from __future__ import annotations
from pathlib import Path
import csv, json
from azmqos import PauliTerm
from .terms import create_custom_registry
from .components import ENDVQSComponent, ENDVQSComponentRegistry

def _term_to_dict(term):
    return {
        "label": term.label,
        "pauli": term.pauli,
        "coeff_real": term.coeff.real,
        "coeff_imag": term.coeff.imag,
    }

def _term_from_dict(data):
    return PauliTerm(
        complex(float(data.get("coeff_real", 0.0)), float(data.get("coeff_imag", 0.0))),
        data["pauli"],
        label=data.get("label"),
    )

def save_term_registry_json(registry, path):
    path = Path(path)
    data = {
        "metadata": registry.metadata,
        "m_terms": [
            {"i": i, "j": j, "terms": [_term_to_dict(t) for t in terms]}
            for (i, j), terms in registry.m_terms.items()
        ],
        "v_terms": [
            {"i": i, "terms": [_term_to_dict(t) for t in terms]}
            for i, terms in registry.v_terms.items()
        ],
    }
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return path

def load_term_registry_json(path):
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    m_terms = {(int(item["i"]), int(item["j"])): [_term_from_dict(t) for t in item["terms"]] for item in data.get("m_terms", [])}
    v_terms = {int(item["i"]): [_term_from_dict(t) for t in item["terms"]] for item in data.get("v_terms", [])}
    return create_custom_registry(m_terms=m_terms, v_terms=v_terms, **data.get("metadata", {}))

def save_component_registry_json(component_registry, path):
    path = Path(path)
    data = {
        "metadata": component_registry.metadata,
        "components": [
            {
                "name": comp.name,
                "quantity": comp.quantity,
                "indices": list(comp.indices) if comp.indices is not None else None,
                "description": comp.description,
                "metadata": comp.metadata,
                "terms": [_term_to_dict(t) for t in comp.terms],
            }
            for comp in component_registry.components.values()
        ],
    }
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return path

def load_component_registry_json(path):
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    reg = ENDVQSComponentRegistry(metadata=data.get("metadata", {}))
    for item in data.get("components", []):
        reg.add(ENDVQSComponent(
            name=item["name"],
            quantity=item["quantity"],
            indices=tuple(item["indices"]) if item.get("indices") is not None else None,
            terms=[_term_from_dict(t) for t in item.get("terms", [])],
            description=item.get("description", ""),
            metadata=item.get("metadata", {}),
        ))
    return reg

def save_term_registry_csv(registry, path):
    path = Path(path)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["quantity", "i", "j", "label", "pauli", "coeff_real", "coeff_imag"])
        for (i, j), terms in registry.m_terms.items():
            for term in terms:
                writer.writerow(["M", i, j, term.label, term.pauli, term.coeff.real, term.coeff.imag])
        for i, terms in registry.v_terms.items():
            for term in terms:
                writer.writerow(["V", i, "", term.label, term.pauli, term.coeff.real, term.coeff.imag])
    return path

def load_term_registry_csv(path):
    m_terms = {}
    v_terms = {}
    with Path(path).open("r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            term = PauliTerm(complex(float(row["coeff_real"]), float(row.get("coeff_imag") or 0.0)), row["pauli"], label=row.get("label") or None)
            if row["quantity"].upper() == "M":
                m_terms.setdefault((int(row["i"]), int(row["j"])), []).append(term)
            elif row["quantity"].upper() == "V":
                v_terms.setdefault(int(row["i"]), []).append(term)
            else:
                raise ValueError(f"Unknown quantity {row['quantity']!r}.")
    return create_custom_registry(m_terms=m_terms, v_terms=v_terms, source="csv_import", path=str(path))
