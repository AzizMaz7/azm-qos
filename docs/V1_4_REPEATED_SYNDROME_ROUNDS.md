# AZM-QOS v1.4 Repeated Syndrome Rounds

v1.4 adds repeated syndrome measurement scaffolds.

## New file

```text
azmqos_qec/rounds.py
```

## Main objects

```text
SyndromeRoundRecord
RepeatedSyndromeResult
```

## Main functions

```text
run_repeated_syndrome_rounds
majority_vote_syndrome
repeated_syndrome_to_syndrome_result
```

## What it models

- repeated stabilizer measurements
- optional measurement-bit flips
- majority aggregation over rounds

## What it does not yet model

- time-correlated data-qubit errors
- real circuit-level noise
- repeated syndrome extraction circuits
- leakage
- connectivity constraints
- decoder graph construction
