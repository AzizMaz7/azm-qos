# AZM-QOS Startup Architecture Vision

## Core product

AZM-QOS Core is a general quantum workload operating layer.

## Plugin ecosystem

Specialized scientific communities can build plugins:

| Plugin | Target users |
|---|---|
| azmqos-vqs | dynamics / variational simulation researchers |
| azmqos-endvqs | END/VQS molecular dynamics researchers |
| azmqos-qec | QEC and logical-qubit researchers |
| azmqos-chemistry | VQE and molecular Hamiltonian users |
| azmqos-qaoa | optimization users |

## Commercial path

1. Open-source core
2. Research plugin ecosystem
3. Managed cloud runtime
4. Enterprise integrations
5. Hardware-provider backend adapters
6. QEC-ready execution layer
