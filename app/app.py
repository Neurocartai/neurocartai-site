from flask import Flask, jsonify

app = Flask(name)

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
