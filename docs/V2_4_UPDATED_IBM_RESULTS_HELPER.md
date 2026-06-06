# AZM-QOS v2.4 Updated IBM Result Helper

This updated v2.4 package includes:

```text
azmqos_research/ibm_results.py
```

## Latest job from any backend

```python
from azmqos_research import retrieve_ibm_hardware_result

result = retrieve_ibm_hardware_result()
print(result.summary())
print(result.counts)
```

## Latest job from a specific backend

```python
result = retrieve_ibm_hardware_result(backend_name="ibm_fez")
```

or:

```python
result = retrieve_ibm_hardware_result(backend_name="ibm_brisbane")
```

## Exact job ID

```python
result = retrieve_ibm_hardware_result(job_id="YOUR_JOB_ID_HERE")
```

## Compare with simulator counts

```python
from azmqos_research import compare_counts

simulator_counts = {"00": 510, "11": 514}
comparison = compare_counts(simulator_counts, result.counts)
print(comparison.summary())
```

`backend_name=None` means AZM-QOS uses the latest visible IBM Runtime job from any backend.
