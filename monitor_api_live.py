import time
import requests

# REMOVED: from api_monitor import collect_metrics
# REMOVED: from api_anomaly_detector import APIAnomalyDetector

# =========================================================
# 1. INTERNAL API GENERATOR (Direct Monitoring)
# =========================================================
def stream_api_data(url="http://127.0.0.1:8000/"):
    """
    Generator for your custom local API monitoring.
    Replaces the deleted api_monitor.py logic.
    """
    while True:
        start_time = time.time()
        try:
            # Direct metric collection without external files
            response = requests.get(url, timeout=3)
            latency = time.time() - start_time
            status = response.json().get("status", "ok")
            error = 1 if (status != "ok" or response.status_code != 200) else 0

            metrics = {
                "timestamp": time.time(),
                "latency": latency,
                "error_rate": error,
                "request_rate": 1,
                "cpu_usage": 0, # Placeholder for UI compatibility
                "memory_usage": 0
            }

            yield metrics
        except Exception as e:
            # Graceful failure if the local API isn't running
            yield {
                "timestamp": time.time(),
                "error_rate": 1, 
                "latency": 5.0, 
                "request_rate": 0,
                "status": f"Offline: {str(e)[:20]}"
            }
        
        time.sleep(1)

# =========================================================
# 2. PUBLIC API GENERATOR (Bitcoin Live Data)
# =========================================================
def stream_public_api():
    """
    Generator for real-world Public API data (Bitcoin).
    Provides live traffic for your dashboard.
    """
    url = "https://api.coinbase.com/v2/prices/BTC-USD/spot"
    while True:
        start_time = time.time()
        try:
            response = requests.get(url, timeout=5)
            latency = time.time() - start_time
            data = response.json().get('data', {})
            
            metrics = {
                "timestamp": time.time(),
                "price": float(data.get('amount', 0)),
                "latency": latency,
                "error_rate": 0 if response.status_code == 200 else 1,
                "request_rate": 1
            }
            yield metrics
        except Exception as e:
            yield {
                "timestamp": time.time(),
                "error_rate": 1, 
                "latency": 1.0, 
                "request_rate": 0, 
                "status": "API Offline"
            }
        
        # Public APIs usually have rate limits
        time.sleep(3)