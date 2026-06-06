from __future__ import annotations

from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any
import json
import time


@dataclass
class ComponentPluginRecord:
    name: str
    plugin_type: str
    description: str = ""
    entry_point: str | None = None
    version: str = "0.1.0"
    enabled: bool = True
    tags: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def summary(self) -> str:
        return (
            f"ComponentPluginRecord(name={self.name}, type={self.plugin_type}, "
            f"version={self.version}, enabled={self.enabled})"
        )


@dataclass
class PluginRegistry:
    plugins: list[ComponentPluginRecord] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def summary(self) -> str:
        enabled = sum(1 for p in self.plugins if p.enabled)
        return f"PluginRegistry(plugins={len(self.plugins)}, enabled={enabled})"

    def to_dict(self):
        return asdict(self)

    def by_type(self, plugin_type: str) -> list[ComponentPluginRecord]:
        return [p for p in self.plugins if p.plugin_type == plugin_type]

    def enabled_plugins(self) -> list[ComponentPluginRecord]:
        return [p for p in self.plugins if p.enabled]

    def add(self, plugin: ComponentPluginRecord):
        self.plugins.append(plugin)
        return plugin


def default_plugin_registry():
    registry = PluginRegistry(metadata={"created_at_unix": time.time(), "source": "default_plugin_registry"})
    registry.add(ComponentPluginRecord(
        name="endvqs_component_registry",
        plugin_type="endvqs_terms",
        description="END/VQS M and V Pauli-term component registry loader.",
        entry_point="azmqos_research.real_terms:load_registry_for_research",
        tags=["END", "VQS", "M", "V"],
    ))
    registry.add(ComponentPluginRecord(
        name="ibm_runtime_sampler",
        plugin_type="hardware_runtime",
        description="IBM Runtime SamplerV2 dry-run/submission helper.",
        entry_point="azmqos_research.ibm_runtime:run_sampler_v2_job",
        tags=["IBM", "SamplerV2", "hardware"],
    ))
    registry.add(ComponentPluginRecord(
        name="hardware_compare",
        plugin_type="analysis",
        description="Hardware-vs-simulator comparison module.",
        entry_point="azmqos_research.hardware_compare:compare_counts",
        tags=["analysis", "counts", "TVD"],
    ))
    registry.add(ComponentPluginRecord(
        name="mitigation",
        plugin_type="analysis",
        description="Readout mitigation and ZNE scaffold.",
        entry_point="azmqos_research.calibration_mitigation:run_mock_mitigation_workflow",
        tags=["mitigation", "readout", "ZNE"],
    ))
    registry.add(ComponentPluginRecord(
        name="dashboard",
        plugin_type="reporting",
        description="Dashboard and multi-run export module.",
        entry_point="azmqos_research.dashboard:build_dashboard_package",
        tags=["dashboard", "HTML", "reports"],
    ))
    return registry


def save_plugin_registry(registry: PluginRegistry, path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(registry.to_dict(), indent=2, default=str), encoding="utf-8")
    return path


def load_plugin_registry(path):
    path = Path(path)
    data = json.loads(path.read_text(encoding="utf-8"))
    plugins = [ComponentPluginRecord(**p) for p in data.get("plugins", [])]
    return PluginRegistry(plugins=plugins, metadata=dict(data.get("metadata", {})))


def make_plugin_registry_report(registry: PluginRegistry, output_path):
    output_path = Path(output_path)
    lines = [
        "# AZM-QOS v3.0 Plugin Registry Report",
        "",
        "## Summary",
        "",
        "```text",
        registry.summary(),
        "```",
        "",
        "## Plugins",
        "",
    ]
    for plugin in registry.plugins:
        lines.extend(["```text", plugin.summary(), "```", ""])
        lines.append(f"- Description: {plugin.description}")
        lines.append(f"- Entry point: `{plugin.entry_point}`")
        lines.append(f"- Tags: {', '.join(plugin.tags)}")
        lines.append("")
    output_path.write_text("\n".join(lines), encoding="utf-8")
    return output_path
