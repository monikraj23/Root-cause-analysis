import time          
import pandas as pd
import traceback
import functools

from rca_agent import root_cause_analysis
from anomaly_detection import CloudAnomalyDetector

detector = CloudAnomalyDetector()

@functools.lru_cache(maxsize=32)
def get_cached_rca(metrics_tuple):
    """Fetches diagnostic reasoning from the RCA Agent."""
    metrics = dict(metrics_tuple)
    return root_cause_analysis(metrics, baseline=None)

def run_orchestrator(row=None):
    """
    Coordinates detection and AI reasoning.
    """
    start = time.time()

    if row is not None:
        try:
            if isinstance(row, pd.Series):
                row = row.to_dict()

            # 1. Detection Phase
            is_anomaly, metrics = detector.detect(row)
            if not is_anomaly or metrics is None:
                return None

            print(f"🚨 Incident Detected at {row.get('timestamp')}. Invoking Groq Cloud...")
            
            # Ensure timestamp is passed to the report
            metrics.setdefault("timestamp", row.get("timestamp"))
            metrics_frozen = tuple(sorted(metrics.items()))

            # 2. Reasoning Phase (Now targeting Groq)
            try:
                rca = get_cached_rca(metrics_frozen) or {}
            except Exception as e:
                print(f"RCA Agent Error: {e}")
                rca = {}

            # 3. Report Generation (Syncing keys for dashboard.py)
            report = {
                "timestamp": metrics.get("timestamp"),
                "root_cause": rca.get("root_cause", "Anomaly Detected"),
                "severity": rca.get("severity", "Medium"),
                "trust_score": rca.get("trust_score", 0),      
                "actions": rca.get("actions", ["Review system logs"]),             
                "ai_hypotheses": rca.get("ai_hypotheses", "Analysis unavailable")
            }
            
            # CRITICAL DEBUG: Check this output in your terminal
            print(f"🤖 AI HYPOTHESIS: {report['ai_hypotheses'][:60]}...")
            print(f"✅ Analysis Complete in {round(time.time() - start, 2)}s")
            
            return report

        except Exception:
            traceback.print_exc()
            return None

    # BATCH MODE (Historical Analysis)
    try:
        df = pd.read_csv("data/cloud_metrics_large.csv") 
        reports = []
        for _, row_data in df.tail(19).iterrows(): 
            res = run_orchestrator(row_data)
            if res:
                reports.append(res)

        return df, reports, round(time.time() - start, 2)
    except Exception as e:
        print(f"Batch Error: {e}")
        return None, [], 0