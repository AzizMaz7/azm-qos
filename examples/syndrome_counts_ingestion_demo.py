from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from azmqos_research import (
    HardwareJobReference,
    synthetic_hardware_counts_for_job,
    compare_dry_run_to_hardware,
    normalize_counts,
)

print("AZM-QOS v4.5 Syndrome Counts Ingestion Demo")
print("=" * 70)

job = HardwareJobReference(
    job_id="example_job_001",
    backend_name="ibm_fez",
    circuit_id="example_syndrome_circuit",
    shots=100,
    dry_run_job_id="AZMQOS-DRYRUN-example",
)

record = synthetic_hardware_counts_for_job(job, n_bits=1)
comparison = compare_dry_run_to_hardware(job, record)

print(job.summary())
print(record.summary())
print(comparison.summary())
print("Normalized counts:", normalize_counts(record.counts, n_bits=1))
