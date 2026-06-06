from pathlib import Path
import csv, json

def export_result_json(result, path):
    path = Path(path)
    path.write_text(json.dumps(result.to_dict(), indent=2), encoding="utf-8")
    return path

def export_result_csv(result, path):
    path = Path(path)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["field", "value"])
        writer.writerow(["job_id", result.job_id])
        writer.writerow(["status", result.status])
        writer.writerow(["workload_name", result.workload_name])
        writer.writerow(["domain", result.domain])
        writer.writerow(["backend_name", result.backend_name])
        writer.writerow(["backend_type", result.backend_type])
        writer.writerow(["shots", result.shots])
        writer.writerow(["repeats", result.repeats])
        writer.writerow(["exact_total_real", "" if result.exact_total is None else result.exact_total.real])
        writer.writerow(["estimate_mean_real", result.estimate_mean.real])
        writer.writerow(["estimate_std", result.estimate_std])
        writer.writerow(["mean_absolute_error", result.mean_absolute_error])
        writer.writerow([])
        writer.writerow(["term", "estimate"])
        for term, value in result.term_estimates.items():
            writer.writerow([term, value])
    return path
