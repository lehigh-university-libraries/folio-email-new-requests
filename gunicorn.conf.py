import os

os.environ["HOME"] = "/tmp"

bind = "0.0.0.0:5000"
workers = int(os.environ.get("WORKERS", 4))
