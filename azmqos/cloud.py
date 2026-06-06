from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any
import time
import uuid

@dataclass
class CloudJobStatus:
    job_id: str
    backend_name: str
    provider: str
    status: str
    message: str = ""
    created_at_unix: float = field(default_factory=time.time)
    updated_at_unix: float = field(default_factory=time.time)
    metadata: dict[str, Any] = field(default_factory=dict)

    def update(self, status: str, message: str = "", **metadata):
        self.status = status
        self.message = message
        self.updated_at_unix = time.time()
        self.metadata.update(metadata)

    def summary(self):
        return (
            f"CloudJobStatus(job_id={self.job_id}, provider={self.provider}, "
            f"backend={self.backend_name}, status={self.status}, message={self.message})"
        )

def make_local_cloud_status(backend_name: str, status: str = "not_submitted", message: str = ""):
    return CloudJobStatus(
        job_id=str(uuid.uuid4()),
        backend_name=backend_name,
        provider="local_or_scaffold",
        status=status,
        message=message,
    )
