import time
import numpy as np
from database import get_all_sessions

try:
    from prism_client import trace_surgical_recommendation
except ImportError:
    trace_surgical_recommendation = None


def generate_recommendation(user_id="default"):
    start_time = time.time()
    sessions = get_all_sessions(user_id)

    reach_errors = []
    reach_distances = []
    for s in sessions:
        try:
            r_err = s["reach_error"]
            if r_err is not None:
                reach_errors.append(float(r_err))
            r_dist = s["reach_distance"]
            if r_dist is not None:
                reach_distances.append(float(r_dist))
        except (KeyError, IndexError, TypeError):
            pass

    hardware_context = {
        "latest_reach_distance": round(reach_distances[-1], 2) if reach_distances else None,
        "avg_reach_distance": round(float(np.mean(reach_distances)), 2) if reach_distances else None,
        "reach_error_variance": round(float(np.var(reach_errors)), 2) if len(reach_errors) > 1 else None,
        "latest_psi": round(float(sessions[-1]["psi"]), 2) if sessions else 0.0,
        "recommended_drill": "line"
    }

    if len(sessions) < 3:
        rec = {
            "recommended_mode": "line",
            "focus_metric": "Consistency",
            "goal": "Build baseline stability (5 sessions)",
            "trend": "Collecting Data"
        }
        if trace_surgical_recommendation:
            latency_ms = max(1, int((time.time() - start_time) * 1000))
            trace_surgical_recommendation(user_id, rec, len(sessions), latency_ms, hardware_context=hardware_context)
        return rec

    tremor = np.array([float(s["tremor"]) for s in sessions])
    error = np.array([float(s["error"]) for s in sessions])
    depth = np.array([float(s["depth_error"]) for s in sessions])

    # Normalize variances to compare different metrics
    variances = {
        "tremor": float(np.var(tremor)),
        "error": float(np.var(error)),
        "depth": float(np.var(depth))
    }
    if len(reach_errors) >= 2:
        variances["reach"] = float(np.var(reach_errors))

    weakest = max(variances, key=variances.get)

    mapping = {
        "tremor": "micro",
        "error": "circle",
        "depth": "depth_drill",
        "reach": "needle"
    }

    focus_names = {
        "tremor": "TREMOR CONTROL",
        "error": "TRAJECTORY ACCURACY",
        "depth": "PENETRATION DEPTH",
        "reach": "REACH STABILITY"
    }

    goals = {
        "tremor": "Reduce hand tremor variance",
        "error": "Minimize path deviation error",
        "depth": "Stabilize vertical depth consistency",
        "reach": "Maintain stable ultrasonic reach distance and eliminate buzzer boundary warnings"
    }

    # Determine trend (slope of PSI)
    psi = np.array([float(s["psi"]) for s in sessions])
    x = np.arange(len(psi))
    slope, _ = np.polyfit(x, psi, 1)
    
    trend_msg = "Steady Improvement" if slope > 0.5 else "Plateau Detected" if slope > -0.5 else "Declining Performance"

    rec = {
        "recommended_mode": mapping.get(weakest, "line"),
        "focus_metric": focus_names.get(weakest, weakest.upper()),
        "goal": goals.get(weakest, "Reduce variance in " + weakest),
        "trend": trend_msg
    }
    hardware_context["recommended_drill"] = rec["recommended_mode"]

    if trace_surgical_recommendation:
        latency_ms = max(1, int((time.time() - start_time) * 1000))
        trace_surgical_recommendation(user_id, rec, len(sessions), latency_ms, hardware_context=hardware_context)

    return rec
