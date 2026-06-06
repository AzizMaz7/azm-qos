"""
IBM Runtime result helpers for AZM-QOS.

This module does NOT submit jobs. It only retrieves existing IBM Runtime jobs
and extracts Sampler/SamplerV2 counts.

Backend handling:
    backend_name="ibm_fez"   -> latest job from ibm_fez only
    backend_name="ibm_brisbane" -> latest job from ibm_brisbane only
    backend_name=None        -> latest visible job from ANY backend

Typical use:
    from azmqos_research import get_latest_ibm_job_id, retrieve_ibm_hardware_result

    # Latest job from any backend:
    result = retrieve_ibm_hardware_result()

    # Latest job from a specific backend:
    result = retrieve_ibm_hardware_result(backend_name="ibm_fez")
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any
import json


@dataclass
class IBMHardwareResult:
    """Container for a retrieved IBM Runtime result."""

    job_id: str
    backend_name: str | None
    status: str
    counts: dict[str, int] | None
    result: Any | None = None

    def summary(self) -> str:
        return (
            "IBMHardwareResult\n"
            f"  job_id: {self.job_id}\n"
            f"  backend_name: {self.backend_name}\n"
            f"  status: {self.status}\n"
            f"  counts: {self.counts}"
        )


def make_service():
    """Create a QiskitRuntimeService instance."""
    from qiskit_ibm_runtime import QiskitRuntimeService

    return QiskitRuntimeService()


def get_latest_ibm_job_id(
    backend_name: str | None = None,
    service=None,
    pending: bool | None = None,
) -> str:
    """Return the most recent IBM Runtime job ID.

    Parameters
    ----------
    backend_name:
        If provided, search only jobs from this backend.
        If None, search the latest visible job from ANY backend.
    service:
        Optional existing QiskitRuntimeService.
    pending:
        Optional IBM filter. Use None for all jobs, True for pending jobs,
        or False for completed/cancelled/error jobs.
    """
    service = service or make_service()

    kwargs = {
        "limit": 1,
        "descending": True,
    }
    if backend_name is not None:
        kwargs["backend_name"] = backend_name
    if pending is not None:
        kwargs["pending"] = pending

    jobs = service.jobs(**kwargs)
    if not jobs:
        backend_msg = f" for backend {backend_name!r}" if backend_name else ""
        raise RuntimeError(f"No IBM Runtime jobs found{backend_msg}.")

    return jobs[0].job_id()


def get_latest_job(
    backend_name: str | None = None,
    service=None,
    pending: bool | None = None,
):
    """Return the most recent IBM Runtime job object.

    If backend_name=None, this returns the latest visible job from any backend.
    """
    service = service or make_service()
    job_id = get_latest_ibm_job_id(
        backend_name=backend_name,
        service=service,
        pending=pending,
    )
    return service.job(job_id)


def get_job(job_id: str | None = None, backend_name: str | None = None, service=None):
    """Return an IBM Runtime job object.

    If job_id is None, the latest job is selected automatically.
    If backend_name is None, the latest job from any backend is selected.
    """
    service = service or make_service()
    if job_id is None:
        job_id = get_latest_ibm_job_id(backend_name=backend_name, service=service)
    return service.job(job_id)


def get_backend_name_from_job(job) -> str | None:
    """Best-effort extraction of backend name from an IBM Runtime job."""
    for attr in ["backend", "backend_name"]:
        try:
            value = getattr(job, attr)
            value = value() if callable(value) else value
            if isinstance(value, str):
                return value
            if value is not None and hasattr(value, "name"):
                name = getattr(value, "name")
                return name() if callable(name) else name
        except Exception:
            pass

    try:
        return job.inputs.get("backend_name")
    except Exception:
        pass

    return None


def extract_sampler_counts(result, preferred_registers=("meas", "c")) -> dict[str, int] | None:
    """Extract counts from SamplerV2 / Runtime results as robustly as possible.

    Handles common cases:
    - result[0].data.meas.get_counts()
    - result[0].data.c.get_counts()
    - result[0].data["c"].get_counts()
    - result.get_counts()
    - direct dict-like count payloads
    """
    if result is None:
        return None

    # Older result-like object with get_counts().
    if hasattr(result, "get_counts"):
        counts = result.get_counts()
        if isinstance(counts, list) and counts:
            counts = counts[0]
        return {str(k): int(v) for k, v in dict(counts).items()}

    # Direct dict of counts.
    if isinstance(result, dict):
        if all(isinstance(v, (int, float)) for v in result.values()):
            return {str(k): int(round(v)) for k, v in result.items()}
        if "counts" in result and isinstance(result["counts"], dict):
            return {str(k): int(v) for k, v in result["counts"].items()}

    # PrimitiveResult-like object: result[0].data.<register>.get_counts().
    try:
        pub_result = result[0]
        data = pub_result.data
    except Exception:
        data = None

    if data is not None:
        for reg_name in preferred_registers:
            # Attribute access: data.meas or data.c
            if hasattr(data, reg_name):
                reg = getattr(data, reg_name)
                if hasattr(reg, "get_counts"):
                    return {str(k): int(v) for k, v in reg.get_counts().items()}

            # Dict-like access: data["meas"] or data["c"]
            try:
                reg = data[reg_name]
                if hasattr(reg, "get_counts"):
                    return {str(k): int(v) for k, v in reg.get_counts().items()}
            except Exception:
                pass

        available = [name for name in dir(data) if not name.startswith("_")]
        print("Could not find a count register. Available data fields:")
        print(available)

    return None


def retrieve_ibm_hardware_result(
    job_id: str | None = None,
    backend_name: str | None = None,
    service=None,
) -> IBMHardwareResult:
    """Retrieve a job result and extract hardware counts.

    Parameters
    ----------
    job_id:
        Exact IBM Runtime job ID. If provided, backend_name is only metadata/filter context.
    backend_name:
        If job_id is None:
            - backend_name=None means latest visible job from ANY backend.
            - backend_name="ibm_fez" means latest visible job from ibm_fez.
    """
    service = service or make_service()

    if job_id is None:
        job = get_latest_job(backend_name=backend_name, service=service)
        job_id = job.job_id()
    else:
        job = service.job(job_id)

    actual_backend_name = get_backend_name_from_job(job) or backend_name
    status = str(job.status())

    result = job.result()
    counts = extract_sampler_counts(result)

    return IBMHardwareResult(
        job_id=job_id,
        backend_name=actual_backend_name,
        status=status,
        counts=counts,
        result=result,
    )


def get_latest_hardware_counts(backend_name: str | None = None) -> dict[str, int] | None:
    """Get counts from the latest visible job.

    backend_name=None means latest visible job from any backend.
    """
    retrieved = retrieve_ibm_hardware_result(job_id=None, backend_name=backend_name)
    return retrieved.counts


def save_counts_json(counts: dict[str, int] | None, path) -> Path:
    """Save counts to JSON."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(counts or {}, indent=2), encoding="utf-8")
    return path


def plot_counts(counts: dict[str, int] | None):
    """Plot counts with Qiskit's histogram tool."""
    if not counts:
        raise ValueError("No counts available to plot.")

    from qiskit.visualization import plot_histogram

    return plot_histogram(counts)


def plot_latest_hardware_counts(backend_name: str | None = None):
    """Retrieve and plot counts from the latest visible job."""
    counts = get_latest_hardware_counts(backend_name=backend_name)
    return plot_counts(counts)


def main():
    """Run directly as a script."""
    # None = latest visible job from any backend.
    # Change to "ibm_fez" or "ibm_brisbane" if you want a specific backend.
    backend_name = None

    retrieved = retrieve_ibm_hardware_result(backend_name=backend_name)
    print(retrieved.summary())

    if retrieved.counts:
        save_counts_json(retrieved.counts, "hardware_counts_latest.json")
        print("Saved counts to hardware_counts_latest.json")

        try:
            plot_counts(retrieved.counts)
        except Exception as exc:
            print("Plot skipped:", exc)


if __name__ == "__main__":
    main()
