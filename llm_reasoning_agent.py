import os
import json
import streamlit as st
from groq import Groq
from dotenv import load_dotenv

# =========================================================
# 🔑 SECURE API CONFIGURATION
# =========================================================
# Load environment variables from .env file
load_dotenv()

# Get the API key securely
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

if not GROQ_API_KEY:
    st.error("GROQ_API_KEY not found! Please check your .env file or Streamlit secrets.")
    st.stop()

client = Groq(api_key=GROQ_API_KEY)

@st.cache_data(show_spinner=False, ttl=600)
def generate_ai_analysis(metrics_context):
    """
    Forces Groq to provide a strictly formatted JSON RCA report.
    """
    # System Instruction for the AI
    prompt = f"""
    You are a Senior Cloud SRE and Predictive Analyst. Analyze these metrics: {metrics_context}
    
    STRICT OUTPUT RULES:
    1. "remediation_script": Provide a REAL single-line Bash command. NEVER return N/A or None.
    2. "predicted_ttf": If Error Rate > 0.1, return "IMMEDIATE". If stress is high, predict time (e.g., "12m").
    3. "severity": Choose: "Critical", "High", or "Predictive".
    
    Return ONLY a JSON object with these exact keys:
    "primary_cause", "hypotheses", "actions", "remediation_script", "severity", "predicted_ttf", "confidence"
    """

    try:
        # Utilizing Llama 3 via Groq LPU for low-latency reasoning
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"}, # Essential for valid JSON
            temperature=0.2
        )
        return json.loads(completion.choices[0].message.content)
    except Exception as e:
        # Fail-safe mechanism to ensure the UI doesn't crash
        return {
            "primary_cause": "System Analysis Failed",
            "hypotheses": f"Agent Error: {str(e)}",
            "actions": ["Check API Connectivity", "Restart Monitoring", "Manual Review"],
            "remediation_script": "kubectl get events --sort-by='.lastTimestamp'",
            "severity": "High",
            "predicted_ttf": "Immediate",
            "confidence": 0
        }

def get_llm_reasoning(prompt, mode="fast"):
    """Helper function for the orchestrator."""
    return generate_ai_analysis(prompt)