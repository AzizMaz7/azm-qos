from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from azmqos_qec import (
    circuit_noise_sweep,
    run_circuit_level_decoder_sweep,
    export_circuit_level_decoder_sweep_csv,
    make_circuit_level_decoder_sweep_report,
)

print("AZM-QOS v1.7 Circuit-Level Decoder Sweep Demo")
print("=" * 70)

result = run_circuit_level_decoder_sweep(
    noise_specs=circuit_noise_sweep(two_qubit_errors=[0.0, 0.005, 0.01], readout_error=0.02),
    n_trials=10,
    n_rounds=5,
    shots=128,
    seed=123,
)

print(result.summary())

out_dir = ROOT / "outputs"
out_dir.mkdir(exist_ok=True)
csv_path = out_dir / "circuit_level_decoder_sweep.csv"
report_path = out_dir / "circuit_level_decoder_sweep_report.md"

export_circuit_level_decoder_sweep_csv(result, csv_path)
make_circuit_level_decoder_sweep_report(result, report_path)

print()
print("Saved CSV:", csv_path)
print("Saved report:", report_path)
