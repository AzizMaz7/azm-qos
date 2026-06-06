from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from azmqos_research import (
    ENDVQSStatePreparationConfig,
    make_derivative_stateprep_config,
    make_endvqs_stateprep_plan,
)

print("AZM-QOS v3.7 Derivative State-Preparation Demo")
print("=" * 70)

base = ENDVQSStatePreparationConfig()

for derivative in ["p", "q", "alpha", "beta"]:
    cfg = make_derivative_stateprep_config(base, derivative=derivative, derivative_index=0)
    plan = make_endvqs_stateprep_plan(cfg)
    print(plan.summary())
    print("Last operation:", plan.operations[-1].summary())
    print()
