import pandas as pd
import time


def stream_data(file_path, delay=1):
    """
    Simulates a live data stream by reading a CSV file line by line.
    NOTE: MongoDB insertion is handled by the caller (dashboard/orchestrator).
    """
    try:
        df = pd.read_csv(file_path)
        for _, row in df.iterrows():
            yield row.to_dict()
            if delay > 0:
                time.sleep(delay)
    except FileNotFoundError:
        print(f"Error: Dataset file {file_path} not found.")


if __name__ == "__main__":
    from db import insert_log_event
    print("📡 Stream simulator started — writing metrics to MongoDB...")
    while True:
        for row in stream_data("data/cloud_metrics_large.csv", delay=2):
            if row:
                insert_log_event(source="simulated_metrics", payload=row)
                print(f"✅ Logged: cpu={row.get('cpu_usage')} | error_rate={row.get('error_rate')} | latency={row.get('network_latency')}")
        print("🔄 Restarting stream...")