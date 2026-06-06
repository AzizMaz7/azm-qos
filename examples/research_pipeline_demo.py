from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from azmqos_pipeline import ResearchPipelineConfig, run_integrated_research_pipeline

print("AZM-QOS v1.0 Research Pipeline Demo")
print("=" * 70)

config = ResearchPipelineConfig(
    backend_policy="shot_simulator",
    shots=2048,
    repeats=20,
    seed=123,
    qec_code="repetition3",
)

result = run_integrated_research_pipeline(config)

print(result.summary())
print()
print("M matrix:")
print(result.M)
print()
print("V vector:")
print(result.V)
print()
print("QEC syndrome:")
print(result.syndrome_result.summary())
print()
print("Decoder:")
print(result.decoder_result.summary())
