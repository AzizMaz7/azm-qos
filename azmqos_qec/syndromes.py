from __future__ import annotations
from dataclasses import dataclass
from typing import Any

@dataclass
class SyndromeResult:
    code_name: str
    stabilizer_values: dict[str, float]
    syndrome_bits: dict[str, int]
    metadata: dict[str, Any]

    def summary(self):
        lines = [f"SyndromeResult(code={self.code_name})"]
        for name, bit in self.syndrome_bits.items():
            value = self.stabilizer_values[name]
            lines.append(f"  {name}: value={value:+.6f}, syndrome_bit={bit}")
        return "\n".join(lines)

def infer_syndrome_from_stabilizers(results, threshold: float = 0.0):
    """Infer syndrome bits from stabilizer JobResult objects.

    Convention:
    stabilizer expectation >= threshold -> syndrome 0
    stabilizer expectation < threshold  -> syndrome 1
    """
    values = {}
    bits = {}
    code_name = "unknown"
    for result in results:
        if not result.workload_name.startswith("qec_stabilizer_"):
            continue
        if result.term_estimates:
            term_name, value = next(iter(result.term_estimates.items()))
            values[term_name] = float(value)
            bits[term_name] = 0 if value >= threshold else 1
        code_name = result.metadata.get("code", code_name) if hasattr(result, "metadata") else code_name

    return SyndromeResult(
        code_name=code_name,
        stabilizer_values=values,
        syndrome_bits=bits,
        metadata={"threshold": threshold},
    )

def syndrome_summary(syndrome: SyndromeResult):
    return syndrome.summary()
