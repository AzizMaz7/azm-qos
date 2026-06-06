# AZM-QOS v2.9 Real IBM Job Sync Guide

v2.9 does not submit jobs. It only retrieves existing job statuses/results.

For one real job:

```python
from azmqos_research import sync_ibm_job

result = sync_ibm_job(
    job_id="YOUR_JOB_ID",
    output_dir="outputs/synced_job",
    simulator_counts={"00": 510, "11": 514},
)
print(result.summary())
```

For database sync, create payloads or extend the workflow to call IBM for every job ID in the database.

The safe demo uses mock payloads:

```python
from azmqos_research import run_mock_sync_workflow
summary = run_mock_sync_workflow("outputs/sync_demo")
```
