from __future__ import annotations

from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any
import csv
import hashlib
import json
import math
import time

from .qec_logical import (
    StabilizerCodeSpec,
    LogicalObservableEstimate,
    ProductionQECResult,
    get_code_by_name,
    run_production_qec_estimator,
    run_qec_demo,
)
from .production import load_production_spec
from .experiment_db import (
    ExperimentDatabase,
    BackendMetadataRecord,
    new_run_record,
    artifact_from_path,
    export_run_table_csv,
    export_dashboard_json,
    make_run_database_report,
)
from .dashboard import build_dashboard_package


@dataclass
class SyndromeSample:
    component_name: str
    shot_index: int
    syndrome: str
    raw_logical_value: int
    true_error_qubit: int | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def summary(self) -> str:
        return (
            "SyndromeSample\n"
            f"  component: {self.component_name}\n"
            f"  shot: {self.shot_index}\n"
            f"  syndrome: {self.syndrome}\n"
            f"  raw_logical_value: {self.raw_logical_value}\n"
            f"  true_error_qubit: {self.true_error_qubit}"
        )


@dataclass
class DecoderResult:
    component_name: str
    syndrome: str
    correction: str
    corrected_logical_value: int
    accepted: bool
    metadata: dict[str, Any] = field(default_factory=dict)

    def summary(self) -> str:
        return (
            "DecoderResult\n"
            f"  component: {self.component_name}\n"
            f"  syndrome: {self.syndrome}\n"
            f"  correction: {self.correction}\n"
            f"  corrected_logical_value: {self.corrected_logical_value}\n"
            f"  accepted: {self.accepted}"
        )


@dataclass
class DecodedLogicalEstimate:
    component_name: str
    quantity: str
    family: str | None
    indices: list[int]
    code_name: str
    raw_estimate: float
    postselected_estimate: float
    corrected_estimate: float
    postselection_acceptance: float
    decoder_success_proxy: float
    uncertainty: float
    shots: int
    n_syndromes: int
    metadata: dict[str, Any] = field(default_factory=dict)

    def summary(self) -> str:
        return (
            "DecodedLogicalEstimate\n"
            f"  component: {self.component_name}\n"
            f"  quantity: {self.quantity}\n"
            f"  code: {self.code_name}\n"
            f"  raw_estimate: {self.raw_estimate:+.10f}\n"
            f"  postselected_estimate: {self.postselected_estimate:+.10f}\n"
            f"  corrected_estimate: {self.corrected_estimate:+.10f}\n"
            f"  postselection_acceptance: {self.postselection_acceptance:.6f}\n"
            f"  decoder_success_proxy: {self.decoder_success_proxy:.6f}\n"
            f"  uncertainty: {self.uncertainty:.8e}"
        )


@dataclass
class ProductionQECDecoderResult:
    project_name: str
    code: StabilizerCodeSpec
    decoded_estimates: list[DecodedLogicalEstimate]
    output_dir: str
    artifacts: dict[str, str] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def summary(self) -> str:
        by_quantity = {}
        for item in self.decoded_estimates:
            by_quantity[item.quantity] = by_quantity.get(item.quantity, 0) + 1
        return (
            "ProductionQECDecoderResult\n"
            f"  project: {self.project_name}\n"
            f"  code: {self.code.name}\n"
            f"  decoded_estimates: {len(self.decoded_estimates)}\n"
            f"  by_quantity: {by_quantity}\n"
            f"  artifacts: {len(self.artifacts)}\n"
            f"  warnings: {self.warnings}"
        )


def _json_default(obj):
    if isinstance(obj, complex):
        return [obj.real, obj.imag]
    return str(obj)


def _stable_unit_interval(text: str) -> float:
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
    intval = int(digest[:14], 16)
    return intval / float(16 ** 14 - 1)


def repetition_syndrome_for_error(error_qubit: int | None, distance: int) -> str:
    if error_qubit is None:
        return "0" * (distance - 1)
    bits = []
    for i in range(distance - 1):
        left = 1 if error_qubit == i else 0
        right = 1 if error_qubit == i + 1 else 0
        bits.append(str(left ^ right))
    return "".join(bits)


def repetition_lookup_table(distance: int = 3) -> dict[str, str]:
    table = {"0" * (distance - 1): "none"}
    for q in range(distance):
        table[repetition_syndrome_for_error(q, distance)] = f"X{q}"
    return table


def decode_repetition_syndrome(syndrome: str, distance: int = 3) -> str:
    table = repetition_lookup_table(distance)
    return table.get(str(syndrome), "unknown")


def apply_repetition_correction(raw_logical_value: int, correction: str, true_error_qubit: int | None = None) -> int:
    if correction == "unknown":
        return raw_logical_value
    if correction == "none":
        return raw_logical_value
    # Scaffold rule: if a correction is applied, flip the raw logical parity.
    return -raw_logical_value


def simulate_syndrome_samples(
    component_name: str,
    code: StabilizerCodeSpec,
    shots: int = 1024,
    physical_error_rate: float = 0.01,
) -> list[SyndromeSample]:
    distance = code.n_physical
    samples = []
    for shot in range(shots):
        u = _stable_unit_interval(f"{component_name}|{code.name}|shot|{shot}")
        if u < physical_error_rate:
            q_unit = _stable_unit_interval(f"{component_name}|{code.name}|qubit|{shot}")
            error_qubit = min(distance - 1, int(q_unit * distance))
        else:
            error_qubit = None

        syndrome = repetition_syndrome_for_error(error_qubit, distance)
        raw_logical = -1 if error_qubit is not None else 1
        samples.append(
            SyndromeSample(
                component_name=component_name,
                shot_index=shot,
                syndrome=syndrome,
                raw_logical_value=raw_logical,
                true_error_qubit=error_qubit,
                metadata={"physical_error_rate": physical_error_rate},
            )
        )
    return samples


def decode_syndrome_samples(samples: list[SyndromeSample], code: StabilizerCodeSpec) -> list[DecoderResult]:
    distance = code.n_physical
    results = []
    for sample in samples:
        correction = decode_repetition_syndrome(sample.syndrome, distance=distance)
        corrected = apply_repetition_correction(
            sample.raw_logical_value,
            correction,
            true_error_qubit=sample.true_error_qubit,
        )
        accepted = sample.syndrome == "0" * (distance - 1)
        results.append(
            DecoderResult(
                component_name=sample.component_name,
                syndrome=sample.syndrome,
                correction=correction,
                corrected_logical_value=corrected,
                accepted=accepted,
                metadata={
                    "shot_index": sample.shot_index,
                    "true_error_qubit": sample.true_error_qubit,
                    "raw_logical_value": sample.raw_logical_value,
                },
            )
        )
    return results


def mean(values: list[float], default: float = 0.0) -> float:
    return sum(values) / len(values) if values else default


def binomial_uncertainty(expectation: float, shots: int) -> float:
    if shots <= 0:
        return float("nan")
    return math.sqrt(max(0.0, 1.0 - expectation * expectation) / shots)


def decoded_estimate_from_logical_estimate(
    estimate: LogicalObservableEstimate,
    code: StabilizerCodeSpec,
    physical_error_rate: float = 0.01,
) -> DecodedLogicalEstimate:
    samples = simulate_syndrome_samples(
        estimate.component_name,
        code,
        shots=estimate.shots,
        physical_error_rate=physical_error_rate,
    )
    decoded = decode_syndrome_samples(samples, code)

    raw_values = [s.raw_logical_value for s in samples]
    accepted_values = [s.raw_logical_value for s in samples if s.syndrome == "0" * (code.n_physical - 1)]
    corrected_values = [d.corrected_logical_value for d in decoded]

    raw_factor = mean(raw_values, default=0.0)
    post_factor = mean(accepted_values, default=0.0)
    corr_factor = mean(corrected_values, default=0.0)

    base = float(estimate.logical_estimate.real)
    raw_est = base * raw_factor
    post_est = base * post_factor
    corr_est = base * corr_factor

    accepted = sum(1 for d in decoded if d.accepted)
    acceptance = accepted / max(1, len(decoded))

    known = sum(1 for d in decoded if d.correction != "unknown")
    success_proxy = known / max(1, len(decoded))

    uncertainty = binomial_uncertainty(corr_factor, max(1, len(decoded))) * abs(base)

    return DecodedLogicalEstimate(
        component_name=estimate.component_name,
        quantity=estimate.quantity,
        family=estimate.family,
        indices=list(estimate.indices),
        code_name=estimate.code_name,
        raw_estimate=raw_est,
        postselected_estimate=post_est,
        corrected_estimate=corr_est,
        postselection_acceptance=acceptance,
        decoder_success_proxy=success_proxy,
        uncertainty=uncertainty,
        shots=estimate.shots,
        n_syndromes=estimate.n_syndromes,
        metadata={
            "base_logical_estimate": base,
            "physical_error_rate": physical_error_rate,
            "n_samples": len(samples),
            "lookup_table": repetition_lookup_table(code.n_physical),
        },
    )


def export_syndrome_samples_csv(samples: list[SyndromeSample], path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["component_name", "shot_index", "syndrome", "raw_logical_value", "true_error_qubit"])
        for s in samples:
            writer.writerow([s.component_name, s.shot_index, s.syndrome, s.raw_logical_value, s.true_error_qubit])
    return path


def export_decoder_results_csv(results: list[DecoderResult], path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["component_name", "syndrome", "correction", "corrected_logical_value", "accepted"])
        for r in results:
            writer.writerow([r.component_name, r.syndrome, r.correction, r.corrected_logical_value, r.accepted])
    return path


def export_decoded_estimates_csv(estimates: list[DecodedLogicalEstimate], path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "component_name", "quantity", "family", "indices", "code_name",
            "raw_estimate", "postselected_estimate", "corrected_estimate",
            "postselection_acceptance", "decoder_success_proxy", "uncertainty",
            "shots", "n_syndromes"
        ])
        for e in estimates:
            writer.writerow([
                e.component_name,
                e.quantity,
                e.family,
                json.dumps(e.indices),
                e.code_name,
                e.raw_estimate,
                e.postselected_estimate,
                e.corrected_estimate,
                e.postselection_acceptance,
                e.decoder_success_proxy,
                e.uncertainty,
                e.shots,
                e.n_syndromes,
            ])
    return path


def export_decoded_estimates_json(estimates: list[DecodedLogicalEstimate], path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps([asdict(e) for e in estimates], indent=2, default=_json_default), encoding="utf-8")
    return path


def export_decoded_mv_tables(estimates: list[DecodedLogicalEstimate], output_dir):
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    m_path = output_dir / "M_decoded_logical_estimates.csv"
    v_path = output_dir / "V_decoded_logical_estimates.csv"
    for quantity, path in [("M", m_path), ("V", v_path)]:
        with path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([
                "component_name", "family", "indices", "code_name",
                "raw_estimate", "postselected_estimate", "corrected_estimate",
                "postselection_acceptance", "decoder_success_proxy", "uncertainty"
            ])
            for e in estimates:
                if e.quantity == quantity:
                    writer.writerow([
                        e.component_name,
                        e.family,
                        json.dumps(e.indices),
                        e.code_name,
                        e.raw_estimate,
                        e.postselected_estimate,
                        e.corrected_estimate,
                        e.postselection_acceptance,
                        e.decoder_success_proxy,
                        e.uncertainty,
                    ])
    return {"M_decoded_logical_estimates_csv": str(m_path), "V_decoded_logical_estimates_csv": str(v_path)}


def plot_decoded_estimates(estimates: list[DecodedLogicalEstimate], path):
    path = Path(path)
    try:
        import matplotlib.pyplot as plt
    except Exception:
        txt = path.with_suffix(".txt")
        txt.write_text("\n".join(e.summary() for e in estimates), encoding="utf-8")
        return txt

    labels = [e.component_name for e in estimates]
    raw = [e.raw_estimate for e in estimates]
    post = [e.postselected_estimate for e in estimates]
    corr = [e.corrected_estimate for e in estimates]
    x = list(range(len(labels)))

    fig = plt.figure()
    ax = fig.add_subplot(111)
    ax.plot(x, raw, marker="o", label="raw")
    ax.plot(x, post, marker="s", label="postselected")
    ax.plot(x, corr, marker="^", label="corrected")
    ax.set_xlabel("component")
    ax.set_ylabel("estimate")
    ax.set_title("QEC decoder: raw vs postselected vs corrected")
    if len(labels) <= 10:
        ax.set_xticks(x)
        ax.set_xticklabels(labels, rotation=45, ha="right")
    ax.legend()
    fig.tight_layout()
    fig.savefig(path, dpi=250)
    plt.close(fig)
    return path


def attach_decoded_estimates_to_database(spec, estimates: list[DecodedLogicalEstimate], database_path, artifact_paths: dict[str, str] | None = None):
    database_path = Path(database_path)
    db = ExperimentDatabase(database_path)
    artifact_paths = artifact_paths or {}
    records = []
    for e in estimates:
        artifacts = [
            artifact_from_path(path, name=name, artifact_type="qec_decoder_artifact")
            for name, path in artifact_paths.items()
        ]
        record = new_run_record(
            name=f"qec_decoded_{e.component_name}",
            run_type="qec_decoder_estimate",
            status="completed",
            tags=["qec", "decoder", e.family or "unknown", e.quantity],
            parameters={
                "component_name": e.component_name,
                "quantity": e.quantity,
                "indices": e.indices,
                "code_name": e.code_name,
                "shots": e.shots,
                "n_syndromes": e.n_syndromes,
            },
            metrics={
                "raw_estimate": e.raw_estimate,
                "postselected_estimate": e.postselected_estimate,
                "corrected_estimate": e.corrected_estimate,
                "postselection_acceptance": e.postselection_acceptance,
                "decoder_success_proxy": e.decoder_success_proxy,
                "uncertainty": e.uncertainty,
            },
            backend=BackendMetadataRecord(
                backend_name="local_qec_decoder",
                job_status="LOCAL_COMPLETED",
                timestamp_unix=time.time(),
            ),
            artifacts=artifacts,
            notes="QEC decoder and syndrome post-processing scaffold.",
        )
        db.append(record)
        records.append(record)
    return db, records


def make_qec_decoder_report(result: ProductionQECDecoderResult, output_path):
    output_path = Path(output_path)
    lines = [
        "# AZM-QOS v4.2 QEC Decoder and Syndrome Post-Processing Report",
        "",
        "## Summary",
        "",
        "```text",
        result.summary(),
        "```",
        "",
        "## Code",
        "",
        "```text",
        result.code.summary(),
        "```",
        "",
        "## Decoded estimates",
        "",
    ]
    for estimate in result.decoded_estimates:
        lines.extend(["```text", estimate.summary(), "```", ""])
    if result.warnings:
        lines.extend(["## Warnings", ""])
        for warning in result.warnings:
            lines.append(f"- {warning}")
        lines.append("")
    lines.extend(["## Artifacts", ""])
    for key, value in result.artifacts.items():
        lines.append(f"- **{key}**: `{value}`")
    lines.extend([
        "",
        "## Scientific note",
        "",
        "v4.2 decoder logic is a local scaffold for syndrome post-processing. For final QEC results, replace the lookup decoder and deterministic syndrome simulator with code-specific circuits, real syndrome counts, and validated decoding logic.",
        "",
    ])
    output_path.write_text("\n".join(lines), encoding="utf-8")
    return output_path


def run_qec_decoder_demo(output_dir):
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    qec = run_qec_demo(output_dir / "base_qec_demo")
    code = qec.code
    decoded = [
        decoded_estimate_from_logical_estimate(e, code, physical_error_rate=0.05)
        for e in qec.estimates
    ]

    # For demo, export samples/results for first estimate.
    samples = simulate_syndrome_samples(qec.estimates[0].component_name, code, shots=qec.estimates[0].shots, physical_error_rate=0.05)
    decoder_results = decode_syndrome_samples(samples, code)

    artifacts = {}
    artifacts["syndrome_samples_csv"] = str(export_syndrome_samples_csv(samples, output_dir / "syndrome_samples.csv"))
    artifacts["decoder_results_csv"] = str(export_decoder_results_csv(decoder_results, output_dir / "decoder_results.csv"))
    artifacts["decoded_estimates_csv"] = str(export_decoded_estimates_csv(decoded, output_dir / "decoded_estimates.csv"))
    artifacts["decoded_estimates_json"] = str(export_decoded_estimates_json(decoded, output_dir / "decoded_estimates.json"))
    artifacts.update(export_decoded_mv_tables(decoded, output_dir))
    artifacts["decoded_estimates_figure"] = str(plot_decoded_estimates(decoded, output_dir / "decoded_estimates.png"))

    result = ProductionQECDecoderResult(
        project_name="qec_decoder_demo",
        code=code,
        decoded_estimates=decoded,
        output_dir=str(output_dir),
        artifacts=artifacts,
        warnings=[],
    )
    artifacts["decoder_report"] = str(make_qec_decoder_report(result, output_dir / "qec_decoder_report.md"))

    manifest_path = output_dir / "qec_decoder_demo_manifest.json"
    manifest_path.write_text(json.dumps({
        "package": "AZM-QOS v4.2 QEC decoder demo",
        "summary": result.summary(),
        "artifacts": artifacts,
    }, indent=2, default=_json_default), encoding="utf-8")
    artifacts["manifest"] = str(manifest_path)

    return ProductionQECDecoderResult(
        project_name="qec_decoder_demo",
        code=code,
        decoded_estimates=decoded,
        output_dir=str(output_dir),
        artifacts=artifacts,
        warnings=[],
    )


def run_production_qec_decoder(
    spec_or_path,
    code_name: str = "repetition3",
    max_components: int | None = None,
    shots: int = 1024,
    physical_error_rate: float = 0.01,
):
    spec = load_production_spec(spec_or_path) if isinstance(spec_or_path, (str, Path)) else spec_or_path
    output_dir = Path(spec.output_dir) / "qec_decoder"
    output_dir.mkdir(parents=True, exist_ok=True)

    base = run_production_qec_estimator(
        spec,
        code_name=code_name,
        max_components=max_components,
        shots=shots,
        physical_error_rate=physical_error_rate,
    )
    code = base.code
    decoded = [
        decoded_estimate_from_logical_estimate(e, code, physical_error_rate=physical_error_rate)
        for e in base.estimates
    ]

    artifacts = {}
    artifacts["decoded_estimates_csv"] = str(export_decoded_estimates_csv(decoded, output_dir / "decoded_estimates.csv"))
    artifacts["decoded_estimates_json"] = str(export_decoded_estimates_json(decoded, output_dir / "decoded_estimates.json"))
    artifacts.update(export_decoded_mv_tables(decoded, output_dir))
    artifacts["decoded_estimates_figure"] = str(plot_decoded_estimates(decoded, output_dir / "decoded_estimates.png"))

    # Export samples/results for all components in compact CSVs.
    all_samples = []
    all_decoder_results = []
    for e in base.estimates:
        samples = simulate_syndrome_samples(e.component_name, code, shots=e.shots, physical_error_rate=physical_error_rate)
        all_samples.extend(samples)
        all_decoder_results.extend(decode_syndrome_samples(samples, code))
    artifacts["syndrome_samples_csv"] = str(export_syndrome_samples_csv(all_samples, output_dir / "syndrome_samples.csv"))
    artifacts["decoder_results_csv"] = str(export_decoder_results_csv(all_decoder_results, output_dir / "decoder_results.csv"))

    db, records = attach_decoded_estimates_to_database(
        spec=spec,
        estimates=decoded,
        database_path=Path(spec.output_dir) / "database" / "qec_decoder_estimates.jsonl",
        artifact_paths={
            "decoded_estimates_csv": artifacts["decoded_estimates_csv"],
            "syndrome_samples_csv": artifacts["syndrome_samples_csv"],
            "decoder_results_csv": artifacts["decoder_results_csv"],
        },
    )
    artifacts["decoder_database_jsonl"] = str(db.path)
    artifacts["decoder_run_table_csv"] = str(export_run_table_csv(records, Path(spec.output_dir) / "database" / "qec_decoder_run_table.csv"))
    artifacts["decoder_dashboard_json"] = str(export_dashboard_json(records, Path(spec.output_dir) / "database" / "qec_decoder_dashboard.json"))
    artifacts["decoder_database_report"] = str(make_run_database_report(records, Path(spec.output_dir) / "database" / "qec_decoder_database_report.md"))

    dashboard = build_dashboard_package(Path(spec.output_dir) / "dashboard_qec_decoder", database_path=db.path)
    artifacts["decoder_dashboard_manifest"] = dashboard.artifacts.get("manifest", "")
    artifacts["decoder_dashboard_html"] = dashboard.artifacts.get("dashboard_html", "")

    result = ProductionQECDecoderResult(
        project_name=spec.project_name,
        code=code,
        decoded_estimates=decoded,
        output_dir=str(output_dir),
        artifacts=artifacts,
        warnings=list(base.warnings),
        metadata={
            "base_qec_artifacts": base.artifacts,
            "physical_error_rate": physical_error_rate,
        },
    )
    artifacts["decoder_report"] = str(make_qec_decoder_report(result, output_dir / "qec_decoder_report.md"))

    manifest_path = output_dir / "production_qec_decoder_manifest.json"
    manifest_path.write_text(json.dumps({
        "package": "AZM-QOS v4.2 production QEC decoder",
        "project": spec.project_name,
        "summary": result.summary(),
        "warnings": result.warnings,
        "artifacts": artifacts,
    }, indent=2, default=_json_default), encoding="utf-8")
    artifacts["manifest"] = str(manifest_path)

    return ProductionQECDecoderResult(
        project_name=spec.project_name,
        code=code,
        decoded_estimates=decoded,
        output_dir=str(output_dir),
        artifacts=artifacts,
        warnings=list(base.warnings),
        metadata={
            "base_qec_artifacts": base.artifacts,
            "physical_error_rate": physical_error_rate,
        },
    )
