from __future__ import annotations
from dataclasses import dataclass, field
from abc import ABC, abstractmethod
from typing import Any

@dataclass
class PluginInfo:
    name: str
    version: str
    domain: str
    description: str
    author: str | None = None
    tags: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

class AZMQOSPlugin(ABC):
    """Base class for AZM-QOS plugins.

    A plugin should convert a domain-specific problem into one or more
    QuantumWorkload objects that the AZM-QOS core can execute.
    """

    @abstractmethod
    def info(self) -> PluginInfo:
        raise NotImplementedError

    @abstractmethod
    def create_workloads(self, **kwargs):
        """Return one QuantumWorkload or a list of QuantumWorkload objects."""
        raise NotImplementedError

    def validate(self) -> bool:
        return True

class PluginRegistry:
    """Simple in-memory plugin registry."""

    def __init__(self):
        self._plugins: dict[str, AZMQOSPlugin] = {}

    def register(self, plugin: AZMQOSPlugin):
        info = plugin.info()
        if info.name in self._plugins:
            raise ValueError(f"Plugin {info.name!r} is already registered.")
        self._plugins[info.name] = plugin

    def unregister(self, name: str):
        if name in self._plugins:
            del self._plugins[name]

    def get(self, name: str) -> AZMQOSPlugin:
        if name not in self._plugins:
            available = ", ".join(self._plugins) or "none"
            raise KeyError(f"Plugin {name!r} not found. Available plugins: {available}")
        return self._plugins[name]

    def list_plugins(self) -> dict[str, PluginInfo]:
        return {name: plugin.info() for name, plugin in self._plugins.items()}

    def create_workloads(self, plugin_name: str, **kwargs):
        plugin = self.get(plugin_name)
        return plugin.create_workloads(**kwargs)

def default_plugin_registry() -> PluginRegistry:
    """Create a registry with the built-in template plugins."""
    from .plugin_templates import VQSPlugin, ENDVQSPlugin, QECPlugin

    registry = PluginRegistry()
    registry.register(VQSPlugin())
    registry.register(ENDVQSPlugin())
    registry.register(QECPlugin())
    try:
        from azmqos_endvqs import ENDVQSWorkloadPlugin
        registry.register(ENDVQSWorkloadPlugin())
    except Exception:
        pass
    try:
        from azmqos_qec import QECWorkloadPlugin
        registry.register(QECWorkloadPlugin())
    except Exception:
        pass
    return registry
