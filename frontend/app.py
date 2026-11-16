import os
import sys
import time
import subprocess
from pathlib import Path
import requests
import streamlit as st

# --- Auto-Start FastAPI Backend on Streamlit Cloud ---
BASE_DIR = Path(__file__).resolve().parent.parent
BACKEND_DIR = BASE_DIR / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

# Load Streamlit Cloud Secrets into environment variables
for secret_key in ["GROQ_API_KEY", "WEBHOOK_SECRET"]:
    if secret_key in st.secrets and not os.getenv(secret_key):
        os.environ[secret_key] = st.secrets[secret_key]

@st.cache_resource
def start_backend_server():
    try:
        r = requests.get("http://127.0.0.1:8000/", timeout=1)
        if r.status_code == 200:
            return True
    except Exception:
        pass

    # Seed database if empty & start Uvicorn in background
    env = os.environ.copy()
    subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "main:app", "--host", "127.0.0.1", "--port", "8000"],
        cwd=str(BACKEND_DIR),
        env=env
    )
    # Wait up to 20 seconds for FastAPI & SentenceTransformer to boot
    for _ in range(20):
        try:
            r = requests.get("http://127.0.0.1:8000/", timeout=1)
            if r.status_code == 200:
                break
        except Exception:
            time.sleep(1)

    # Auto-seed agents if none exist
    try:
        agents = requests.get("http://127.0.0.1:8000/api/v1/agents", timeout=3).json()
        if len(agents) == 0:
            subprocess.run([sys.executable, "seed_agents.py"], cwd=str(BACKEND_DIR), env=env)
    except Exception:
        pass
    return True

start_backend_server()