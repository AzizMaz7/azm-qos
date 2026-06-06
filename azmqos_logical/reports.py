from __future__ import annotations
from pathlib import Path
from .mapper import compare_registry_sizes
from .resources import estimate_logical_mapping_resources

def make_logical_mapping_report(physical_registry, logical_registry, encoding, output_path=None):
    comparison = compare_registry_sizes(physical_registry, logical_registry)
    estimate = estimate_logical_mapping_resources(physical_registry, encoding)

    lines = [
        "# AZM-QOS v1.2 Logical Observable Mapping Report",
        "",
        "## Encoding",
        "",
        "```text",
        encoding.summary(),
        "```",
        "",
        "## Registry size comparison",
        "",
        "```json",
        str(comparison),
        "```",
        "",
        "## Resource estimate",
        "",
        "```text",
        estimate.summary(),
        "```",
        "",
        "## Scientific note",
        "",
        "This logical mapping is a scaffold. Replace block-wise repetition mapping with code-specific logical Pauli operators for production QEC research.",
        "",
    ]

    text = "\n".join(lines)
    if output_path is not None:
        Path(output_path).write_text(text, encoding="utf-8")
    return text
