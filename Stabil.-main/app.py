import os
from flask import Flask, render_template, request, redirect, jsonify
import time
import uuid
import json
import base64
import cv2
from tracker import start_tracking, is_camera_reachable, format_camera_url
from analysis import analyze_session
from database import init_db, save_session, get_all_sessions, get_last_session
from planner import generate_recommendation
from predictor import predict_next_psi

try:
    from prism_client import trace_surgical_analysis, trace_session_trajectory
except ImportError:
    trace_surgical_analysis = None
    trace_session_trajectory = None

try:
    from flask_cors import CORS
    has_cors = True
except ImportError:
    has_cors = False

app = Flask(__name__)
if has_cors:
    CORS(app)

# Initialize DB
init_db()


# =========================
# HOME PAGE
# =========================
@app.route("/")
def home():
    return render_template("index.html")


# =========================
# TRAIN PAGE
# =========================
@app.route("/train")
def train():
    return render_template("train.html")



# =========================
# API: CHECK CAMERA REACHABILITY
# =========================
@app.route("/api/check_camera", methods=["GET", "POST"])
def check_camera():
    if request.method == "POST":
        data = request.get_json(silent=True) or request.form
        cam_url = data.get("url") or data.get("ip_address") or data.get("camera_url")
    else:
        cam_url = request.args.get("url") or request.args.get("ip_address") or request.args.get("camera_url")

    if not cam_url:
        return jsonify({"reachable": False, "formatted_url": None, "message": "No camera address provided"}), 400

    formatted = format_camera_url(cam_url)
    reachable = is_camera_reachable(formatted, timeout=0.8)
    
    if isinstance(formatted, int):
        msg = f"Local webcam device index {formatted} selected."
    elif reachable:
        msg = f"Successfully reached {formatted}."
    else:
        msg = f"Could not connect to {formatted}. Please ensure phone and PC are on the same Wi-Fi network and IP Webcam is streaming."

    return jsonify({
        "reachable": reachable,
        "formatted_url": formatted,
        "message": msg
    })


# =========================
# START TRAINING
# =========================
@app.route("/start", methods=["POST"])
def start():
    if request.is_json:
        req_data = request.get_json() or {}
        mode = req_data.get("mode")
        top_cam_url = req_data.get("top_cam_url") or req_data.get("ip_address")
        side_cam_url = req_data.get("side_cam_url")
    else:
        mode = request.form.get("mode")
        top_cam_url = request.form.get("top_cam_url") or request.form.get("ip_address")
        side_cam_url = request.form.get("side_cam_url")

    start_time = time.time()
    data = start_tracking(mode, side_cam_url=side_cam_url, top_cam_url=top_cam_url)
    analysis = analyze_session(data)
    latency_ms = max(1, int((time.time() - start_time) * 1000))

    session_id = f"session-{uuid.uuid4().hex[:12]}"

    save_session(
        "default",
        mode,
        data["psi"],
        data["tremor"],
        data["error"],
        data["depth_error"],
        data["pressure_dev"],
        data["trajectory"],
        reach_distance=data.get("reach_distance"),
        reach_error=data.get("reach_error"),
        reach_violations=data.get("reach_violations", 0)
    )

    if trace_surgical_analysis:
        trace_surgical_analysis(session_id, "default", mode, data, analysis, latency_ms)
    if trace_session_trajectory:
        trace_session_trajectory(session_id, "default", mode, data, analysis, latency_ms)

    if request.is_json or request.headers.get("Accept") == "application/json":
        return jsonify({"data": data, "analysis": analysis, "session_id": session_id})

    return render_template("result.html", data=data, analysis=analysis)


# =========================
# API: ARDUINO HARDWARE STATUS & TELEMETRY
# =========================
@app.route("/api/hardware/status")
def hardware_status():
    try:
        from hardware import get_hardware_reader
        reader = get_hardware_reader()
        curr = reader.get_current_distance()
        return jsonify({
            "connected": reader.is_connected,
            "port": reader.port,
            "current_distance_cm": curr,
            "latest_distance_cm": reader.latest_distance,
            "is_warning": bool(curr is not None and curr < 10.0),
            "last_seen_epoch": reader.last_seen_time,
            "available_ports": reader.list_available_ports()
        })
    except Exception as e:
        return jsonify({"connected": False, "error": str(e)}), 500


@app.route("/api/hardware/connect", methods=["POST"])
def hardware_connect():
    req_data = request.get_json(silent=True) or {}
    port = req_data.get("port")
    try:
        from hardware import get_hardware_reader
        reader = get_hardware_reader()
        success = reader.connect(port=port)
        return jsonify({
            "success": success,
            "connected": reader.is_connected,
            "port": reader.port,
            "message": f"Connected to {reader.port}" if success else f"Could not connect to {port or 'Arduino'}"
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/camera_snapshot", methods=["GET", "POST"])
def camera_snapshot():
    if request.method == "POST":
        data = request.get_json(silent=True) or request.form
        cam_url = data.get("url") or data.get("ip_address") or data.get("camera_url")
    else:
        cam_url = request.args.get("url") or request.args.get("ip_address") or request.args.get("camera_url")

    if not cam_url:
        return jsonify({"success": False, "message": "No camera address provided"}), 400

    formatted = format_camera_url(cam_url)
    if isinstance(formatted, str) and formatted.startswith("http"):
        if not is_camera_reachable(formatted, timeout=0.6):
            return jsonify({"success": False, "message": f"Camera is unreachable or offline: {formatted}"}), 400

    try:
        cap = cv2.VideoCapture(formatted)
        if not cap.isOpened():
            return jsonify({"success": False, "message": f"Cannot open camera source: {formatted}"}), 400

        ret, frame = cap.read()
        cap.release()
        if not ret or frame is None:
            return jsonify({"success": False, "message": f"Failed to grab frame from: {formatted}"}), 400

        h, w = frame.shape[:2]
        new_w = min(480, w)
        new_h = int(h * (new_w / w))
        thumb = cv2.resize(frame, (new_w, new_h))

        _, buf = cv2.imencode(".jpg", thumb, [int(cv2.IMWRITE_JPEG_QUALITY), 75])
        b64 = base64.b64encode(buf).decode("utf-8")
        return jsonify({"success": True, "image": f"data:image/jpeg;base64,{b64}"})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@app.route("/api/hardware/simulate_reading", methods=["POST"])
def hardware_simulate():
    """Allows automated testing of ultrasonic reach sensor inputs."""
    req_data = request.get_json(silent=True) or {}
    dist = float(req_data.get("distance", 14.5))
    try:
        from hardware import get_hardware_reader
        reader = get_hardware_reader()
        reader.inject_synthetic_reading(dist)
        return jsonify({"status": "ok", "injected_distance": dist})
    except Exception as e:
        return jsonify({"status": "error", "error": str(e)}), 500


# =========================
# DASHBOARD
# =========================
@app.route("/dashboard")
def dashboard():

    sessions = get_all_sessions("default")

    labels = []
    psi = []
    tremor = []
    error = []
    depth = []

    for s in sessions:
        labels.append(s["timestamp"])
        psi.append(float(s["psi"]))
        tremor.append(float(s["tremor"]))
        error.append(float(s["error"]))
        depth.append(float(s["depth_error"]))

    recommendation = generate_recommendation("default")
    prediction = predict_next_psi("default", 5)

    return render_template(
        "dashboard.html",
        labels=labels,
        psi=psi,
        tremor=tremor,
        error=error,
        depth=depth,
        recommendation=recommendation,
        prediction=prediction,
        modes=labels # Fix for template using 'modes' or 'labels'
    )


# =========================
# REPORTS PAGE
# =========================
@app.route("/reports")
def reports():
    sessions = get_all_sessions("default")
    return render_template("reports.html", sessions=sessions)


# =========================
# HEATMAP / REPLAY
# =========================
@app.route("/replay")
def replay():
    return render_template("replay.html")

@app.route("/heatmap-data")
def heatmap_data():
    # Get the latest session for replay
    session = get_last_session("default")

    if not session:
        return jsonify([])

    # Trajectory is stored as a JSON string in DB, need to parse if it is, or if already list
    try:
        trajectory = json.loads(session["trajectory"])
    except:
        trajectory = [] # Fallback

    return jsonify(trajectory)


# =========================
# PLANNER / PROGRESS
# =========================
@app.route("/progress")
def progress():
    recommendation = generate_recommendation("default")
    prediction = predict_next_psi("default", 5)
    
    # Calculate simple stats for the view
    sessions = get_all_sessions("default")
    avg_psi = 0
    if sessions:
        avg_psi = sum([s["psi"] for s in sessions]) / len(sessions)

    return render_template(
        "progress.html", 
        recommendation=recommendation, 
        prediction=prediction,
        avg_psi=round(avg_psi, 1)
    )


# =========================
# LEADERBOARD
# =========================
@app.route("/leaderboard")
def leaderboard():
    # Mock leaderboard
    leaders = [
        {"name": "Dr. Strange", "score": 98.5},
        {"name": "House M.D.", "score": 96.2},
        {"name": "Meredith Grey", "score": 94.0},
        {"name": "You", "score": 0} # Placeholder
    ]
    
    # Try to get user max score
    sessions = get_all_sessions("default")
    if sessions:
        max_score = max([s["psi"] for s in sessions])
        leaders[3]["score"] = max_score

    leaders.sort(key=lambda x: x["score"], reverse=True)
    
    return render_template("leaderboard.html", leaders=leaders)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    debug = os.environ.get("FLASK_ENV") != "production"
    app.run(host="0.0.0.0", port=port, debug=debug)
