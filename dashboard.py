import streamlit as st
import pandas as pd
import time
import requests
import os
import random
import plotly.graph_objects as go
from datetime import datetime
from groq import Groq
from streamlit_mic_recorder import mic_recorder
from dotenv import load_dotenv
from streamlit_autorefresh import st_autorefresh

from orchestrator import run_orchestrator
from db import get_recent_rca_results, get_recent_log_events, insert_rca_result, insert_log_event
from llm_reasoning_agent import get_llm_reasoning

load_dotenv(override=True)

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
SLACK_WEBHOOK = os.getenv("SLACK_WEBHOOK_URL")

if not GROQ_API_KEY:
    st.error("❌ GROQ_API_KEY not found! Please check your .env file.")
    st.stop()

client = Groq(api_key=GROQ_API_KEY)

st.set_page_config(page_title="AI Cloud Incident Monitor", layout="wide", page_icon="☁️")


def generate_live_row(chaos_load=100, chaos_latency=0):
    base = {
        "timestamp": datetime.now().isoformat(),
        "cpu_usage": random.randint(20, 80),
        "memory_usage": random.randint(30, 75),
        "disk_io": random.randint(100, 300),
        "network_latency": random.randint(10, 60),
        "error_rate": round(random.uniform(0, 0.04), 3),
        "request_rate": random.randint(200, 600),
    }
    if random.random() < 0.30:
        anomaly_type = random.choice(["cpu", "error", "latency", "combined"])
        if anomaly_type == "cpu":
            base["cpu_usage"] = random.randint(85, 99)
            base["memory_usage"] = random.randint(85, 99)
        elif anomaly_type == "error":
            base["error_rate"] = round(random.uniform(0.5, 1.5), 3)
            base["request_rate"] = random.randint(800, 2000)
        elif anomaly_type == "latency":
            base["network_latency"] = random.randint(200, 500)
            base["disk_io"] = random.randint(400, 800)
        elif anomaly_type == "combined":
            base["cpu_usage"] = random.randint(85, 99)
            base["error_rate"] = round(random.uniform(0.3, 1.0), 3)
            base["network_latency"] = random.randint(150, 400)

    base["cpu_usage"] = min(100, base["cpu_usage"] * (chaos_load / 100))
    base["network_latency"] += chaos_latency
    base["error_rate"] = round(base["error_rate"] + (chaos_load / 5000), 3)
    return base


def send_to_slack(report):
    if not SLACK_WEBHOOK:
        st.sidebar.warning("⚠️ Slack Webhook URL not configured in .env")
        return False
    actions_list = report.get('actions', [])
    formatted_actions = "\n".join([f"• {a}" for a in actions_list]) if actions_list else "Check logs"
    payload = {
        "text": f"🚨 *Incident Detected: {report.get('root_cause', 'Anomaly')}*",
        "attachments": [{
            "color": "#f21616" if report.get('severity') == "Critical" else "#e8912d",
            "fields": [
                {"title": "Severity", "value": report.get('severity', 'High'), "short": True},
                {"title": "Predicted TTF", "value": report.get('predicted_ttf', 'Immediate'), "short": True},
                {"title": "Hypothesis", "value": str(report.get('ai_hypotheses', 'N/A')), "short": False},
                {"title": "Recommended Actions", "value": formatted_actions, "short": False},
                {"title": "Remediation Script", "value": f"`{report.get('remediation_script', 'kubectl get pods')}`", "short": False}
            ],
            "footer": "Nerve.ai | Groq Llama 3"
        }]
    }
    try:
        response = requests.post(SLACK_WEBHOOK, json=payload, timeout=5)
        return response.status_code == 200
    except Exception as e:
        st.sidebar.error(f"Slack Error: {e}")
        return False


def analyze_with_groq(row):
    try:
        rca = get_llm_reasoning(row, mode="fast") or {}
        report = {
            "timestamp": str(row.get('timestamp')),
            "root_cause": rca.get("primary_cause", "Anomaly Detected"),
            "severity": rca.get("severity", "High"),
            "trust_score": rca.get("confidence", 75),
            "actions": rca.get("actions", ["Review system logs"]),
            "ai_hypotheses": rca.get("hypotheses", "Metrics exceed stability thresholds."),
            "predicted_ttf": rca.get("predicted_ttf", "Immediate"),
            "remediation_script": rca.get("remediation_script", "kubectl get pods"),
        }
        insert_rca_result(report)
        return report
    except Exception as e:
        st.error(f"Groq Error: {e}")
        return None


def display_report(report):
    with st.expander("🔍 AI Root Cause & Prediction", expanded=True):
        st.markdown(f"### {report.get('root_cause')}")
        col_s1, col_s2, col_s3 = st.columns(3)
        col_s1.metric("Severity", report.get('severity', 'N/A'))
        col_s2.metric("Trust Score", f"{report.get('trust_score', 0)}%")
        col_s3.metric("Time to Failure", report.get('predicted_ttf', 'Immediate'))
        st.info(f"**Hypothesis:** {report.get('ai_hypotheses')}")
        st.write("### 🛠 Recommended Actions")
        for a in report.get("actions", []):
            st.write(f"✅ {a}")
        st.code(report.get("remediation_script", "kubectl get pods"), language="bash")
        if st.button("🎫 Manual Log to Slack"):
            with st.spinner("Logging..."):
                if send_to_slack(report):
                    st.balloons()
                    st.success("🚀 Logged to Slack!")


# =========================================================
# PAGE HEADER
# =========================================================
st.title("☁️ AI Cloud Incident Monitor")
st.caption("Real-Time Anomaly Detection & Root Cause Analysis (Powered by Groq & Llama 3)")

mode = st.sidebar.radio("Select Mode", [
    "🔴 Live Monitoring",
    "📊 Batch Investigation",
    "🗄️ MongoDB History"
])

st.sidebar.divider()
st.sidebar.subheader("☢️ Chaos Engineering Lab")
chaos_load = st.sidebar.slider("Inject Traffic Load (%)", 100, 500, 100)
chaos_latency = st.sidebar.slider("Simulate Network Jitter (ms)", 0, 1000, 0)

# =========================================================
# VOICE SRE ASSISTANT
# =========================================================
st.sidebar.divider()
st.sidebar.subheader("🎙️ Voice SRE Assistant")

if "voice_chat_history" not in st.session_state:
    st.session_state.voice_chat_history = []

audio = mic_recorder(
    start_prompt="🎙️ Ask AI about incidents",
    stop_prompt="⏹️ Stop Recording",
    key='recorder'
)

if audio:
    with st.sidebar.spinner("Transcribing..."):
        try:
            transcription = client.audio.transcriptions.create(
                file=("temp_audio.wav", audio['bytes']),
                model="whisper-large-v3",
                response_format="text",
            )
            question = transcription.strip()
            st.sidebar.success(f"🗣️ You: {question}")

            # Build context from current session state
            current_metrics = st.session_state.get("current_row", {})
            last_report = st.session_state.get("last_report", {})
            recent_results = get_recent_rca_results(limit=5)

            context = f"""
You are an expert Cloud SRE Assistant. Answer the user's question based on the current system state.

CURRENT METRICS:
{current_metrics if current_metrics else "No live metrics yet."}

LAST INCIDENT REPORT:
- Root Cause: {last_report.get('root_cause', 'None') if last_report else 'No active incident'}
- Severity: {last_report.get('severity', 'N/A') if last_report else 'N/A'}
- Trust Score: {last_report.get('trust_score', 'N/A') if last_report else 'N/A'}
- Time to Failure: {last_report.get('predicted_ttf', 'N/A') if last_report else 'N/A'}
- Actions: {last_report.get('actions', []) if last_report else []}

RECENT INCIDENTS FROM DATABASE:
{[{'root_cause': r.get('root_cause'), 'severity': r.get('severity'), 'timestamp': str(r.get('timestamp', ''))} for r in recent_results] if recent_results else 'None'}

USER QUESTION: {question}

Respond in 2-3 sentences. Be direct, technical, and actionable.
"""

            with st.sidebar.spinner("🤖 Groq is thinking..."):
                response = client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=[{"role": "user", "content": context}],
                    temperature=0.3,
                    max_tokens=200
                )
                answer = response.choices[0].message.content.strip()

            st.session_state.voice_chat_history.append({
                "question": question,
                "answer": answer
            })

        except Exception as e:
            st.sidebar.error(f"Voice Error: {str(e)}")

# Display conversation history
if st.session_state.voice_chat_history:
    st.sidebar.markdown("---")
    st.sidebar.markdown("**💬 Conversation History**")
    for chat in reversed(st.session_state.voice_chat_history[-5:]):
        st.sidebar.markdown(f"🗣️ **You:** {chat['question']}")
        st.sidebar.markdown(f"🤖 **SRE AI:** {chat['answer']}")
        st.sidebar.markdown("---")

    if st.sidebar.button("🗑️ Clear History"):
        st.session_state.voice_chat_history = []
        st.rerun()

# =========================================================
# LIVE MONITORING MODE
# =========================================================
if mode == "🔴 Live Monitoring":
    st.subheader("📡 Live Monitoring")
    run = st.sidebar.toggle("Start Monitoring")

    if "history" not in st.session_state: st.session_state.history = []
    if "last_report" not in st.session_state: st.session_state.last_report = None
    if "last_alert_time" not in st.session_state: st.session_state.last_alert_time = 0
    if "last_analyzed_ts" not in st.session_state: st.session_state.last_analyzed_ts = None
    if "current_row" not in st.session_state: st.session_state.current_row = None
    if "is_anomaly" not in st.session_state: st.session_state.is_anomaly = False

    if run:
        st_autorefresh(interval=15000, key="live_refresh")

        row = generate_live_row(chaos_load, chaos_latency)
        st.session_state.current_row = row

        insert_log_event(source="live_generated", payload=row)

        st.session_state.history.append(row)
        if len(st.session_state.history) > 20:
            st.session_state.history.pop(0)

        is_anomaly = (
            row['error_rate'] > 0.05 or
            row['network_latency'] > 150 or
            row['cpu_usage'] > 80 or
            chaos_load > 300
        )
        st.session_state.is_anomaly = is_anomaly

        if is_anomaly:
            current_ts = row['timestamp']
            if current_ts != st.session_state.last_analyzed_ts:
                with st.spinner("🤖 Groq is analyzing the incident..."):
                    report = analyze_with_groq(row)
                    if report:
                        st.session_state.last_report = report
                        st.session_state.last_analyzed_ts = current_ts
                        current_time = time.time()
                        if report.get('severity') in ["High", "Critical"]:
                            if (current_time - st.session_state.last_alert_time) > 60:
                                if send_to_slack(report):
                                    st.toast("🚀 Alert sent to Slack!")
                                    st.session_state.last_alert_time = current_time
        else:
            st.session_state.last_report = None
            st.session_state.last_analyzed_ts = None

    if st.session_state.current_row:
        row = st.session_state.current_row
        col_m1, col_m2 = st.columns([1, 2])

        with col_m1:
            st.write("### 📊 Current Metrics")
            st.json(row)

        with col_m2:
            if st.session_state.is_anomaly:
                st.error("🚨 INCIDENT / STRESS DETECTED")
                if st.session_state.last_report:
                    display_report(st.session_state.last_report)
                else:
                    st.info("⏳ Waiting for Groq analysis...")
            else:
                st.success("✅ System Healthy")
                st.metric("CPU", f"{row.get('cpu_usage', 0):.1f}%")
                st.metric("Error Rate", f"{row.get('error_rate', 0):.3f}")
                st.metric("Latency", f"{row.get('network_latency', 0)} ms")
    else:
        st.info("👈 Toggle **Start Monitoring** to begin live metric generation")

    if st.session_state.history:
        st.write("### 📈 Live Trends")
        df_history = pd.DataFrame(st.session_state.history)
        st.line_chart(df_history[['cpu_usage', 'error_rate', 'network_latency']])

# =========================================================
# BATCH INVESTIGATION MODE
# =========================================================
elif mode == "📊 Batch Investigation":
    st.subheader("📊 Batch Investigation")
    if st.button("🚨 Run Full Pipeline Analysis"):
        with st.status("Analyzing Historical Logs...", expanded=True) as status:
            df, reports, exec_time = run_orchestrator()
            st.session_state.batch_reports = reports
            status.update(label="Analysis Complete!", state="complete")

    if "batch_reports" in st.session_state and st.session_state.batch_reports:
        st.table(pd.DataFrame(st.session_state.batch_reports)[['root_cause', 'severity', 'trust_score']])

# =========================================================
# MONGODB HISTORY MODE
# =========================================================
elif mode == "🗄️ MongoDB History":
    st.subheader("🗄️ MongoDB — Incident Analytics Dashboard")

    results = get_recent_rca_results(limit=200)
    logs = get_recent_log_events(limit=200)

    if not results:
        st.info("No RCA results yet. Run Live Monitoring or Batch Analysis first.")
    else:
        df_rca = pd.DataFrame(results)
        df_rca['timestamp'] = pd.to_datetime(df_rca['timestamp'], errors='coerce')
        df_rca = df_rca.dropna(subset=['timestamp'])
        df_rca = df_rca.sort_values('timestamp')

        severity_color = {
            "Critical": "#e74c3c",
            "High": "#e67e22",
            "Predictive": "#3498db"
        }

        # ── 1. INCIDENT TIMELINE ─────────────────────────────────────────
        st.markdown("### 📅 Incident Timeline")
        fig_timeline = go.Figure()
        for severity, group in df_rca.groupby("severity"):
            fig_timeline.add_trace(go.Scatter(
                x=group['timestamp'],
                y=group['severity'],
                mode='markers',
                marker=dict(
                    size=12,
                    color=severity_color.get(severity, "#95a5a6"),
                    symbol='circle'
                ),
                name=severity,
                hovertemplate="<b>%{y}</b><br>%{x}<extra></extra>"
            ))
        fig_timeline.update_layout(
            height=300,
            xaxis_title="Time",
            yaxis_title="Severity",
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            font=dict(color='white'),
            legend=dict(orientation="h", y=1.1)
        )
        st.plotly_chart(fig_timeline, use_container_width=True)

        st.divider()

        # ── 2. METRIC TRENDS ─────────────────────────────────────────────
        st.markdown("### 📈 Metric Trends from Log Events")
        if logs:
            df_logs = pd.DataFrame(logs)
            df_logs['timestamp'] = pd.to_datetime(df_logs['timestamp'], errors='coerce')
            df_logs = df_logs.dropna(subset=['timestamp']).sort_values('timestamp')

            if 'payload' in df_logs.columns:
                payload_df = pd.json_normalize(df_logs['payload'])
                for col in ['cpu_usage', 'network_latency', 'error_rate']:
                    if col in payload_df.columns:
                        df_logs[col] = pd.to_numeric(payload_df[col], errors='coerce')

            available = [c for c in ['cpu_usage', 'network_latency', 'error_rate'] if c in df_logs.columns]

            if available:
                fig_metrics = go.Figure()
                colors = {
                    'cpu_usage': '#e74c3c',
                    'network_latency': '#f39c12',
                    'error_rate': '#9b59b6'
                }
                for col in available:
                    fig_metrics.add_trace(go.Scatter(
                        x=df_logs['timestamp'],
                        y=df_logs[col],
                        mode='lines',
                        name=col.replace('_', ' ').title(),
                        line=dict(color=colors.get(col, '#3498db'), width=2)
                    ))
                fig_metrics.update_layout(
                    height=350,
                    xaxis_title="Time",
                    plot_bgcolor='rgba(0,0,0,0)',
                    paper_bgcolor='rgba(0,0,0,0)',
                    font=dict(color='white'),
                    legend=dict(orientation="h", y=1.1)
                )
                st.plotly_chart(fig_metrics, use_container_width=True)
            else:
                st.info("No metric columns found in log payloads yet.")
        else:
            st.info("No log events stored yet.")

        st.divider()

        # ── 3 & 4. SEVERITY BREAKDOWN + TRUST SCORE ──────────────────────
        col1, col2 = st.columns(2)

        with col1:
            st.markdown("### 🥧 Severity Breakdown")
            if 'severity' in df_rca.columns:
                sev_counts = df_rca['severity'].value_counts().reset_index()
                sev_counts.columns = ['severity', 'count']
                fig_pie = go.Figure(go.Pie(
                    labels=sev_counts['severity'],
                    values=sev_counts['count'],
                    hole=0.4,
                    marker=dict(colors=[
                        severity_color.get(s, '#95a5a6') for s in sev_counts['severity']
                    ])
                ))
                fig_pie.update_layout(
                    height=300,
                    plot_bgcolor='rgba(0,0,0,0)',
                    paper_bgcolor='rgba(0,0,0,0)',
                    font=dict(color='white'),
                    showlegend=True
                )
                st.plotly_chart(fig_pie, use_container_width=True)

        with col2:
            st.markdown("### 📊 Trust Score Distribution")
            if 'trust_score' in df_rca.columns:
                scores = pd.to_numeric(df_rca['trust_score'], errors='coerce').dropna()
                fig_hist = go.Figure(go.Histogram(
                    x=scores,
                    nbinsx=10,
                    marker_color='#2ecc71',
                    opacity=0.8
                ))
                fig_hist.update_layout(
                    height=300,
                    xaxis_title="Trust Score (%)",
                    yaxis_title="Count",
                    plot_bgcolor='rgba(0,0,0,0)',
                    paper_bgcolor='rgba(0,0,0,0)',
                    font=dict(color='white')
                )
                st.plotly_chart(fig_hist, use_container_width=True)

        st.divider()

        # ── 5. TOP ROOT CAUSES ────────────────────────────────────────────
        st.markdown("### 🔍 Top Root Causes")
        if 'root_cause' in df_rca.columns:
            cause_counts = df_rca['root_cause'].value_counts().head(8).reset_index()
            cause_counts.columns = ['cause', 'count']
            fig_causes = go.Figure(go.Bar(
                x=cause_counts['count'],
                y=cause_counts['cause'],
                orientation='h',
                marker_color='#e74c3c',
                text=cause_counts['count'],
                textposition='outside'
            ))
            fig_causes.update_layout(
                height=400,
                xaxis_title="Occurrences",
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                font=dict(color='white'),
                yaxis=dict(autorange="reversed")
            )
            st.plotly_chart(fig_causes, use_container_width=True)

        st.divider()

        # ── 6. TTF HEATMAP ────────────────────────────────────────────────
        st.markdown("### 🕐 Incident Heatmap by Hour of Day")
        if 'timestamp' in df_rca.columns and 'severity' in df_rca.columns:
            df_rca['hour'] = df_rca['timestamp'].dt.hour
            df_rca['day'] = df_rca['timestamp'].dt.strftime('%a %b %d')

            critical_df = df_rca[df_rca['severity'].isin(['Critical', 'High'])]

            if not critical_df.empty:
                heatmap_data = critical_df.groupby(['day', 'hour']).size().reset_index(name='count')
                pivot = heatmap_data.pivot(index='day', columns='hour', values='count').fillna(0)

                fig_heat = go.Figure(go.Heatmap(
                    z=pivot.values,
                    x=[f"{h}:00" for h in pivot.columns],
                    y=pivot.index.tolist(),
                    colorscale='Reds',
                    showscale=True
                ))
                fig_heat.update_layout(
                    height=350,
                    xaxis_title="Hour of Day",
                    yaxis_title="Date",
                    plot_bgcolor='rgba(0,0,0,0)',
                    paper_bgcolor='rgba(0,0,0,0)',
                    font=dict(color='white')
                )
                st.plotly_chart(fig_heat, use_container_width=True)
            else:
                st.info("Not enough Critical/High incidents for heatmap yet.")

        st.divider()

        # ── 7. RAW DATA TABLES ────────────────────────────────────────────
        st.markdown("### 🗃️ Raw Records")
        tab1, tab2 = st.tabs(["RCA Results", "Log Events"])

        with tab1:
            display_cols = [c for c in ['timestamp', 'root_cause', 'severity', 'trust_score', 'predicted_ttf'] if c in df_rca.columns]
            st.dataframe(df_rca[display_cols], use_container_width=True)

        with tab2:
            if logs:
                df_logs_display = pd.DataFrame(logs)
                if 'timestamp' in df_logs_display.columns:
                    df_logs_display['timestamp'] = pd.to_datetime(df_logs_display['timestamp']).dt.strftime('%Y-%m-%d %H:%M:%S')
                st.dataframe(df_logs_display[['timestamp', 'source']], use_container_width=True)
            else:
                st.info("No log events yet.")

    if st.button("🔄 Refresh"):
        st.rerun()

st.divider()
st.write("✅ Status: **Monitoring System Online** | 🗄️ MongoDB: **Connected**")