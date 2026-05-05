import logging
import threading

from flask import Flask, jsonify

from new_requests import load_config, run_check

log = logging.getLogger(__name__)

cfg = load_config("config.yaml")
app = Flask(__name__)
lock = threading.Lock()


@app.post("/check-requests")
def check_requests():
    if not lock.acquire(blocking=False):
        return jsonify({"error": "check already in progress"}), 409
    try:
        success, found = run_check(cfg)
        if not success:
            return jsonify({"error": "one or more emails failed"}), 500
        return jsonify({"found": found})
    except Exception as exc:
        log.exception("Unhandled error during check")
        return jsonify({"error": str(exc)}), 500
    finally:
        lock.release()


@app.route("/healthcheck")
def healthcheck():
    return "OK"
