from fastapi import FastAPI
import random
import time

app = FastAPI()


# ==============================
# HEALTH CHECK ENDPOINT
# ==============================
@app.get("/")
def home():
    return {"message": "🚀 API Monitor Running"}


# ==============================
# METRICS ENDPOINT
# ==============================
@app.get("/metrics")
def get_metrics():
    """
    Simulated API metrics with occasional anomalies
    """

    # Normal values
    latency = random.randint(20, 300)
    error_rate = random.choice([0, 0, 0, 1])  # mostly no errors
    request_rate = random.randint(50, 500)

    # ==============================
    # SIMULATE ANOMALIES (IMPORTANT)
    # ==============================
    if random.random() < 0.1:  # 10% chance
        latency = random.randint(500, 1500)       # high latency spike
        error_rate = random.randint(1, 5)         # increased errors
        request_rate = random.randint(800, 2000)  # traffic spike

    return {
        "timestamp": time.time(),
        "latency": latency,
        "error_rate": error_rate,
        "request_rate": request_rate
    }