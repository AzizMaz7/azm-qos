from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from azmqos_qec import default_circuit_noise_spec, save_circuit_noise_spec_json, qiskit_aer_noise_available

print("AZM-QOS v1.6 Circuit Noise Model Demo")
print("=" * 70)

spec = default_circuit_noise_spec()
print(spec.summary())
print("Qiskit Aer noise available:", qiskit_aer_noise_available())

out_dir = ROOT / "outputs"
out_dir.mkdir(exist_ok=True)
path = out_dir / "circuit_noise_spec.json"
save_circuit_noise_spec_json(spec, path)
print("Saved noise spec:", path)

if qiskit_aer_noise_available():
    from azmqos_qec import build_qiskit_aer_noise_model
    noise_model = build_qiskit_aer_noise_model(spec)
    print("Built Qiskit Aer NoiseModel:", noise_model)
else:
    print("Qiskit Aer not installed; skipped actual NoiseModel construction.")
