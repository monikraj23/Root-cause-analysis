import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import time
import requests
import os
from groq import Groq 
from streamlit_mic_recorder import mic_recorder 
from dotenv import load_dotenv

from orchestrator import run_orchestrator
from evaluation import evaluate_system
from monitor_api_live import stream_api_data, stream_public_api
from stream_simulator import stream_data
from streamlit_autorefresh import st_autorefresh

# ==============================
# 🔑 SECURE CONFIGURATION
# ==============================
load_dotenv(override=True) 

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
SLACK_WEBHOOK = os.getenv("SLACK_WEBHOOK_URL")

if not GROQ_API_KEY:
    st.error("❌ GROQ_API_KEY not found! Please check your .env file.")
    st.stop()

client = Groq(api_key=GROQ_API_KEY)

st.set_page_config(
    page_title="AI Cloud Incident Monitor",
    layout="wide",
    page_icon="☁️"
)

# HELPER: Slack Integration Logic
def send_to_slack(report):
    if not SLACK_WEBHOOK:
        st.sidebar.warning("⚠️ Slack Webhook URL not configured in .env")
        return False
    
    root_cause = report.get('root_cause', 'System Anomaly')
    severity = report.get('severity', 'High')
    ttf = report.get('predicted_ttf') if report.get('predicted_ttf') != "N/A" else "Immediate"
    
    script = report.get('remediation_script', "Manual investigation required")
    actions_list = report.get('actions', [])
    formatted_actions = "\n".join([f"• {a}" for a in actions_list]) if actions_list else "Check logs"

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
    except Exception as e:
        st.sidebar.error(f"Slack Connection Error: {e}")
        return False

st.title("☁️ AI Cloud Incident Monitor")
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
audio = mic_recorder(start_prompt="Ask AI about incidents", stop_prompt="Stop Recording", key='recorder')

if audio:
    with st.sidebar.spinner("Processing voice..."):
        try:
            transcription = client.audio.transcriptions.create(
                file=("temp_audio.wav", audio['bytes']),
                model="whisper-large-v3",
                response_format="text",
            )
            st.sidebar.success(f"🗣️ You: {transcription}")
        except Exception as e:
            st.sidebar.error(f"Voice Error: {str(e)}")

# =========================================================
# 🔴 LIVE MONITORING MODE
# =========================================================
if mode == "🔴 Live Monitoring":
    st.subheader("📡 Live Monitoring")
    source = st.sidebar.selectbox("Data Source", ["Custom API", "Public API", "Simulated Metrics"])
    run = st.sidebar.toggle("Start Monitoring")

    if "stream" not in st.session_state: st.session_state.stream = None
    if "history" not in st.session_state: st.session_state.history = []
    if "last_alert_time" not in st.session_state: st.session_state.last_alert_time = 0

    if run:
        st_autorefresh(interval=10000, key="live_refresh")
        
        if st.session_state.stream is None:
            st.session_state.stream = stream_data("data/cloud_metrics_large.csv", delay=0)

        try:
            row = next(st.session_state.stream)
            row['cpu_usage'] *= (chaos_load / 100)
            row['network_latency'] += (chaos_latency / 1000)
            row['error_rate'] += (chaos_load / 5000)
            
            st.session_state.history.append(row)
            if len(st.session_state.history) > 20: st.session_state.history.pop(0)
            
            col_m1, col_m2 = st.columns([1, 2])
            with col_m1:
                st.write("### 📊 Metrics")
                st.json(row)

            with col_m2:
                if row['error_rate'] > 0.05 or row['network_latency'] > 0.5 or chaos_load > 300:
                    st.error("🚨 INCIDENT / STRESS DETECTED")
                    report = run_orchestrator(row) 

                    if report:
                        # 🔄 AUTOMATIC ALERTS
                        current_time = time.time()
                        if report.get('severity') in ["High", "Critical"]:
                            if (current_time - st.session_state.last_alert_time) > 60:
                                if send_to_slack(report):
                                    st.toast("🚀 Automated Alert sent!") 
                                    st.session_state.last_alert_time = current_time

                        with st.expander("🔍 AI Root Cause & Prediction", expanded=True):
                            st.markdown(f"### {report.get('root_cause')}")
                            st.info(f"**Hypothesis:** {report.get('ai_hypotheses')}")
                            st.write("### 🛠 Recommended Actions")
                            for a in report.get("actions", []):
                                st.write(f"✅ {a}")
                            st.warning(f"⏳ **Predicted Time to Failure:** {report.get('predicted_ttf', 'Immediate')}")
                            st.code(report.get("remediation_script", "kubectl get pods"), language="bash")
                            
                            # ✨ MANUAL LOG WITH "GLITTERS" (Balloons & Snow)
                            if st.button("🎫 Manual Log to Slack"):
                                with st.spinner("Logging incident..."):
                                    if send_to_slack(report):
                                        st.balloons() # Visual effect 1
                                        st.snow()     # Visual effect 2
                                        st.success("🚀 Incident successfully logged to Slack!")
                                        st.toast("Check your Slack channel!")
                else:
                    st.success("✅ System Healthy")
        except StopIteration:
            st.session_state.stream = None 
            st.warning("Data stream ended.")
    else:
        st.session_state.stream = None

    if st.session_state.history:
        st.write("### 📈 Live Trends")
        st.line_chart(pd.DataFrame(st.session_state.history)[['cpu_usage', 'error_rate']])

# =========================================================
# 📊 BATCH INVESTIGATION MODE
# =========================================================
else:
    st.subheader("📊 Batch Investigation")
    if st.button("🚨 Run Full Pipeline Analysis"):
        with st.status("Analyzing Historical Logs...", expanded=True) as status:
            df, reports, exec_time = run_orchestrator()
            st.session_state.batch_reports = reports
            status.update(label="Analysis Complete!", state="complete")

    if "batch_reports" in st.session_state:
        st.table(pd.DataFrame(st.session_state.batch_reports)[['root_cause', 'severity', 'confidence']])

st.divider()
st.write(f"✅ Status: **Monitoring System Online**")