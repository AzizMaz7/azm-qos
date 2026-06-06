from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pathlib import Path
from azmqos_research import (
    HardwareJobReference,
    RuntimeFetchConfig,
    fetch_job_with_retry,
)

print("AZM-QOS v4.6 Runtime Cache Demo")
print("=" * 70)

cache_dir = ROOT / "outputs" / "runtime_cache_demo" / "cache"
job = HardwareJobReference(
    job_id="cache_demo_job",
    backend_name="ibm_fez",
    circuit_id="cache_demo_circuit",
    shots=64,
)

config = RuntimeFetchConfig(enable_runtime_fetch=False, use_cache=True)

first = fetch_job_with_retry(job, config, cache_dir=cache_dir)
second = fetch_job_with_retry(job, config, cache_dir=cache_dir)

print("First fetch:")
print(first.summary())
print()
print("Second fetch:")
print(second.summary())
print()
print("Cache path:", second.cache_path)
