from __future__ import annotations
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any
import csv, hashlib, json, math, time, uuid

from .production import ProductionProjectSpec, ProductionPlan, load_production_spec, make_production_plan
from .production_execution import WorkloadSpec, ExecutionResult, production_plan_to_workloads, export_workloads_csv, export_execution_results_json, export_execution_results_csv
from .experiment_db import ExperimentDatabase, BackendMetadataRecord, new_run_record, artifact_from_path, export_run_table_csv, export_dashboard_json, make_run_database_report
from .dashboard import build_dashboard_package

@dataclass
class CircuitSpec:
    circuit_id: str
    workload_id: str
    component_name: str
    family: str | None
    quantity: str
    n_qubits: int
    rotation_angle: float
    observable: str = 'Z'
    measurement_register: str = 'c'
    description: str = ''
    metadata: dict[str, Any] = field(default_factory=dict)
    def summary(self) -> str:
        return ("CircuitSpec\n"
                f"  circuit_id: {self.circuit_id}\n"
                f"  workload_id: {self.workload_id}\n"
                f"  component_name: {self.component_name}\n"
                f"  n_qubits: {self.n_qubits}\n"
                f"  rotation_angle: {self.rotation_angle:.8f}\n"
                f"  observable: {self.observable}")

@dataclass
class SimulatorExecutionConfig:
    backend: str = 'auto'
    shots: int = 1024
    seed: int | None = 123
    use_qiskit_if_available: bool = True
    exact_reference: bool = True
    def summary(self) -> str:
        return ("SimulatorExecutionConfig\n"
                f"  backend: {self.backend}\n"
                f"  shots: {self.shots}\n"
                f"  seed: {self.seed}\n"
                f"  use_qiskit_if_available: {self.use_qiskit_if_available}\n"
                f"  exact_reference: {self.exact_reference}")

@dataclass
class SimulatorComparisonResult:
    workload_id: str
    component_name: str
    exact_expectation: float
    sampled_expectation: float
    absolute_error: float
    shots: int
    backend_used: str
    counts: dict[str, int]
    metadata: dict[str, Any] = field(default_factory=dict)
    def summary(self) -> str:
        return ("SimulatorComparisonResult\n"
                f"  component_name: {self.component_name}\n"
                f"  exact_expectation: {self.exact_expectation:+.10f}\n"
                f"  sampled_expectation: {self.sampled_expectation:+.10f}\n"
                f"  absolute_error: {self.absolute_error:.8e}\n"
                f"  shots: {self.shots}\n"
                f"  backend_used: {self.backend_used}")

@dataclass
class ShotScalingPoint:
    workload_id: str
    component_name: str
    shots: int
    log2_shots: float
    exact_expectation: float
    sampled_expectation: float
    absolute_error: float
    log2_absolute_error: float
    backend_used: str
    def summary(self) -> str:
        return f"ShotScalingPoint(component={self.component_name}, shots={self.shots}, AE={self.absolute_error:.8e}, log2_AE={self.log2_absolute_error:.6f})"

@dataclass
class ProductionSimulatorBatchResult:
    spec: ProductionProjectSpec
    plan: ProductionPlan
    workloads: list[WorkloadSpec]
    circuit_specs: list[CircuitSpec]
    execution_results: list[ExecutionResult]
    comparisons: list[SimulatorComparisonResult]
    output_dir: str
    artifacts: dict[str, str] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    def summary(self) -> str:
        backend_counts = {}
        for c in self.comparisons:
            backend_counts[c.backend_used] = backend_counts.get(c.backend_used, 0) + 1
        return ("ProductionSimulatorBatchResult\n"
                f"  project: {self.spec.project_name}\n"
                f"  workloads: {len(self.workloads)}\n"
                f"  circuits: {len(self.circuit_specs)}\n"
                f"  comparisons: {len(self.comparisons)}\n"
                f"  backends: {backend_counts}\n"
                f"  artifacts: {len(self.artifacts)}\n"
                f"  warnings: {self.warnings}")

def _stable_unit_interval(text: str) -> float:
    digest = hashlib.sha256(text.encode('utf-8')).hexdigest()
    intval = int(digest[:14], 16)
    return intval / float(16 ** 14 - 1)

def workload_to_rotation_angle(workload: WorkloadSpec) -> float:
    unit = _stable_unit_interval(f"{workload.component_name}|{workload.quantity}|{workload.family}|{workload.indices}|{workload.n_terms}")
    return 0.15 + unit * (math.pi - 0.30)

def workload_to_circuit_spec(workload: WorkloadSpec) -> CircuitSpec:
    theta = workload_to_rotation_angle(workload)
    return CircuitSpec(
        circuit_id=str(uuid.uuid4()), workload_id=workload.workload_id,
        component_name=workload.component_name, family=workload.family,
        quantity=workload.quantity, n_qubits=1, rotation_angle=theta,
        observable='Z', measurement_register='c',
        description='Single-qubit Ry scaffold circuit for simulator integration.',
        metadata={'measurement_type': workload.measurement_type, 'n_terms': workload.n_terms, 'indices': workload.indices},
    )

def circuit_spec_to_qiskit(circuit: CircuitSpec, measure: bool = True):
    try:
        from qiskit import QuantumCircuit
    except Exception as exc:
        raise ImportError('Qiskit is not installed. Install with: python -m pip install qiskit') from exc
    qc = QuantumCircuit(circuit.n_qubits, circuit.n_qubits if measure else 0)
    qc.ry(circuit.rotation_angle, 0)
    if measure:
        qc.measure(0, 0)
    return qc

def exact_expectation_from_circuit_spec(circuit: CircuitSpec) -> float:
    return float(math.cos(circuit.rotation_angle))

def exact_probabilities_from_circuit_spec(circuit: CircuitSpec) -> dict[str, float]:
    p0 = math.cos(circuit.rotation_angle / 2.0) ** 2
    p1 = math.sin(circuit.rotation_angle / 2.0) ** 2
    return {'0': float(p0), '1': float(p1)}

def _deterministic_counts_from_probabilities(probs: dict[str, float], shots: int) -> dict[str, int]:
    raw = {k: float(v) * shots for k, v in probs.items()}
    counts = {k: int(math.floor(v)) for k, v in raw.items()}
    remainder = shots - sum(counts.values())
    order = sorted(raw, key=lambda k: (raw[k] - math.floor(raw[k]), k), reverse=True)
    for k in order[:remainder]:
        counts[k] += 1
    return counts

def expectation_from_binary_counts(counts: dict[str, int]) -> float:
    shots = sum(counts.values())
    if shots <= 0:
        raise ValueError('Counts are empty.')
    if '0' in counts or '1' in counts:
        return (counts.get('0', 0) - counts.get('1', 0)) / shots
    total = 0
    for bitstring, c in counts.items():
        parity = sum(int(ch) for ch in str(bitstring) if ch in '01') % 2
        total += c * (1 if parity == 0 else -1)
    return total / shots

def run_fallback_simulator(circuit: CircuitSpec, shots: int) -> dict[str, int]:
    return _deterministic_counts_from_probabilities(exact_probabilities_from_circuit_spec(circuit), shots=shots)

def run_aer_simulator(circuit: CircuitSpec, shots: int, seed: int | None = 123) -> dict[str, int]:
    qc = circuit_spec_to_qiskit(circuit, measure=True)
    try:
        from qiskit_aer import AerSimulator
        backend = AerSimulator(seed_simulator=seed)
        result = backend.run(qc, shots=shots, seed_simulator=seed).result()
        return {str(k): int(v) for k, v in result.get_counts().items()}
    except Exception:
        try:
            from qiskit.providers.basic_provider import BasicSimulator
            backend = BasicSimulator()
            result = backend.run(qc, shots=shots, seed_simulator=seed).result()
            return {str(k): int(v) for k, v in result.get_counts().items()}
        except Exception as exc:
            raise ImportError('Neither qiskit-aer nor BasicSimulator was available.') from exc

def run_simulator_for_circuit(circuit: CircuitSpec, config: SimulatorExecutionConfig) -> tuple[dict[str, int], str]:
    backend_choice = config.backend.lower()
    if backend_choice == 'fallback':
        return run_fallback_simulator(circuit, config.shots), 'fallback'
    if backend_choice in {'auto', 'aer'} and config.use_qiskit_if_available:
        try:
            return run_aer_simulator(circuit, config.shots, seed=config.seed), 'aer_or_basic'
        except Exception:
            if backend_choice == 'aer':
                raise
    return run_fallback_simulator(circuit, config.shots), 'fallback'

def compare_simulator_to_exact(workload: WorkloadSpec, circuit: CircuitSpec, config: SimulatorExecutionConfig):
    counts, backend_used = run_simulator_for_circuit(circuit, config)
    sampled = expectation_from_binary_counts(counts)
    exact = exact_expectation_from_circuit_spec(circuit)
    ae = abs(sampled - exact)
    execution = ExecutionResult(
        workload_id=workload.workload_id, plan_id=workload.plan_id,
        component_name=workload.component_name, status='completed', estimate=sampled,
        counts=counts, job_id=None, backend_name=backend_used, execution_mode='simulator',
        message='Simulator backend integration result.',
        metadata={'exact_expectation': exact, 'absolute_error': ae, 'circuit_id': circuit.circuit_id, 'rotation_angle': circuit.rotation_angle},
    )
    comparison = SimulatorComparisonResult(
        workload_id=workload.workload_id, component_name=workload.component_name,
        exact_expectation=exact, sampled_expectation=sampled, absolute_error=ae,
        shots=config.shots, backend_used=backend_used, counts=counts,
        metadata={'circuit_id': circuit.circuit_id, 'family': workload.family, 'quantity': workload.quantity},
    )
    return execution, comparison

def export_circuit_specs_json(circuits: list[CircuitSpec], path):
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps([asdict(c) for c in circuits], indent=2, default=str), encoding='utf-8')
    return path

def export_simulator_comparisons_csv(comparisons: list[SimulatorComparisonResult], path):
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['workload_id','component_name','exact_expectation','sampled_expectation','absolute_error','shots','backend_used','counts_json'])
        for c in comparisons:
            writer.writerow([c.workload_id,c.component_name,c.exact_expectation,c.sampled_expectation,c.absolute_error,c.shots,c.backend_used,json.dumps(c.counts)])
    return path

def plot_simulator_comparisons(comparisons: list[SimulatorComparisonResult], path):
    path = Path(path)
    try:
        import matplotlib.pyplot as plt
    except Exception:
        txt = path.with_suffix('.txt')
        txt.write_text('\n'.join(c.summary() for c in comparisons), encoding='utf-8')
        return txt
    labels = [c.component_name for c in comparisons]
    exact = [c.exact_expectation for c in comparisons]
    sampled = [c.sampled_expectation for c in comparisons]
    x = list(range(len(labels)))
    fig = plt.figure()
    ax = fig.add_subplot(111)
    ax.plot(x, exact, marker='o', label='exact')
    ax.plot(x, sampled, marker='s', label='sampled')
    ax.set_xlabel('production workload')
    ax.set_ylabel('expectation')
    ax.set_title('Simulator vs exact expectations')
    if len(labels) <= 10:
        ax.set_xticks(x)
        ax.set_xticklabels(labels, rotation=45, ha='right')
    ax.legend()
    fig.tight_layout()
    fig.savefig(path, dpi=250)
    plt.close(fig)
    return path

def attach_simulator_results_to_database(spec: ProductionProjectSpec, workloads: list[WorkloadSpec], results: list[ExecutionResult], database_path, artifact_paths: dict[str, str] | None = None):
    database_path = Path(database_path)
    db = ExperimentDatabase(database_path)
    artifact_paths = artifact_paths or {}
    result_by_workload = {r.workload_id: r for r in results}
    records = []
    for workload in workloads:
        result = result_by_workload.get(workload.workload_id)
        metrics = {'n_terms': float(workload.n_terms), 'shots': float(workload.shots)}
        if result and result.estimate is not None:
            metrics['sampled_expectation'] = float(result.estimate)
            metrics['exact_expectation'] = float(result.metadata.get('exact_expectation', result.estimate))
            metrics['absolute_error'] = float(result.metadata.get('absolute_error', 0.0))
        if result and result.counts:
            metrics['total_counts'] = float(sum(result.counts.values()))
        artifacts = [artifact_from_path(path, name=name, artifact_type='simulator_artifact') for name, path in artifact_paths.items()]
        record = new_run_record(
            name=f'simulator_{workload.component_name}', run_type='production_simulator',
            status=result.status if result else 'missing_result',
            tags=['production','simulator',workload.family or 'unknown',workload.quantity],
            parameters={'component_name': workload.component_name, 'quantity': workload.quantity, 'indices': workload.indices, 'measurement_type': workload.measurement_type, 'execution_mode':'simulator'},
            metrics=metrics,
            backend=BackendMetadataRecord(backend_name=result.backend_name if result else 'simulator', job_status=result.status if result else 'missing_result', timestamp_unix=time.time()),
            artifacts=artifacts, notes=result.message if result else 'No simulator result attached.',
        )
        db.append(record); records.append(record)
    return db, records

def make_simulator_report(batch: ProductionSimulatorBatchResult, output_path):
    output_path = Path(output_path); output_path.parent.mkdir(parents=True, exist_ok=True)
    lines = ['# AZM-QOS v3.3 Real Simulator Backend Report', '', '## Summary', '', '```text', batch.summary(), '```', '', '## Simulator comparisons', '']
    for comparison in batch.comparisons:
        lines.extend(['```text', comparison.summary(), '```', ''])
    if batch.warnings:
        lines.extend(['## Warnings', ''])
        for warning in batch.warnings: lines.append(f'- {warning}')
        lines.append('')
    lines.extend(['## Artifacts', ''])
    for key, value in batch.artifacts.items(): lines.append(f'- **{key}**: `{value}`')
    lines.extend(['', '## Scientific note', '', 'The default v3.3 circuit is a single-qubit simulator scaffold. Replace workload-to-circuit mapping with actual Pauli-term circuit construction for final END/VQS production studies.', ''])
    output_path.write_text('\n'.join(lines), encoding='utf-8')
    return output_path

def run_production_simulator_batch(spec_or_path, backend: str = 'auto', shots: int | None = None, seed: int | None = 123) -> ProductionSimulatorBatchResult:
    spec = load_production_spec(spec_or_path) if isinstance(spec_or_path, (str, Path)) else spec_or_path
    if shots is not None: spec.execution_policy.shots = int(shots)
    output_dir = Path(spec.output_dir); sim_dir = output_dir/'simulator'; sim_dir.mkdir(parents=True, exist_ok=True)
    plan = make_production_plan(spec)
    workloads = production_plan_to_workloads(plan, spec)
    circuit_specs = [workload_to_circuit_spec(w) for w in workloads]
    config = SimulatorExecutionConfig(backend=backend, shots=spec.execution_policy.shots, seed=seed)
    execution_results, comparisons = [], []
    for workload, circuit in zip(workloads, circuit_specs):
        execution, comparison = compare_simulator_to_exact(workload, circuit, config)
        execution_results.append(execution); comparisons.append(comparison)
    artifacts = {}
    artifacts['workloads_csv'] = str(export_workloads_csv(workloads, sim_dir/'workloads.csv'))
    artifacts['circuit_specs_json'] = str(export_circuit_specs_json(circuit_specs, sim_dir/'circuit_specs.json'))
    artifacts['simulator_results_json'] = str(export_execution_results_json(execution_results, sim_dir/'simulator_results.json'))
    artifacts['simulator_results_csv'] = str(export_execution_results_csv(execution_results, sim_dir/'simulator_results.csv'))
    artifacts['simulator_comparison_csv'] = str(export_simulator_comparisons_csv(comparisons, sim_dir/'simulator_comparison.csv'))
    artifacts['simulator_comparison_figure'] = str(plot_simulator_comparisons(comparisons, sim_dir/'simulator_comparison.png'))
    db, records = attach_simulator_results_to_database(spec, workloads, execution_results, output_dir/'database'/'production_simulator_runs.jsonl', {'simulator_results_json': artifacts['simulator_results_json'], 'simulator_comparison_csv': artifacts['simulator_comparison_csv']})
    artifacts['simulator_database_jsonl'] = str(db.path)
    artifacts['simulator_run_table_csv'] = str(export_run_table_csv(records, output_dir/'database'/'simulator_run_table.csv'))
    artifacts['simulator_dashboard_json'] = str(export_dashboard_json(records, output_dir/'database'/'simulator_dashboard.json'))
    artifacts['simulator_database_report'] = str(make_run_database_report(records, output_dir/'database'/'simulator_database_report.md'))
    dashboard = build_dashboard_package(output_dir/'dashboard_simulator', database_path=db.path)
    artifacts['dashboard_manifest'] = dashboard.artifacts.get('manifest','')
    artifacts['dashboard_html'] = dashboard.artifacts.get('dashboard_html','')
    artifacts['artifact_browser_html'] = dashboard.artifacts.get('artifact_browser_html','')
    batch = ProductionSimulatorBatchResult(spec, plan, workloads, circuit_specs, execution_results, comparisons, str(output_dir), artifacts, list(plan.warnings))
    artifacts['simulator_report'] = str(make_simulator_report(batch, sim_dir/'production_simulator_report.md'))
    manifest_path = sim_dir/'production_simulator_manifest.json'
    manifest_path.write_text(json.dumps({'package':'AZM-QOS v3.3 real simulator backend','summary': batch.summary(),'warnings': batch.warnings,'artifacts': artifacts}, indent=2, default=str), encoding='utf-8')
    artifacts['production_simulator_manifest'] = str(manifest_path)
    return ProductionSimulatorBatchResult(spec, plan, workloads, circuit_specs, execution_results, comparisons, str(output_dir), artifacts, list(plan.warnings))

def run_shot_scaling_for_workload(workload: WorkloadSpec, shot_powers=(6,8,10), backend: str = 'fallback', seed: int | None = 123) -> list[ShotScalingPoint]:
    circuit = workload_to_circuit_spec(workload)
    exact = exact_expectation_from_circuit_spec(circuit)
    points = []
    for p in shot_powers:
        shots = int(2**p)
        config = SimulatorExecutionConfig(backend=backend, shots=shots, seed=None if seed is None else seed+p)
        counts, backend_used = run_simulator_for_circuit(circuit, config)
        sampled = expectation_from_binary_counts(counts)
        ae = abs(sampled - exact)
        points.append(ShotScalingPoint(workload.workload_id, workload.component_name, shots, float(p), exact, sampled, ae, math.log(max(ae,1e-16),2), backend_used))
    return points

def export_shot_scaling_points_csv(points: list[ShotScalingPoint], path):
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f); writer.writerow(['workload_id','component_name','shots','log2_shots','exact_expectation','sampled_expectation','absolute_error','log2_absolute_error','backend_used'])
        for p in points:
            writer.writerow([p.workload_id,p.component_name,p.shots,p.log2_shots,p.exact_expectation,p.sampled_expectation,p.absolute_error,p.log2_absolute_error,p.backend_used])
    return path

def plot_shot_scaling_points(points: list[ShotScalingPoint], path):
    path = Path(path)
    try:
        import matplotlib.pyplot as plt
    except Exception:
        txt = path.with_suffix('.txt'); txt.write_text('\n'.join(p.summary() for p in points), encoding='utf-8'); return txt
    by_component = {}
    for point in points: by_component.setdefault(point.component_name, []).append(point)
    fig = plt.figure(); ax = fig.add_subplot(111)
    for component, pts in by_component.items():
        pts = sorted(pts, key=lambda p: p.log2_shots)
        ax.plot([p.log2_shots for p in pts], [p.log2_absolute_error for p in pts], marker='o', label=component)
    ax.set_xlabel('log2(shots)'); ax.set_ylabel('log2(absolute error)'); ax.set_title('Production simulator shot scaling')
    if len(by_component) <= 8: ax.legend(fontsize=8)
    fig.tight_layout(); fig.savefig(path, dpi=250); plt.close(fig); return path

def run_production_shot_scaling(spec_or_path, shot_powers=(6,8,10), backend: str = 'fallback') -> dict[str, Any]:
    spec = load_production_spec(spec_or_path) if isinstance(spec_or_path, (str, Path)) else spec_or_path
    output_dir = Path(spec.output_dir); scaling_dir = output_dir/'simulator'/'shot_scaling'; scaling_dir.mkdir(parents=True, exist_ok=True)
    plan = make_production_plan(spec); workloads = production_plan_to_workloads(plan, spec)
    all_points = []
    for workload in workloads: all_points.extend(run_shot_scaling_for_workload(workload, shot_powers=shot_powers, backend=backend))
    csv_path = export_shot_scaling_points_csv(all_points, scaling_dir/'production_shot_scaling.csv')
    fig_path = plot_shot_scaling_points(all_points, scaling_dir/'production_shot_scaling.png')
    manifest_path = scaling_dir/'production_shot_scaling_manifest.json'
    manifest_path.write_text(json.dumps({'package':'AZM-QOS v3.3 production shot scaling','points':[asdict(p) for p in all_points],'artifacts':{'csv':str(csv_path),'figure':str(fig_path)}}, indent=2, default=str), encoding='utf-8')
    return {'points': all_points, 'csv': str(csv_path), 'figure': str(fig_path), 'manifest': str(manifest_path)}
