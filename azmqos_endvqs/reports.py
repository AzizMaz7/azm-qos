from __future__ import annotations
from pathlib import Path
import numpy as np

def make_endvqs_report(benchmark_data: dict, output_path: str | Path | None = None):
    """Create a Markdown report for an END/VQS benchmark."""
    registry = benchmark_data["registry"]
    parameter_point = benchmark_data["parameter_point"]
    M = np.asarray(benchmark_data["M"])
    V = np.asarray(benchmark_data["V"])
    results = benchmark_data["results"]

    lines = [
        "# AZM-QOS END/VQS Plugin Report",
        "",
        "## Scientific status",
        "",
        "The default v0.8 END/VQS terms are proxy/demo terms. Replace them with real Pauli decompositions for research use.",
        "",
        "## Registry",
        "",
        "```text",
        registry.summary(),
        "```",
        "",
        "## Parameter point",
        "",
        "```json",
        str(parameter_point.to_dict()),
        "```",
        "",
        "## Assembled M matrix",
        "",
        "```text",
        str(M),
        "```",
        "",
        "## Assembled V vector",
        "",
        "```text",
        str(V),
        "```",
        "",
        "## Workload results",
        "",
    ]

    for result in results:
        lines.extend([
            f"### {result.workload_name}",
            "",
            "```text",
            result.summary(),
            "```",
            "",
        ])

    text = "\n".join(lines)

    if output_path is not None:
        output_path = Path(output_path)
        output_path.write_text(text, encoding="utf-8")

    return text
