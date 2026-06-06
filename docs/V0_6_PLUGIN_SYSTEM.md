# AZM-QOS Core v0.6 Plugin System

v0.6 adds a formal plugin system.

## New modules

```text
azmqos/plugins.py
azmqos/plugin_templates.py
```

## Main classes

```python
PluginInfo
AZMQOSPlugin
PluginRegistry
```

## Built-in template plugins

```text
VQSPlugin
ENDVQSPlugin
QECPlugin
```

## Why plugins matter

The core should not know specific physics equations.

The core should only know:

```text
QuantumWorkload
PauliTerm
RuntimeManager
BackendAdapter
ErrorManager
JobResult
```

Specific domains should become plugins:

```text
azmqos-vqs
azmqos-endvqs
azmqos-qec
azmqos-chemistry
azmqos-qaoa
```

## END/VQS design rule

The END/VQS plugin should contain:

- M-matrix Pauli decompositions
- V-vector Pauli decompositions
- M/V assembly routines
- project-specific reports and figures

The core should not contain these directly.
