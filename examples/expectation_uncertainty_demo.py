from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from azmqos_research import (
    bootstrap_expectation_uncertainty,
    parity_observable_map,
    propagate_difference_uncertainty,
)

print("AZM-QOS v2.6 Expectation Uncertainty Demo")
print("=" * 70)

simulator_counts = {"00": 510, "11": 514}
hardware_counts = {"00": 470, "01": 30, "10": 34, "11": 490}

observable = parity_observable_map(2)

sim = bootstrap_expectation_uncertainty(simulator_counts, observable, n_bootstrap=500, seed=1)
hw = bootstrap_expectation_uncertainty(hardware_counts, observable, n_bootstrap=500, seed=2)
diff = propagate_difference_uncertainty(sim.estimate, sim.standard_error, hw.estimate, hw.standard_error)

print(sim.summary())
print()
print(hw.summary())
print()
print(diff.summary())
