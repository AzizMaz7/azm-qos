# AZM-QOS v1.1 END/VQS Real-Term Registry

v1.1 adds infrastructure to replace proxy END/VQS terms with real Pauli decompositions.

## New files

```text
azmqos_endvqs/components.py
azmqos_endvqs/registry_io.py
azmqos_endvqs/validation.py
templates/endvqs_real_terms_template.json
```

## Workflow

1. Open `templates/endvqs_real_terms_template.json`.
2. Replace placeholder terms with derived `Mbb`, `Mab`, `Maa`, `Va`, `Vb` Pauli terms.
3. Run `python examples\endvqs_real_terms_template_demo.py`.
4. Validate using `validate_term_registry`.
5. Run the integrated v1.0/v1.1 pipeline with your registry.
