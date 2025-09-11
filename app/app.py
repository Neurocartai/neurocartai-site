from flask import Flask, jsonify
from flask import Flask, jsonify
from flask import Flask, jsonify, request
import os
from utils.risk_guard import RiskGuard

app = Flask(name)

RISK_PATH = os.environ.get("RISK_BOOKLET_PATH", "config/agent5_risks.yml")
GUARD = RiskGuard(RISK_PATH)

 @app.route("/health")
 def health():
     return jsonify({"status": "ok"}), 200
 
@app.route("/dispatch/check", methods=["POST"])
def dispatch_check():
    """
    Accepts a JSON payload describing a pending post/action and checks guardrails.
    Example body:
    {
      "kind": "social_post",
      "channel": "twitter",
      "caption": "Big launch today!",
      "image_id": "gcs://licensed/hero.png",
      "asset_source": "unsplash-api",
      "license_tag": "unsplash-123",
      "locale": "US",
      "sot_checked": true
    }
    """
    action = request.get_json(silent=True) or {}
    ok, violations = GUARD.check(action)
    return jsonify({"ok": ok, "violations": violations}), (200 if ok else 409)

@app.route("/dispatch/record", methods=["POST"])
def dispatch_record():
    """Call after a post succeeds so guard has history for duplicates/rate limits."""
    ev = request.get_json(silent=True) or {}
    GUARD.record_event(ev)
    return jsonify({"status":"recorded"}), 200

 @app.route("/cron/daily", methods=["POST"])
 def cron_daily():
     # placeholder for daily tasks
     return jsonify({"status": "daily job executed"}), 200

@app.route("/health")
def health():
    return jsonify({"status": "ok"}), 200

@app.route("/cron/daily", methods=["POST"])
def cron_daily():
    # placeholder for daily tasks
    return jsonify({"status": "daily job executed"}), 200

@app.route("/cron/fast", methods=["POST"])
def cron_fast():
    # placeholder for fast job
    return jsonify({"status": "fast job executed"}), 200

if name == "main":
    app.run(host="0.0.0.0", port=8080)
