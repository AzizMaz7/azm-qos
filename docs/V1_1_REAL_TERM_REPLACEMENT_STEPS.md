# Real END/VQS Term Replacement Steps

Represent each derived expression as:

```json
{
  "label": "Mab_P1P2_component",
  "pauli": "XX",
  "coeff_real": -0.5,
  "coeff_imag": 0.0
}
```

Use component families:

```text
Mbb
Mab
Maa
Va
Vb
```

Then run:

```bash
python examples\endvqs_real_terms_template_demo.py
```
