# AZM-QOS Core v0.7 IBM Runtime Adapter

v0.7 adds the first IBM Runtime adapter scaffold.

## New modules

```text
azmqos/cloud.py
azmqos/backend_selector.py
azmqos/ibm_runtime_adapter.py
azmqos/ibm_backends.py
```

## Main features

- Safe IBM Runtime diagnostics
- Optional `qiskit-ibm-runtime` import
- IBM backend metadata
- Cloud job status model
- Backend selector policy
- Safe failure behavior

## Why no automatic hardware submission yet?

IBM Runtime APIs and account access depend on:

- installed `qiskit-ibm-runtime` version
- saved IBM Quantum credentials
- channel / instance configuration
- backend access
- primitive API version
- circuit and observable compatibility

v0.7 provides the correct architecture without making unsafe assumptions.

## Next step

v0.8 or v0.7.1 should implement actual Sampler/Estimator submission after the user's IBM Runtime environment is confirmed.
