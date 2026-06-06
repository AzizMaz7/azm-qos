from __future__ import annotations
from azmqos import AZMQOSPlugin, PluginInfo
from .builders import build_all_endvqs_workloads, ENDVQSParameterPoint
from .terms import default_endvqs_registry

class ENDVQSWorkloadPlugin(AZMQOSPlugin):
    """END/VQS plugin compatible with AZM-QOS PluginRegistry."""

    def info(self):
        return PluginInfo(
            name="azmqos-endvqs-v08",
            version="0.8.0",
            domain="endvqs",
            description="Structured END/VQS plugin with M-matrix and V-vector workload builders.",
            author="Abdul Aziz Maaz",
            tags=["endvqs", "M-matrix", "V-vector", "plugin"],
            metadata={
                "status": "proxy_terms_ready_for_replacement",
                "package": "azmqos_endvqs",
            },
        )

    def create_workloads(self, theta0=0.4, theta1=0.7, label="plugin_parameter_point", **kwargs):
        registry = kwargs.get("registry", default_endvqs_registry())
        parameter_point = ENDVQSParameterPoint(theta0=theta0, theta1=theta1, label=label)
        return build_all_endvqs_workloads(registry=registry, parameter_point=parameter_point)
