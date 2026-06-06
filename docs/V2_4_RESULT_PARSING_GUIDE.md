# AZM-QOS v2.4 Result Parsing Guide

The parser supports:

- direct count dictionaries
- dictionaries with `counts`
- dictionaries with `probabilities`
- dictionaries with `quasi_dists`
- objects with `get_counts()`
- simple estimator outputs with `values`, `evs`, `value`, `expectation`, or `mean`

Because IBM Runtime result containers can vary by version, v2.4 keeps parsing defensive and transparent.
