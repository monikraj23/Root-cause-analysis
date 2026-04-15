from sklearn.ensemble import IsolationForest
import pandas as pd

FEATURE_COLUMNS = [
    "cpu_usage", "memory_usage", "disk_io", 
    "network_latency", "error_rate", "request_rate"
]

MAX_HISTORY = 500

class CloudAnomalyDetector:
    def __init__(self):
        self.history = []
        self.model = IsolationForest(contamination=0.15, random_state=42)
        self.trained = False
        self.counter = 0

    def detect(self, row):
        """
        Detect anomaly with a hybrid of ML and Hard Thresholds.
        """
        latency = row.get("network_latency") or row.get("latency", 0)
        error_rate = row.get("error_rate", 0)
        cpu = row.get("cpu_usage", 0)

        # 1. HARD THRESHOLD GATE — fixed thresholds (latency in ms, not decimal)
        if error_rate > 0.05 or latency > 150 or cpu > 85:
            return True, row

        # 2. ML PREPARATION
        df_row = (
            pd.DataFrame([row])
            .reindex(columns=FEATURE_COLUMNS, fill_value=0)
            .fillna(0)
        )

        self.history.append(df_row.iloc[0].to_dict())

        if len(self.history) > MAX_HISTORY:
            self.history.pop(0)

        # 3. MACHINE LEARNING GATE
        if len(self.history) < 10:
            return False, None

        history_df = pd.DataFrame(self.history)

        if not self.trained:
            self.model.fit(history_df)
            self.trained = True

        self.counter += 1
        if self.counter % 50 == 0:
            self.model.fit(history_df)

        pred = self.model.predict(df_row)[0]

        if pred == -1:
            return True, df_row.iloc[0].to_dict()

        return False, Nonee