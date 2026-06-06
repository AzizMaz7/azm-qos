from __future__ import annotations

from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any
import csv
import html
import json
import math
import statistics
import time

from .experiment_db import (
    ExperimentDatabase,
    ExperimentRunRecord,
    ArtifactRecord,
    create_demo_run_database,
    export_run_table_csv,
    export_dashboard_json,
    make_run_database_report,
    summarize_records,
)


@dataclass
class MetricTrendPoint:
    run_id: str
    run_name: str
    created_at_unix: float
    run_type: str
    backend_name: str | None
    metric_name: str
    metric_value: float

    def to_dict(self):
        return asdict(self)


@dataclass
class MetricTrendResult:
    metric_name: str
    points: list[MetricTrendPoint]
    metadata: dict[str, Any] = field(default_factory=dict)

    def summary(self) -> str:
        if not self.points:
            return f"MetricTrendResult(metric={self.metric_name}, points=0)"
        values = [p.metric_value for p in self.points]
        return (
            f"MetricTrendResult(metric={self.metric_name}, points={len(self.points)}, "
            f"min={min(values):.8g}, max={max(values):.8g}, mean={statistics.mean(values):.8g})"
        )


@dataclass
class BackendHistoryEntry:
    backend_name: str
    run_count: int
    job_ids: list[str]
    metric_summary: dict[str, dict[str, float]]
    latest_timestamp_unix: float | None = None

    def to_dict(self):
        return asdict(self)

    def summary(self) -> str:
        return (
            f"BackendHistoryEntry(backend={self.backend_name}, runs={self.run_count}, "
            f"metrics={list(self.metric_summary.keys())})"
        )


@dataclass
class DashboardPackage:
    output_dir: str
    records_count: int
    artifacts: dict[str, str]
    summary: dict[str, Any]

    def summary_text(self) -> str:
        return (
            "DashboardPackage\n"
            f"  output_dir: {self.output_dir}\n"
            f"  records_count: {self.records_count}\n"
            f"  artifacts: {len(self.artifacts)}\n"
            f"  summary: {self.summary}"
        )


def collect_metric_trend(records: list[ExperimentRunRecord], metric_name: str) -> MetricTrendResult:
    points = []
    for record in sorted(records, key=lambda r: r.created_at_unix):
        if metric_name not in record.metrics:
            continue
        backend_name = record.backend.backend_name if record.backend else None
        points.append(
            MetricTrendPoint(
                run_id=record.run_id,
                run_name=record.name,
                created_at_unix=record.created_at_unix,
                run_type=record.run_type,
                backend_name=backend_name,
                metric_name=metric_name,
                metric_value=float(record.metrics[metric_name]),
            )
        )
    return MetricTrendResult(metric_name=metric_name, points=points)


def export_metric_trend_csv(result: MetricTrendResult, path):
    path = Path(path)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "run_id", "run_name", "created_at_unix", "run_type", "backend_name", "metric_name", "metric_value"
        ])
        for p in result.points:
            writer.writerow([
                p.run_id,
                p.run_name,
                p.created_at_unix,
                p.run_type,
                p.backend_name or "",
                p.metric_name,
                p.metric_value,
            ])
    return path


def plot_metric_trend(result: MetricTrendResult, path):
    path = Path(path)
    try:
        import matplotlib.pyplot as plt
    except Exception:
        txt = path.with_suffix(".txt")
        txt.write_text(result.summary(), encoding="utf-8")
        return txt

    x = list(range(len(result.points)))
    y = [p.metric_value for p in result.points]
    labels = [p.run_name for p in result.points]

    fig = plt.figure()
    ax = fig.add_subplot(111)
    ax.plot(x, y, marker="o")
    ax.set_xlabel("run index")
    ax.set_ylabel(result.metric_name)
    ax.set_title(f"Metric trend: {result.metric_name}")
    if len(labels) <= 8:
        ax.set_xticks(x)
        ax.set_xticklabels(labels, rotation=45, ha="right")
    fig.tight_layout()
    fig.savefig(path, dpi=250)
    plt.close(fig)
    return path


def backend_performance_history(records: list[ExperimentRunRecord]) -> list[BackendHistoryEntry]:
    grouped: dict[str, list[ExperimentRunRecord]] = {}
    for record in records:
        if record.backend and record.backend.backend_name:
            grouped.setdefault(record.backend.backend_name, []).append(record)

    entries = []
    for backend_name, items in sorted(grouped.items()):
        metric_values: dict[str, list[float]] = {}
        job_ids = []
        latest = None
        for record in items:
            latest = record.created_at_unix if latest is None else max(latest, record.created_at_unix)
            if record.backend and record.backend.job_id:
                job_ids.append(record.backend.job_id)
            for k, v in record.metrics.items():
                metric_values.setdefault(k, []).append(float(v))

        metric_summary = {}
        for k, vals in metric_values.items():
            metric_summary[k] = {
                "count": float(len(vals)),
                "min": min(vals),
                "max": max(vals),
                "mean": sum(vals) / len(vals),
            }

        entries.append(
            BackendHistoryEntry(
                backend_name=backend_name,
                run_count=len(items),
                job_ids=job_ids,
                metric_summary=metric_summary,
                latest_timestamp_unix=latest,
            )
        )
    return entries


def export_backend_history_csv(entries: list[BackendHistoryEntry], path):
    path = Path(path)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["backend_name", "run_count", "job_ids", "metric_name", "count", "min", "max", "mean", "latest_timestamp_unix"])
        for entry in entries:
            if not entry.metric_summary:
                writer.writerow([entry.backend_name, entry.run_count, ",".join(entry.job_ids), "", "", "", "", "", entry.latest_timestamp_unix])
                continue
            for metric_name, summary in entry.metric_summary.items():
                writer.writerow([
                    entry.backend_name,
                    entry.run_count,
                    ",".join(entry.job_ids),
                    metric_name,
                    summary.get("count"),
                    summary.get("min"),
                    summary.get("max"),
                    summary.get("mean"),
                    entry.latest_timestamp_unix,
                ])
    return path


def collect_artifacts(records: list[ExperimentRunRecord]) -> list[dict[str, Any]]:
    rows = []
    for record in records:
        for artifact in record.artifacts:
            rows.append({
                "run_id": record.run_id,
                "run_name": record.name,
                "run_type": record.run_type,
                "artifact_name": artifact.name,
                "artifact_type": artifact.artifact_type,
                "path": artifact.path,
                "description": artifact.description,
                "exists": artifact.metadata.get("exists") if artifact.metadata else None,
            })
    return rows


def export_artifact_index_csv(records: list[ExperimentRunRecord], path):
    rows = collect_artifacts(records)
    path = Path(path)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["run_id", "run_name", "run_type", "artifact_name", "artifact_type", "path", "description", "exists"],
        )
        writer.writeheader()
        for row in rows:
            writer.writerow(row)
    return path


def make_artifact_browser_html(records: list[ExperimentRunRecord], output_path):
    output_path = Path(output_path)
    rows = collect_artifacts(records)

    body = [
        "<!DOCTYPE html>",
        "<html><head><meta charset='utf-8'><title>AZM-QOS Artifact Browser</title>",
        "<style>body{font-family:Arial,sans-serif;margin:2rem;} table{border-collapse:collapse;width:100%;} th,td{border:1px solid #ccc;padding:0.4rem;text-align:left;} th{background:#f4f4f4;} code{white-space:nowrap;}</style>",
        "</head><body>",
        "<h1>AZM-QOS Artifact Browser</h1>",
        f"<p>Total artifacts: {len(rows)}</p>",
        "<table>",
        "<tr><th>Run</th><th>Type</th><th>Artifact</th><th>Artifact Type</th><th>Path</th><th>Exists</th></tr>",
    ]
    for row in rows:
        path = html.escape(str(row["path"]))
        body.append(
            "<tr>"
            f"<td>{html.escape(str(row['run_name']))}</td>"
            f"<td>{html.escape(str(row['run_type']))}</td>"
            f"<td>{html.escape(str(row['artifact_name']))}</td>"
            f"<td>{html.escape(str(row['artifact_type']))}</td>"
            f"<td><code>{path}</code></td>"
            f"<td>{html.escape(str(row['exists']))}</td>"
            "</tr>"
        )
    body.extend(["</table>", "</body></html>"])
    output_path.write_text("\n".join(body), encoding="utf-8")
    return output_path


def make_dashboard_html(records: list[ExperimentRunRecord], output_path, metric_names: list[str] | None = None):
    output_path = Path(output_path)
    summary = summarize_records(records)
    metric_names = metric_names or sorted(summary.get("metrics", {}).keys())

    body = [
        "<!DOCTYPE html>",
        "<html><head><meta charset='utf-8'><title>AZM-QOS Dashboard</title>",
        "<style>body{font-family:Arial,sans-serif;margin:2rem;} .card{border:1px solid #ccc;border-radius:8px;padding:1rem;margin:1rem 0;} table{border-collapse:collapse;width:100%;} th,td{border:1px solid #ccc;padding:0.4rem;text-align:left;} th{background:#f4f4f4;} code{white-space:nowrap;}</style>",
        "</head><body>",
        "<h1>AZM-QOS Dashboard</h1>",
        f"<p>Generated at Unix time: {time.time():.3f}</p>",
        "<div class='card'><h2>Summary</h2><pre>",
        html.escape(json.dumps(summary, indent=2, default=str)),
        "</pre></div>",
        "<div class='card'><h2>Metric Trends</h2>",
    ]

    for metric in metric_names:
        trend = collect_metric_trend(records, metric)
        body.append(f"<h3>{html.escape(metric)}</h3>")
        body.append("<table><tr><th>Index</th><th>Run</th><th>Type</th><th>Backend</th><th>Value</th></tr>")
        for idx, p in enumerate(trend.points):
            body.append(
                "<tr>"
                f"<td>{idx}</td>"
                f"<td>{html.escape(p.run_name)}</td>"
                f"<td>{html.escape(p.run_type)}</td>"
                f"<td>{html.escape(str(p.backend_name or ''))}</td>"
                f"<td>{p.metric_value:.8g}</td>"
                "</tr>"
            )
        body.append("</table>")

    body.append("</div>")
    body.append("<div class='card'><h2>Runs</h2><table>")
    body.append("<tr><th>Name</th><th>Type</th><th>Status</th><th>Tags</th><th>Backend</th><th>Metrics</th><th>Artifacts</th></tr>")
    for r in records:
        backend = r.backend.backend_name if r.backend else ""
        body.append(
            "<tr>"
            f"<td>{html.escape(r.name)}</td>"
            f"<td>{html.escape(r.run_type)}</td>"
            f"<td>{html.escape(r.status)}</td>"
            f"<td>{html.escape(', '.join(r.tags))}</td>"
            f"<td>{html.escape(str(backend))}</td>"
            f"<td><code>{html.escape(json.dumps(r.metrics, default=str))}</code></td>"
            f"<td>{len(r.artifacts)}</td>"
            "</tr>"
        )
    body.extend(["</table></div>", "</body></html>"])
    output_path.write_text("\n".join(body), encoding="utf-8")
    return output_path


def make_dashboard_markdown_report(records: list[ExperimentRunRecord], output_path):
    output_path = Path(output_path)
    summary = summarize_records(records)
    backend_entries = backend_performance_history(records)

    lines = [
        "# AZM-QOS v2.8 Dashboard Report",
        "",
        "## Summary",
        "",
        "```json",
        json.dumps(summary, indent=2, default=str),
        "```",
        "",
        "## Backend history",
        "",
    ]
    if backend_entries:
        for entry in backend_entries:
            lines.extend(["```text", entry.summary(), "```", ""])
    else:
        lines.append("No backend history records found.")
        lines.append("")

    lines.extend(["## Runs", ""])
    for r in records:
        lines.extend(["```text", r.summary(), "```", ""])

    output_path.write_text("\n".join(lines), encoding="utf-8")
    return output_path


def build_dashboard_package(output_dir, database_path=None, records: list[ExperimentRunRecord] | None = None):
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    if records is None:
        if database_path is None:
            db, records, _ = create_demo_run_database(output_dir / "demo_database")
        else:
            db = ExperimentDatabase(database_path)
            records = db.read_all()
    else:
        db = None

    artifacts = {}
    artifacts["run_table_csv"] = str(export_run_table_csv(records, output_dir / "run_table.csv"))
    artifacts["dashboard_json"] = str(export_dashboard_json(records, output_dir / "dashboard.json"))
    artifacts["dashboard_html"] = str(make_dashboard_html(records, output_dir / "dashboard.html"))
    artifacts["artifact_index_csv"] = str(export_artifact_index_csv(records, output_dir / "artifact_index.csv"))
    artifacts["artifact_browser_html"] = str(make_artifact_browser_html(records, output_dir / "artifact_browser.html"))
    artifacts["backend_history_csv"] = str(export_backend_history_csv(backend_performance_history(records), output_dir / "backend_history.csv"))
    artifacts["markdown_report"] = str(make_dashboard_markdown_report(records, output_dir / "dashboard_report.md"))

    summary = summarize_records(records)

    # Trend outputs for all known metrics.
    for metric_name in sorted(summary.get("metrics", {}).keys()):
        trend = collect_metric_trend(records, metric_name)
        safe_metric = metric_name.replace("/", "_").replace(" ", "_")
        artifacts[f"trend_{safe_metric}_csv"] = str(export_metric_trend_csv(trend, output_dir / f"trend_{safe_metric}.csv"))
        artifacts[f"trend_{safe_metric}_figure"] = str(plot_metric_trend(trend, output_dir / f"trend_{safe_metric}.png"))

    manifest = {
        "package": "AZM-QOS v2.8 dashboard package",
        "records_count": len(records),
        "summary": summary,
        "artifacts": artifacts,
    }
    manifest_path = output_dir / "dashboard_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, default=str), encoding="utf-8")
    artifacts["manifest"] = str(manifest_path)

    return DashboardPackage(
        output_dir=str(output_dir),
        records_count=len(records),
        artifacts=artifacts,
        summary=summary,
    )
