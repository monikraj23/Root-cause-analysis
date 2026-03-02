from orchestrator import run_orchestrator
from stream_simulator import stream_data

# number of anomalies that used AI reasoning
AI_SAMPLE_LIMIT = 5   # keep in sync with rca_agent.py

MODE = "batch"        # change to "live" for streaming mode


def print_report(reports, exec_time):
    print("\n==============================")
    print("AGENTIC DATA QA REPORT")
    print("==============================")

    for i, r in enumerate(reports, 1):

        print(f"\n===== ANOMALY {i} =====")
        print("Timestamp:", r["timestamp"])

        print("\nRoot Cause Analysis:")
        print(r["llm_root_cause"])

        print("\nBusiness Impact:")
        print(r["business_impact"]["summary"])

        print("\nRecommended Actions:")
        for a in r["actions"]:
            print("-", a)

        print("\nTrust Score:", r["trust_score"])

        # ✅ SAFE AI STATUS DISPLAY
        ai_text = r.get("ai_hypotheses", "")

        if "skipped" in ai_text.lower():
            print("AI Status: Skipped (speed optimization)")
        elif ai_text:
            print("AI Status: Local AI reasoning applied")
        else:
            print("AI Status: Not available")

    print("\n==============================")
    print("EXECUTION SUMMARY")
    print("==============================")
    print("Execution Time:", round(exec_time, 2), "seconds")
    print("Total Anomalies:", len(reports))
    print("AI Analyses Used:", min(len(reports), AI_SAMPLE_LIMIT))


def live_monitor():
    print("\n📡 LIVE MONITORING STARTED...\n")

    for row in stream_data("data/online_retail.csv", delay=0.5):
        result = run_orchestrator(row)

        if result:   # anomaly detected
            print("\n🚨 LIVE ALERT 🚨")
            print("Time:", result["timestamp"])
            print("Root Cause:", result["root_cause"])
            print("Trust Score:", result["trust_score"])
            print("---------------------------")


def main():

    if MODE == "batch":
        df, reports, exec_time = run_orchestrator()
        print_report(reports, exec_time)

    elif MODE == "live":
        live_monitor()

    else:
        print("Invalid MODE. Use 'batch' or 'live'.")


if __name__ == "__main__":
    main()