import os
import json
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
client = Groq(api_key=GROQ_API_KEY)


def generate_ai_analysis(metrics_context):
    """
    Calls Groq with actual metric values to get a dynamic RCA report.
    No caching — every row gets a fresh, unique analysis.
    """
    # Extract key values for dynamic prompt context
    if isinstance(metrics_context, dict):
        cpu = metrics_context.get("cpu_usage", 0)
        memory = metrics_context.get("memory_usage", 0)
        latency = metrics_context.get("network_latency", 0)
        error_rate = metrics_context.get("error_rate", 0)
        disk_io = metrics_context.get("disk_io", 0)
        request_rate = metrics_context.get("request_rate", 0)
    else:
        cpu = memory = latency = error_rate = disk_io = request_rate = 0

    prompt = f"""
You are a Senior Cloud SRE and Predictive Analyst. Analyze these EXACT cloud metrics:

- CPU Usage: {cpu}%
- Memory Usage: {memory}%
- Network Latency: {latency}ms
- Error Rate: {error_rate}
- Disk IO: {disk_io}
- Request Rate: {request_rate}

Based on the ACTUAL values above, generate a dynamic RCA report. Your response MUST vary based on the real numbers.

STRICT RULES:
1. "primary_cause": Name the single most anomalous metric and why it is problematic.
2. "hypotheses": List 2 likely causes as a JSON array of strings based on the actual metrics.
3. "actions": List 2-3 specific remediation steps as a JSON array of strings.
4. "remediation_script": A real, single-line bash command specific to the root cause. NEVER return N/A.
5. "severity":
   - "Critical" if error_rate > 0.5 OR cpu > 90
   - "High" if cpu > 75 OR latency > 200 OR error_rate > 0.05
   - "Predictive" otherwise
6. "predicted_ttf":
   - "IMMEDIATE" if error_rate > 0.5
   - "5m" if cpu > 90
   - "15m" if cpu > 80 OR latency > 300
   - "30m" if cpu > 70 OR latency > 150
   - "60m" otherwise
7. "confidence": A number 0-100 calculated from metric severity:
   - Start at 50
   - Add 20 if error_rate > 0.3
   - Add 10 if error_rate > 0.05
   - Add 10 if cpu > 85
   - Add 5 if cpu > 70
   - Add 5 if latency > 200
   - Add 5 if memory > 85
   - Return the final sum capped at 99

Return ONLY a valid JSON object with exactly these keys:
"primary_cause", "hypotheses", "actions", "remediation_script", "severity", "predicted_ttf", "confidence"
"""

    try:
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            temperature=0.4
        )
        return json.loads(completion.choices[0].message.content)
    except Exception as e:
        return {
            "primary_cause": "System Analysis Failed",
            "hypotheses": [f"Agent Error: {str(e)}", "Check API connectivity"],
            "actions": ["Check API Connectivity", "Restart Monitoring", "Manual Review"],
            "remediation_script": "kubectl get events --sort-by='.lastTimestamp'",
            "severity": "High",
            "predicted_ttf": "Immediate",
            "confidence": 0
        }


def get_llm_reasoning(metrics, mode="fast"):
    """Helper function called by orchestrator and dashboard."""
    return generate_ai_analysis(metrics)