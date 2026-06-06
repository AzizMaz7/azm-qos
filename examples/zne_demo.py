from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from azmqos_research import zero_noise_extrapolate, plot_zne

print("AZM-QOS v2.5 Zero-Noise Extrapolation Demo")
print("=" * 70)

result = zero_noise_extrapolate([1.0, 2.0, 3.0], [0.91, 0.84, 0.76], fit_order=1)

out_dir = ROOT / "outputs" / "zne_demo"
out_dir.mkdir(parents=True, exist_ok=True)
fig_path = plot_zne(result, out_dir / "zne.png")

print(result.summary())
print("Saved figure:", fig_path)
