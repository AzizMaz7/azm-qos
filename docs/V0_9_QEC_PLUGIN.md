# AZM-QOS Core v0.9 QEC Plugin

v0.9 adds the separated package:

```text
azmqos_qec
```

## Package structure

```text
azmqos_qec/
   ├── __init__.py
   ├── stabilizers.py
   ├── logicals.py
   ├── builders.py
   ├── syndromes.py
   ├── decoders.py
   ├── resources.py
   └── plugin.py
```

## Main features

- Stabilizer-code specs
- Logical observable specs
- Stabilizer workloads
- Logical observable workloads
- Syndrome inference
- Decoder placeholder interface
- Majority-vote repetition decoder placeholder
- Resource estimates
- PluginRegistry integration

## Why this matters for your thesis direction

This QEC plugin can later connect to the END/VQS plugin so that M-matrix and V-vector observables are estimated as logical observables under an error-correcting code.
