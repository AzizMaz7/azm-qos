# AZM-QOS v1.0 Integrated Research Pipeline

v1.0 adds:

```text
azmqos_pipeline
```

## Main package structure

```text
azmqos_pipeline/
   ├── __init__.py
   ├── config.py
   ├── mapping.py
   ├── pipeline.py
   └── reports.py
```

## Pipeline components

1. END/VQS workload construction
2. QEC workload construction
3. placeholder logical mapping plan
4. backend-aware execution
5. END/VQS M and V assembly
6. QEC syndrome inference
7. decoder placeholder
8. QEC resource estimate
9. integrated report generation

## Why this matters

This is the first release that behaves like a full research workflow rather than separate modules.
