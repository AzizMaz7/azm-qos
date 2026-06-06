from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from azmqos_research import run_research_platform_pipeline, matplotlib_available

print("AZM-QOS v2.0 Figure Generation Demo")
print("=" * 70)
print("Matplotlib available:", matplotlib_available())

out_dir = ROOT / "outputs" / "figure_generation_demo"
result = run_research_platform_pipeline(output_dir=out_dir, shots=64, repeats=1, n_rounds=3, n_trials=5)

print("Generated figure artifacts:")
for key in ["m_matrix_figure", "v_vector_figure", "matching_failure_figure"]:
    print(f"  {key}: {result.artifacts[key]}")
