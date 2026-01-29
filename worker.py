import os
from backend.orchestrator import run_pipeline

if __name__ == "__main__":
    mode = os.getenv("WORKER_MODE", "LIVE").upper()
    run_pipeline(mode)