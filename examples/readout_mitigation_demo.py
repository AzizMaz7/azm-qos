from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from azmqos_research import (
    mock_calibration_snapshot,
    readout_matrices_from_calibration,
    mitigate_counts_readout,
    mitigated_probabilities_to_pseudo_counts,
)

print("AZM-QOS v2.5 Readout Mitigation Demo")
print("=" * 70)

counts = {"00": 470, "01": 30, "10": 34, "11": 490}
calibration = mock_calibration_snapshot()
matrices = readout_matrices_from_calibration(calibration, n_qubits=2)
result = mitigate_counts_readout(counts, matrices)
pseudo = mitigated_probabilities_to_pseudo_counts(result.mitigated_probabilities, sum(counts.values()))

print(calibration.summary())
print()
print(result.summary())
print()
print("Mitigated probabilities:")
for k, v in sorted(result.mitigated_probabilities.items()):
    print(f"  {k}: {v:.6f}")
print()
print("Pseudo-counts:", pseudo)
