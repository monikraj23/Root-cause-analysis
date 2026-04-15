import os
import certifi
from pymongo import MongoClient
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI")
MONGO_DB = os.getenv("MONGO_DB", "project_agent")

client = MongoClient(MONGO_URI, tlsCAFile=certifi.where())
db = client[MONGO_DB]

log_events = db["log_events"]
rca_results = db["rca_results"]


def insert_log_event(source: str, payload: dict):
    """Insert a raw log/metric event into MongoDB."""
    try:
        doc = {
            "source": source,
            "timestamp": datetime.utcnow(),
            "payload": payload
        }
        log_events.insert_one(doc)
    except Exception as e:
        print(f"[MongoDB] Failed to insert log event: {e}")


def insert_rca_result(report: dict):
    """Insert an RCA result into MongoDB."""
    try:
        doc = {
            "timestamp": datetime.utcnow(),
            "root_cause": report.get("root_cause"),
            "severity": report.get("severity"),
            "trust_score": report.get("trust_score"),
            "actions": report.get("actions"),
            "ai_hypotheses": report.get("ai_hypotheses"),
            "predicted_ttf": report.get("predicted_ttf"),
            "remediation_script": report.get("remediation_script"),
            "metrics": report.get("impacts", {})
        }
        rca_results.insert_one(doc)
    except Exception as e:
        print(f"[MongoDB] Failed to insert RCA result: {e}")


def get_recent_rca_results(limit: int = 20):
    """Fetch the most recent RCA results for the dashboard."""
    try:
        results = list(
            rca_results.find({}, {"_id": 0})
            .sort("timestamp", -1)
            .limit(limit)
        )
        return results
    except Exception as e:
        print(f"[MongoDB] Failed to fetch RCA results: {e}")
        return []


def get_recent_log_events(source: str = None, limit: int = 50):
    """Fetch recent log events, optionally filtered by source."""
    try:
        query = {"source": source} if source else {}
        results = list(
            log_events.find(query, {"_id": 0})
            .sort("timestamp", -1)
            .limit(limit)
        )
        return results
    except Exception as e:
        print(f"[MongoDB] Failed to fetch log events: {e}")
        return []