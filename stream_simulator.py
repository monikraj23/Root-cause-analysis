import pandas as pd
import time

def stream_data(file_path, delay=1):
    """
    Simulates a live data stream by reading a CSV file line by line.
    """
    try:
        df = pd.read_csv(file_path)
        for _, row in df.iterrows():
            # Convert row to a dictionary to simulate a JSON API response
            yield row.to_dict()
            time.sleep(delay)
    except FileNotFoundError:
        print(f"Error: Dataset file {file_path} not found.")
        yield None