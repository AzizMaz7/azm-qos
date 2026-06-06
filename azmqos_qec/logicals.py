from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any
from azmqos import PauliTerm

@dataclass
class LogicalObservableSpec:
    name: str
    logicals: list[PauliTerm]
    description: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def summary(self):
        lines = [f"LogicalObservableSpec: {self.name}"]
        for term in self.logicals:
            lines.append(f"  {term.name}: {term.pauli}")
        return "\n".join(lines)

def default_logical_observables(code_name: str):
    """Return simple logical-observable demos for known template codes."""
    if code_name == "repetition_code_3_demo":
        return LogicalObservableSpec(
            name="repetition_code_3_logicals",
            logicals=[
                PauliTerm(1.0, "ZZZ", label="logical_Z_proxy"),
                PauliTerm(1.0, "XXX", label="logical_X_proxy"),
            ],
            description="Proxy logical operators for repetition-code demo.",
            metadata={"code": code_name},
        )
    if code_name == "bell_pair_stabilizer_demo":
        return LogicalObservableSpec(
            name="bell_pair_logicals",
            logicals=[
                PauliTerm(1.0, "ZZ", label="logical_ZZ_proxy"),
                PauliTerm(1.0, "XX", label="logical_XX_proxy"),
            ],
            description="Logical/correlation observables for Bell demo.",
            metadata={"code": code_name},
        )
    if code_name == "ghz_3_stabilizer_demo":
        return LogicalObservableSpec(
            name="ghz_3_logicals",
            logicals=[
                PauliTerm(1.0, "ZZI", label="logical_ZZI_proxy"),
                PauliTerm(1.0, "XXX", label="logical_XXX_proxy"),
            ],
            description="Logical/correlation observables for GHZ demo.",
            metadata={"code": code_name},
        )
    raise KeyError(f"No default logical observables for code {code_name!r}.")
