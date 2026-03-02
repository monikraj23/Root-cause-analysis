import pandas as pd
import random
from datetime import datetime, timedelta

rows = []
start = datetime(2025, 1, 1)

for i in range(400):
    rows.append({
        "timestamp": start + timedelta(seconds=i*30),
        "cpu_usage": random.randint(20, 60),
        "memory_usage": random.randint(30, 70),
        "disk_io": random.randint(100, 300),
        "network_latency": random.randint(10, 40),
        "error_rate": random.uniform(0, 1),
        "request_rate": random.randint(200, 500),
    })

# inject anomalies
rows[120]["cpu_usage"] = 95
rows[121]["memory_usage"] = 98
rows[300]["network_latency"] = 250
rows[301]["error_rate"] = 8
rows[350]["request_rate"] = 3000

df = pd.DataFrame(rows)
df.to_csv("data/cloud_metrics.csv", index=False)

print("Large cloud dataset created ✅")