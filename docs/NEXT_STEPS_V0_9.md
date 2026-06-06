# Next Steps: AZM-QOS Core v0.9

Recommended next milestone:

## QEC Plugin Implementation

Add a separated package:

```text
azmqos_qec
```

Suggested structure:

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

## Why v0.9 matters

Your broader thesis direction includes QEC. A separated QEC plugin can later connect to END/VQS logical observable estimation.
