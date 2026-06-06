# QEC Plugin Design

The QEC plugin should support:

- stabilizer generators
- logical Pauli operators
- syndrome extraction workloads
- decoder interface placeholder
- logical observable estimation
- resource estimates

The core only needs to know that the plugin returns QuantumWorkload objects.
