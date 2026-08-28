"""
Entry point wrapper for the Licensing Portal Railway deployment.
Railway's Custom Start Command runs `python licensing_app.py` from the repo root.
This file imports the actual app from licensing_system/app.py and runs it.
"""
import os
import sys

# Add licensing_system directory to Python path so it can find its modules
LICENSING_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "licensing_system")
sys.path.insert(0, LICENSING_DIR)

# Change working directory so Flask can find templates/ and static/
os.chdir(LICENSING_DIR)

# Import the Flask app (this triggers create_app() at module level)
from app import app  # noqa: E402

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8081))
    app.run(host="0.0.0.0", port=port)
