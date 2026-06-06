from __future__ import annotations
from dataclasses import dataclass
from azmqos import QuantumWorkload
from .stabilizers import StabilizerCodeSpec, repetition_code_3
from .logicals import LogicalObservableSpec, default_logical_observables

@dataclass
class QECWorkloadSet:
    code: StabilizerCodeSpec
    stabilizer_workloads: list[QuantumWorkload]
    logical_workloads: list[QuantumWorkload]

    @property
    def all_workloads(self):
        return self.stabilizer_workloads + self.logical_workloads

def build_stabilizer_workloads(code: StabilizerCodeSpec | None = None):
    code = code or repetition_code_3()
    workloads = []
    for stabilizer in code.stabilizers:
        workload = QuantumWorkload(
            n_qubits=code.n_physical_qubits,
            observables=[stabilizer],
            state_preparation=code.state_preparation,
            parameters={},
            name=f"qec_stabilizer_{stabilizer.name}",
            domain="qec",
            description=f"QEC stabilizer workload for {stabilizer.name}.",
            tags=["qec", "stabilizer", "plugin"],
            metadata={"plugin": "azmqos_qec", "code": code.name, "quantity": "stabilizer"},
        )
        workloads.append(workload)
    return workloads

def build_logical_observable_workloads(code: StabilizerCodeSpec | None = None, logicals: LogicalObservableSpec | None = None):
    code = code or repetition_code_3()
    logicals = logicals or default_logical_observables(code.name)
    workloads = []
    for logical in logicals.logicals:
        workload = QuantumWorkload(
            n_qubits=code.n_physical_qubits,
            observables=[logical],
            state_preparation=code.state_preparation,
            parameters={},
            name=f"qec_logical_{logical.name}",
            domain="qec",
            description=f"QEC logical observable workload for {logical.name}.",
            tags=["qec", "logical", "plugin"],
            metadata={"plugin": "azmqos_qec", "code": code.name, "quantity": "logical"},
        )
        workloads.append(workload)
    return workloads

def build_all_qec_workloads(code: StabilizerCodeSpec | None = None, logicals: LogicalObservableSpec | None = None):
    code = code or repetition_code_3()
    return QECWorkloadSet(
        code=code,
        stabilizer_workloads=build_stabilizer_workloads(code),
        logical_workloads=build_logical_observable_workloads(code, logicals),
    )
