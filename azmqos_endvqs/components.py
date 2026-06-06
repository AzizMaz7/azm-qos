from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any
from azmqos import PauliTerm
from .terms import ENDVQSTermRegistry, default_endvqs_registry

@dataclass
class ENDVQSComponent:
    """Named END/VQS component such as Mbb, Mab, Maa, Va, or Vb."""
    name: str
    quantity: str
    terms: list[PauliTerm]
    indices: tuple[int, int] | tuple[int] | None = None
    description: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

@dataclass
class ENDVQSComponentRegistry:
    """Research-facing named-component registry."""
    components: dict[str, ENDVQSComponent] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    def add(self, component: ENDVQSComponent):
        if component.name in self.components:
            raise ValueError(f"Component {component.name!r} already exists.")
        self.components[component.name] = component

    def get(self, name: str) -> ENDVQSComponent:
        return self.components[name]

    def list_components(self):
        return list(self.components.keys())

    def summary(self):
        lines = ["ENDVQSComponentRegistry", f"  components: {len(self.components)}", f"  metadata: {self.metadata}"]
        for name, comp in self.components.items():
            lines.append(f"  {name}: quantity={comp.quantity}, terms={len(comp.terms)}, indices={comp.indices}")
        return "\n".join(lines)

def default_component_registry_from_proxy_terms() -> ENDVQSComponentRegistry:
    base = default_endvqs_registry()
    reg = ENDVQSComponentRegistry(metadata={
        "source": "default_proxy_terms",
        "warning": "Replace with real END/VQS Pauli decompositions.",
    })
    reg.add(ENDVQSComponent("Mbb_proxy_00", "M", base.get_m_terms(0, 0), (0, 0), "Proxy Mbb diagonal term."))
    reg.add(ENDVQSComponent("Mab_proxy_01", "M", base.get_m_terms(0, 1), (0, 1), "Proxy Mab off-diagonal term."))
    reg.add(ENDVQSComponent("Mab_proxy_10", "M", base.get_m_terms(1, 0), (1, 0), "Proxy Mab reverse off-diagonal term."))
    reg.add(ENDVQSComponent("Maa_proxy_11", "M", base.get_m_terms(1, 1), (1, 1), "Proxy Maa diagonal term."))
    reg.add(ENDVQSComponent("Va_proxy_0", "V", base.get_v_terms(0), (0,), "Proxy Va vector term."))
    reg.add(ENDVQSComponent("Vb_proxy_1", "V", base.get_v_terms(1), (1,), "Proxy Vb vector term."))
    return reg

def component_registry_to_term_registry(component_registry: ENDVQSComponentRegistry) -> ENDVQSTermRegistry:
    m_terms = {}
    v_terms = {}
    for comp in component_registry.components.values():
        q = comp.quantity.upper()
        if q == "M":
            if comp.indices is None or len(comp.indices) != 2:
                raise ValueError(f"M component {comp.name} requires two indices.")
            i, j = comp.indices
            m_terms[(int(i), int(j))] = comp.terms
        elif q == "V":
            if comp.indices is None or len(comp.indices) != 1:
                raise ValueError(f"V component {comp.name} requires one index.")
            i = comp.indices[0]
            v_terms[int(i)] = comp.terms
        else:
            raise ValueError(f"Unknown END/VQS quantity: {comp.quantity}")
    return ENDVQSTermRegistry(
        m_terms=m_terms,
        v_terms=v_terms,
        metadata={"source": "component_registry", **component_registry.metadata},
    )
