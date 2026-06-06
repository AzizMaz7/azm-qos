# AZM-QOS v4.1 Initial QEC/Logical-Qubit Extension

v4.1 adds the first QEC/logical-qubit scaffold to AZM-QOS.

## Required first production command

```powershell
azmqos production-init --output-dir outputs\production_project --project-name my_endvqs_project
```

## New file

```text
azmqos_research/qec_logical.py
```

## Main commands

Standalone demo:

```powershell
azmqos qec-demo --output-dir outputs\qec_demo
```

Production QEC-aware estimates:

```powershell
azmqos production-qec-estimate --config outputs\production_project\azmqos_production.json --code repetition3 --max-components 2 --shots 64
```

## Features

- stabilizer-code dataclasses
- repetition-code scaffold
- five-qubit-code scaffold metadata
- logical Pauli mapping
- syndrome measurement specs
- logical observable estimator
- QEC-aware M/V tables
- QEC dashboard artifacts
