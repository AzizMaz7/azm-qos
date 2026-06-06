from pathlib import Path

def make_text_report(workload, result, output_path=None):
    lines = [
        "AZM-QOS Core v0.4 Runtime Report",
        "=" * 70,
        f"Workload: {workload.name}",
        f"Domain: {workload.domain}",
        f"Backend: {result.backend_name} ({result.backend_type})",
        f"Job ID: {result.job_id}",
        f"Qubits: {workload.n_qubits}",
        f"Observable terms: {len(workload.observables)}",
        f"Shots: {result.shots}",
        f"Repeats: {result.repeats}",
        "",
        "Term estimates:",
    ]
    for term, value in result.term_estimates.items():
        lines.append(f"  {term:24s} {value:+.10f}")
    lines += [
        "",
        f"Exact total:          {'N/A' if result.exact_total is None else f'{result.exact_total.real:+.10f}'}",
        f"Estimated total mean: {result.estimate_mean.real:+.10f}",
        f"Estimate std:         {result.estimate_std:.6e}",
        f"Mean absolute error:  {'N/A' if result.mean_absolute_error is None else f'{result.mean_absolute_error:.6e}'}",
        "",
        "Commuting groups:",
    ]
    for i, group in enumerate(workload.commuting_groups(), 1):
        labels = ", ".join(f"{t.name}:{t.pauli}" for t in group)
        lines.append(f"  Group {i}: {labels}")
    text = "\n".join(lines)
    if output_path:
        Path(output_path).write_text(text, encoding="utf-8")
    return text
