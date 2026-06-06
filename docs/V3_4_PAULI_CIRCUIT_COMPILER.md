# AZM-QOS v3.4 END/VQS Pauli-Term Circuit Compiler

v3.4 adds the Pauli-term circuit compiler scaffold.

## New file

```text
azmqos_research/pauli_compiler.py
```

## Main command

```bash
azmqos pauli-compile --output-dir outputs/pauli_compile_demo
```

Compile a component registry:

```bash
azmqos pauli-compile --registry templates/endvqs_real_terms_template.json --output-dir outputs/compiled_terms
```

## Features

- parse Pauli terms
- group compatible Pauli strings
- create measurement-circuit specs
- create Hadamard-test specs
- extract expectations from measurement counts
- export JSON and Markdown compiler reports
