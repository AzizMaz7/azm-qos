from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from azmqos import (
    make_generic_two_qubit_workload,
    RuntimeManager,
    RuntimeConfig,
    ErrorManager,
    bootstrap_confidence_interval,
    ReadoutMitigationModel,
    linear_zero_noise_extrapolation,
)

workload = make_generic_two_qubit_workload()
manager = RuntimeManager()
error_manager = ErrorManager()

# Collect repeated estimates for bootstrap uncertainty.
samples = []
for seed in range(20):
    result = manager.run(
        workload,
        "shot_simulator",
        RuntimeConfig(shots=1024, repeats=1, seed=seed),
    )
    samples.append(result.estimate_mean.real)

ci = bootstrap_confidence_interval(samples, confidence=0.95, n_resamples=1000, seed=123)
allocation = error_manager.allocate_shots(workload, total_shots=4096, strategy="variance_aware")

print("AZM-QOS v0.5 Error Management Demo")
print("=" * 70)
print("Bootstrap CI for repeated total estimates:")
print(" ", ci.summary())
print()
print(allocation.summary())

# Readout mitigation placeholder example.
model = ReadoutMitigationModel([[0.97, 0.03], [0.05, 0.95]])
measured_z = 0.80
corrected_z = model.mitigate_z_expectation(measured_z)
print()
print("Readout mitigation placeholder:")
print(f"  measured <Z>  = {measured_z:+.6f}")
print(f"  corrected <Z> = {corrected_z:+.6f}")

# ZNE placeholder example.
zne = linear_zero_noise_extrapolation([1.0, 2.0, 3.0], [0.91, 0.84, 0.78])
print()
print("Zero-noise extrapolation placeholder:")
print(f"  extrapolated zero-noise value = {zne.extrapolated_zero_noise:+.6f}")
