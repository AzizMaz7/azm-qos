from __future__ import annotations
from azmqos import AZMQOSPlugin, PluginInfo
from .stabilizers import repetition_code_3, bell_stabilizer_code, ghz_stabilizer_code
from .builders import build_all_qec_workloads

class QECWorkloadPlugin(AZMQOSPlugin):
    """QEC plugin compatible with AZM-QOS PluginRegistry."""

    def info(self):
        return PluginInfo(
            name="azmqos-qec-v09",
            version="0.9.0",
            domain="qec",
            description="Structured QEC plugin with stabilizer, logical, syndrome, decoder, and resource-estimation tools.",
            author="Abdul Aziz Maaz",
            tags=["qec", "stabilizer", "logical", "decoder", "plugin"],
            metadata={"package": "azmqos_qec", "status": "template_ready"},
        )

    def create_workloads(self, code: str = "repetition3", **kwargs):
        if code == "bell":
            spec = bell_stabilizer_code()
        elif code == "ghz":
            spec = ghz_stabilizer_code()
        else:
            spec = repetition_code_3()
        return build_all_qec_workloads(spec).all_workloads
