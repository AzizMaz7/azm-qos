from __future__ import annotations
from pathlib import Path
import numpy as np

def make_integrated_markdown_report(result, output_path: str | Path | None = None):
    lines = [
        "# AZM-QOS v1.0 Integrated Research Pipeline Report",
        "",
        "## Configuration",
        "",
        "```text",
        result.config.summary(),
        "```",
        "",
        "## Summary",
        "",
        "```text",
        result.summary(),
        "```",
        "",
        "## Assembled END/VQS M Matrix",
        "",
        "```text",
        str(np.asarray(result.M)),
        "```",
        "",
        "## Assembled END/VQS V Vector",
        "",
        "```text",
        str(np.asarray(result.V)),
        "```",
        "",
        "## QEC Syndrome",
        "",
        "```text",
        result.syndrome_result.summary(),
        "```",
        "",
        "## Decoder Result",
        "",
        "```text",
        result.decoder_result.summary(),
        "```",
        "",
        "## QEC Resource Estimate",
        "",
        "```text",
        result.qec_resource_estimate.summary(),
        "```",
        "",
        "## Logical Mapping Plan",
        "",
        "```text",
        result.logical_mapping_plan.summary(),
        "```",
        "",
        "## END/VQS Job Results",
        "",
    ]

    for job in result.endvqs_results:
        lines.extend([
            f"### {job.workload_name}",
            "",
            "```text",
            job.summary(),
            "```",
            "",
        ])

    lines.extend([
        "## QEC Job Results",
        "",
    ])

    for job in result.qec_results:
        lines.extend([
            f"### {job.workload_name}",
            "",
            "```text",
            job.summary(),
            "```",
            "",
        ])

    text = "\n".join(lines)

    if output_path is not None:
        output_path = Path(output_path)
        output_path.write_text(text, encoding="utf-8")

    return text

def make_manuscript_style_report(result, output_path: str | Path | None = None):
    """Create a compact manuscript-style report.

    This is not a full paper. It is a structured draft that can be extended
    into a thesis section or manuscript methods/results section.
    """
    lines = [
        "# AZM-QOS v1.0 Manuscript-Style Research Summary",
        "",
        "## Abstract",
        "",
        "We present an integrated AZM-QOS workflow connecting END/VQS-style observable estimation, QEC diagnostic workloads, backend selection, uncertainty-aware shot allocation, and automated report generation. The present v1.0 demonstration uses proxy Pauli decompositions to validate the software architecture; the terms can be replaced by derived problem-specific decompositions for production research.",
        "",
        "## Methods",
        "",
        "The pipeline constructs Pauli-observable workloads for an END/VQS M matrix and V vector, executes them through the AZM-QOS runtime manager, assembles numerical M and V objects, runs QEC stabilizer/logical diagnostic workloads, infers syndrome information, applies a placeholder decoder, and estimates measurement resources.",
        "",
        "## Results",
        "",
        "### M matrix",
        "",
        "```text",
        str(np.asarray(result.M)),
        "```",
        "",
        "### V vector",
        "",
        "```text",
        str(np.asarray(result.V)),
        "```",
        "",
        "### QEC diagnostic",
        "",
        "```text",
        result.syndrome_result.summary(),
        "",
        result.decoder_result.summary(),
        "```",
        "",
        "## Limitations",
        "",
        "The included END/VQS Pauli terms and logical mapping are placeholders. A research-grade version should replace these with the user's derived M and V Pauli decompositions and a code-specific logical encoding map.",
        "",
        "## Next step",
        "",
        "Replace the proxy END/VQS registry with derived Mbb, Mab, Va, Vb terms and extend the QEC plugin from stabilizer diagnostics to logical observable estimation.",
        "",
    ]

    text = "\n".join(lines)

    if output_path is not None:
        output_path = Path(output_path)
        output_path.write_text(text, encoding="utf-8")

    return text
