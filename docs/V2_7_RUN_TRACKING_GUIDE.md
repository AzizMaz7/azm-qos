# AZM-QOS v2.7 Run Tracking Guide

Create a database:

```python
from azmqos_research import ExperimentDatabase

db = ExperimentDatabase("outputs/runs.jsonl")
```

Create and append a run:

```python
from azmqos_research import new_run_record

record = new_run_record(
    name="my_hardware_run",
    run_type="hardware",
    status="completed",
    tags=["ibm", "sampler"],
    metrics={"tvd": 0.05},
)
db.append(record)
```

Query:

```python
hardware_runs = db.query(run_type="hardware")
good_runs = db.query(metric_max={"tvd": 0.1})
```
