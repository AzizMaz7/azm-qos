# AZM-QOS v2.8 Dashboard Guide

Build a dashboard from a database:

```python
from azmqos_research import build_dashboard_package

package = build_dashboard_package(
    output_dir="outputs/dashboard",
    database_path="outputs/runs.jsonl",
)
```

Or build a demo dashboard:

```python
package = build_dashboard_package("outputs/dashboard_demo")
```

Open:

```text
dashboard.html
artifact_browser.html
```

in your browser.
