import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import time
import requests
import os
from groq import Groq 
from streamlit_mic_recorder import mic_recorder 
from dotenv import load_dotenv # Added for security

from orchestrator import run_orchestrator
from evaluation import evaluate_system
from monitor_api_live import stream_api_data, stream_public_api
from stream_simulator import stream_data
from streamlit_autorefresh import st_autorefresh

# ==============================
# 🔐 SECURE CONFIGURATION
# ==============================
load_dotenv() # Pulls variables from your private .env file

# Fetching secrets from environment variables instead of hardcoding
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
SLACK_WEBHOOK = os.getenv("SLACK_WEBHOOK_URL")

# Guardrail: Ensure the app doesn't crash if secrets are missing
if not GROQ_API_KEY:
    st.error("⚠️ **GROQ_API_KEY not found.** Please ensure it is defined in your `.env` file.")
    st.stop()

client = Groq(api_key=GROQ_API_KEY)

st.set_page_config(
    page_title="Nerve.ai | Cloud Incident Monitor",
    layout="wide",
    page_icon="☁️"
)

# HELPER: Slack Integration Logic
def send_to_slack(report):
    if not SLACK_WEBHOOK:
        return False
        
    # Extracting report details for the Slack payload
    root_cause = report.get('root_cause', 'System Anomaly')
    severity = report.get('severity', 'High')
    ttf = report.get('predicted_ttf') if report.get('predicted_ttf') != "N/A" else "Immediate"
    
    script = report.get('remediation_script', "Manual investigation required")
    actions_list = report.get('actions', [])
    formatted_actions = "\n".join([f"• {a}" for a in actions_list]) if actions_list else "Check logs."

    payload = {
        "text": f"🚨 *Incident Detected: {root_cause}*",
        "attachments": [
            {
                "color": "#f21616" if severity == "Critical" else "#e8912d",
                "fields": [
                    {"title": "Severity", "value": severity, "short": True},
                    {"title": "Predicted TTF", "value": ttf, "short": True},
                    {"title": "Hypothesis", "value": report.get('ai_hypotheses', 'N/A'), "short": False},
                    {"title": "Recommended Actions", "value": formatted_actions, "short": False},
                    {"title": "Remediation Script", "value": f"`{script}`", "short": False}
                ],
                "footer": "Nerve.ai | Groq Llama 3"
            }
        ]
    }
    try:
        response = requests.post(SLACK_WEBHOOK, json=payload, timeout=5)
        return response.status_code == 200
    except Exception:
        return False

st.title("☁️ Nerve.ai: Cloud Incident Monitor")
st.caption("Real-Time Anomaly Detection & Root Cause Analysis (Powered by Groq & Llama 3)")

# ==============================
# SIDEBAR: MODES, CHAOS & VOICE
# ==============================
mode = st.sidebar.radio("Select Mode", ["🔴 Live Monitoring", "📊 Batch Investigation"])

st.sidebar.divider()
st.sidebar.subheader("☢️ Chaos Engineering Lab")
chaos_load = st.sidebar.slider("Inject Traffic Load (%)", 100, 500, 100)
chaos_latency = st.sidebar.slider("Simulate Network Jitter (ms)", 0, 1000, 0)

st.sidebar.divider()
st.sidebar.subheader("🎙️ Voice SRE Assistant")
audio = mic_recorder(
    start_prompt="Ask AI about incidents", 
    stop_prompt="Stop Recording", 
    key='recorder'
)

if audio:
    st.sidebar.info("Processing your voice command...")
    try:
        # Voice-to-Text via Groq Whisper
        transcription = client.audio.transcriptions.create(
            file=("temp_audio.wav", audio['bytes']),
            model="whisper-large-v3",
            response_format="text",
        )
        st.sidebar.success(f"🗣️ You: {transcription}")
        
        query = transcription.lower()
        if any(word in query for word in ["status", "happen", "incident", "current"]):
            if st.session_state.get('history'):
                last_event = st.session_state.history[-1]
                st.sidebar.write(f"🤖 **AI Status Check:**")
                st.sidebar.write(f"* CPU: {last_event.get('cpu_usage', 0):.1f}%")
                st.sidebar.write(f"* Errors: {last_event.get('error_rate', 0):.2f}")
            else:
                st.sidebar.warning("🤖 AI: No live data available yet.")
    except Exception as e:
        st.sidebar.error(f"Voice Error: {str(e)}")

# =========================================================
# 🔴 LIVE MONITORING MODE
# =========================================================
if mode == "🔴 Live Monitoring":
    st.subheader("📡 Live Infrastructure Feed")
    run = st.sidebar.toggle("Start Monitoring")

    if "history" not in st.session_state: st.session_state.history = []
    if "last_alert_time" not in st.session_state: st.session_state.last_alert_time = 0

    if run:
        st_autorefresh(interval=5000, key="live_refresh") # Refresh every 5s
        
        try:
            # Simulate real-time data stream
            stream = stream_data("data/cloud_metrics_large.csv", delay=0)
            row = next(stream)
            
            # Apply Chaos Modifiers
            row['cpu_usage'] *= (chaos_load / 100)
            row['network_latency'] += (chaos_latency / 1000)
            row['error_rate'] += (chaos_load / 5000)
            
            st.session_state.history.append(row)
            st.session_state.history = st.session_state.history[-20:]
            
            # Incident Logic
            if row['error_rate'] > 0.05 or chaos_load > 300:
                st.error("🚨 CRITICAL ANOMALY DETECTED")
                with st.spinner("⚡ AI Root Cause Analysis in progress..."):
                    report = run_orchestrator(row) 

                if report:
                    # Rate-limited Slack alerts (once per minute)
                    if report.get('severity') in ["High", "Critical"] and (time.time() - st.session_state.last_alert_time > 60):
                        if send_to_slack(report):
                            st.toast("🚀 Automated Alert sent to Slack!")
                            st.session_state.last_alert_time = time.time()

                    with st.expander("🔍 AI Root Cause & Remediation", expanded=True):
                        st.markdown(f"### {report.get('root_cause')}")
                        st.info(f"**AI Hypothesis:** {report.get('ai_hypotheses')}")
                        st.code(report.get("remediation_script", "kubectl get pods"), language="bash")
            else:
                st.success("✅ System Healthy")
        except StopIteration:
            st.info("Stream concluded.")

    if st.session_state.history:
        st.line_chart(pd.DataFrame(st.session_state.history)[['cpu_usage', 'error_rate']])

# =========================================================
# 📊 BATCH INVESTIGATION MODE
# =========================================================
else:
    st.subheader("📊 Historical Log Analysis")
    if st.button("🚨 Run Full AI Pipeline"):
        with st.status("Analyzing historical logs...", expanded=True) as status:
            df, reports, exec_time = run_orchestrator()
            st.session_state.batch_reports = reports
            status.update(label="Analysis Complete!", state="complete")

    if "batch_reports" in st.session_state:
        st.table(pd.DataFrame(st.session_state.batch_reports)[['root_cause', 'severity', 'confidence']])

st.divider()
st.write(f"✅ **Nerve.ai Monitoring Engine Online**")