# ☁️ AI Cloud Incident Monitor

An **AIOps Command Center** that automates Root Cause Analysis (RCA) and remediation for cloud infrastructure using **Groq LPUs** and **Llama 3**.

### 🚀 Key Features
* **Real-Time Monitoring**: Live anomaly detection across CPU, RAM, and Network metrics.
* **Voice SRE Assistant**: Hands-free querying of system status using Groq Whisper-v3.
* **AI Root Cause Analysis**: Instant technical hypotheses and predicted Time-to-Failure (TTF).
* **Automated Remediation**: One-click Slack alerts with generated Bash scripts for instant fixes.
* **Chaos Engineering Lab**: Stress-test your system by injecting traffic load and network jitter.

### 🛠️ Setup
1. Clone the repo: `git clone <your-repo-link>`
2. Install dependencies: `pip install -r requirements.txt`
3. Generate data: `python generate_cloud_data.py`
4. Run the App: `streamlit run dashboard.py`