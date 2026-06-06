from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from azmqos_research import (
    PauliComponent,
    PauliTerm,
    ENDVQSStatePreparationConfig,
    DerivativeEstimatorConfig,
    DerivativeParameter,
    estimate_component_derivatives,
)

print("AZM-QOS v3.8 Finite-Difference Validation Demo")
print("=" * 70)

component = PauliComponent(
    name="demo_validation_component",
    quantity="M",
    indices=[0, 0],
    terms=[
        PauliTerm(0.5, "ZI"),
        PauliTerm(-0.25, "IZ"),
        PauliTerm(0.1, "XX"),
    ],
    metadata={"component_family": "Mbb"},
)

config = DerivativeEstimatorConfig(
    parameters=[DerivativeParameter("p", 0), DerivativeParameter("q", 0)],
    shots=256,
    backend="fallback",
)

estimates = estimate_component_derivatives(component, ENDVQSStatePreparationConfig(), config)

for estimate in estimates:
    print(estimate.summary())
    print()
