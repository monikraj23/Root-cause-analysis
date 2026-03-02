from fastapi import FastAPI
import random
import time
import uvicorn

app = FastAPI()


@app.get("/metrics")
def get_metrics():
    """
    Simulated API metrics
    """

    return {
        "timestamp": time.time(),
        "latency": random.randint(20, 300),
        "error_rate": random.choice([0, 0, 0, 1]),  # occasional errors
        "request_rate": random.randint(50, 500)
    }


# ✅ THIS STARTS THE SERVER
if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)