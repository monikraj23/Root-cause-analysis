def evaluate_system(exec_time_seconds, total_anomalies, explained_anomalies):
    manual_time_minutes = 30

    return {
        "anomalies_explained": f"{explained_anomalies}/{total_anomalies}",
        "time_taken_seconds": round(exec_time_seconds, 2),
        "estimated_manual_time_minutes": manual_time_minutes,
        "time_reduction_percent": round(
            (1 - (exec_time_seconds / (manual_time_minutes * 60))) * 100, 2
        )
    }
