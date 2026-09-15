import os
import sys
import json
import logging
import uuid
from typing import Optional, Dict, Any, List

logger = logging.getLogger("prismtrace")

# Automatically load local .env file if present
def _load_env():
    env_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
    if os.path.exists(env_file):
        try:
            with open(env_file, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        k, v = line.split("=", 1)
                        k = k.strip()
                        v = v.strip().strip("'\"")
                        if k not in os.environ:
                            os.environ[k] = v
        except Exception as e:
            logger.debug("Failed to read .env file: %s", e)

_load_env()

# Configuration
PRISMTRACE_API_KEY = os.environ.get("PRISMTRACE_API_KEY", "pt-sk-844bddeda98e4c539bfe7e8d8ab8fe57")
PRISMTRACE_PROJECT_ID = os.environ.get("PRISMTRACE_PROJECT_ID", "f3b27f46-8c06-41bf-ad16-3583c338e0b7")
PRISMTRACE_HOST = os.environ.get("PRISMTRACE_HOST", "https://prism-api-prod.up.railway.app")

_client = None

def get_prism_client():
    global _client
    if _client is not None:
        return _client
    if not PRISMTRACE_API_KEY or not PRISMTRACE_PROJECT_ID:
        return None
    try:
        from prismtrace import PRISMtrace
        _client = PRISMtrace(
            api_key=PRISMTRACE_API_KEY,
            host=PRISMTRACE_HOST,
            project_id=PRISMTRACE_PROJECT_ID,
        )
        return _client
    except Exception as e:
        logger.warning(f"Failed to initialize PRISMtrace: {e}")
        return None


def trace_surgical_analysis(session_id: str, user_id: str, mode: str, data: dict, analysis: dict, latency_ms: int = 50):
    """
    Records analysis of surgical precision metrics (PSI, tremor, path error, depth, pressure, reach) into PRISM.
    """
    client = get_prism_client()
    if not client:
        return
    try:
        psi = float(data.get("psi", 0.0))
        tremor = float(data.get("tremor", 0.0))
        error = float(data.get("error", 0.0))
        depth_error = float(data.get("depth_error", 0.0))
        pressure_dev = float(data.get("pressure_dev", 0.0))
        progress = float(data.get("progress", 100))

        reach_dist = data.get("reach_distance")
        reach_err = data.get("reach_error")
        reach_violations = data.get("reach_violations", 0)

        hw_info = ""
        if reach_dist is not None:
            hw_info = (
                f"\n- Arduino Reach Distance: {reach_dist} cm\n"
                f"- Reach Deviation/Error: {reach_err} cm\n"
                f"- Proximity (<10cm) Buzzer Alerts: {reach_violations}"
            )

        input_prompt = (
            f"Review surgical session metrics for user '{user_id}' (mode: {mode}):\n"
            f"- PSI: {psi}\n"
            f"- Path Progress: {progress}%\n"
            f"- Tremor: {tremor}\n"
            f"- Path Deviation Error: {error}\n"
            f"- Depth Error: {depth_error}\n"
            f"- Pressure Deviation: {pressure_dev}"
            f"{hw_info}"
        )

        output_summary = {
            "percentage": analysis.get("percentage", psi),
            "feedback": analysis.get("feedback", []),
            "mistakes": analysis.get("mistakes", []),
            "reach_distance": reach_dist,
            "reach_error": reach_err,
            "reach_violations": reach_violations
        }

        client.trace_llm(
            model="stabil-surgical-analyzer-v1",
            agent_name="stabil-analyzer",
            agent_id="stabil-surgical-analyzer",
            session_id=session_id,
            input_messages=[{"role": "user", "content": input_prompt}],
            output=json.dumps(output_summary),
            latency_ms=latency_ms,
            metadata={
                "user_id": user_id,
                "mode": mode,
                "psi": psi,
                "tremor": tremor,
                "error": error,
                "depth_error": depth_error,
                "pressure_dev": pressure_dev,
                "reach_distance": reach_dist,
                "reach_error": reach_err,
                "reach_violations": reach_violations,
                "hardware_connected": data.get("reach_sensor_connected", False)
            }
        )
    except Exception as e:
        logger.warning(f"PRISMtrace surgical analysis trace error: {e}")


def trace_surgical_recommendation(user_id: str, recommendation: dict, num_sessions: int, latency_ms: int = 20,
                                  hardware_context: Optional[dict] = None, session_id: Optional[str] = None):
    """
    Records training module recommendations into PRISM with relevant hardware context.
    """
    client = get_prism_client()
    if not client:
        return
    try:
        sess_id = session_id or f"recommendation-{user_id}"
        hw_summary = ""
        if hardware_context:
            hw_summary = (
                f"\nHardware & Performance Context:\n"
                f"- Latest PSI: {hardware_context.get('latest_psi')}\n"
                f"- Ultrasonic Reach Distance: {hardware_context.get('latest_reach_distance')} cm "
                f"(avg: {hardware_context.get('avg_reach_distance')} cm)\n"
                f"- Reach Error Variance: {hardware_context.get('reach_error_variance')}\n"
                f"- Recommended Drill: {hardware_context.get('recommended_drill')}"
            )

        input_prompt = (
            f"Generate training recommendation for user '{user_id}' across {num_sessions} completed surgical sessions."
            f"{hw_summary}"
        )

        meta = {
            "user_id": user_id,
            "sessions_evaluated": num_sessions,
            "recommended_mode": recommendation.get("recommended_mode"),
            "recommended_drill": recommendation.get("recommended_mode"),
            "focus_metric": recommendation.get("focus_metric"),
            "trend": recommendation.get("trend"),
            "goal": recommendation.get("goal")
        }
        if hardware_context:
            for k, v in hardware_context.items():
                meta[k] = v

        client.trace_llm(
            model="stabil-recommendation-planner-v1",
            agent_name="stabil-planner",
            agent_id="stabil-surgical-planner",
            session_id=sess_id,
            input_messages=[{"role": "user", "content": input_prompt}],
            output=json.dumps(recommendation),
            latency_ms=latency_ms,
            metadata=meta
        )
    except Exception as e:
        logger.warning(f"PRISMtrace surgical recommendation trace error: {e}")


def trace_psi_prediction(user_id: str, predicted_psi: list, num_sessions: int, latency_ms: int = 15):
    """
    Records future PSI score predictions into PRISM.
    """
    client = get_prism_client()
    if not client:
        return
    try:
        session_id = f"prediction-{user_id}"
        input_prompt = f"Predict future PSI scores for user '{user_id}' based on {num_sessions} historical records."
        client.trace_llm(
            model="stabil-psi-predictor-v1",
            agent_name="stabil-predictor",
            agent_id="stabil-surgical-predictor",
            session_id=session_id,
            input_messages=[{"role": "user", "content": input_prompt}],
            output=json.dumps({"predicted_psi": [float(p) for p in predicted_psi]}),
            latency_ms=latency_ms,
            metadata={
                "user_id": user_id,
                "sessions_evaluated": num_sessions,
                "prediction_count": len(predicted_psi)
            }
        )
    except Exception as e:
        logger.warning(f"PRISMtrace PSI prediction trace error: {e}")


def trace_session_trajectory(session_id: str, user_id: str, mode: str, data: dict, analysis: dict, total_latency_ms: int = 100):
    """
    Submits a structured multi-step surgical evaluation trajectory to PRISM.
    """
    client = get_prism_client()
    if not client:
        return
    try:
        psi = float(data.get("psi", 0.0))
        tremor = float(data.get("tremor", 0.0))
        error = float(data.get("error", 0.0))
        depth_error = float(data.get("depth_error", 0.0))
        pressure_dev = float(data.get("pressure_dev", 0.0))
        reach_dist = data.get("reach_distance")
        reach_err = data.get("reach_error", 0.0)
        reach_violations = data.get("reach_violations", 0)

        steps = [
            {
                "step_type": "tool_call",
                "tool_name": "opencv_spatial_tracker",
                "label": f"3D Vision Trajectory Tracking ({mode})",
                "input_summary": f"Dual camera tracking: mode={mode}, user={user_id}",
                "output_summary": f"Points captured: {len(data.get('trajectory', []))}, raw PSI: {psi}",
                "duration_ms": max(10, int(total_latency_ms * 0.5)),
                "status": "success"
            }
        ]

        if data.get("reach_sensor_connected") or reach_dist is not None:
            steps.append({
                "step_type": "tool_call",
                "tool_name": "arduino_ultrasonic_reach_sensor",
                "label": "Arduino Ultrasonic Reach Telemetry",
                "input_summary": "HC-SR04 ultrasonic distance telemetry stream (9600 baud)",
                "output_summary": (
                    f"Mean reach: {reach_dist} cm, "
                    f"reach deviation: {reach_err} cm, "
                    f"buzzer proximity alerts (<10cm): {reach_violations}"
                ),
                "duration_ms": max(5, int(total_latency_ms * 0.15)),
                "status": "success"
            })

        steps.append({
            "step_type": "reasoning",
            "label": "Psychomotor Variance & Stability Analysis",
            "input_summary": f"Metrics: tremor={tremor}, error={error}, depth_error={depth_error}, pressure={pressure_dev}, reach_error={reach_err}",
            "output_summary": f"Identified mistakes: {', '.join(analysis.get('mistakes', [])) or 'None'}",
            "duration_ms": max(5, int(total_latency_ms * 0.15)),
            "status": "success"
        })

        steps.append({
            "step_type": "final_answer",
            "label": "Surgical Precision Evaluation & Debrief",
            "input_summary": "Certified score calculation",
            "output_summary": f"Final PSI: {psi}, Feedback count: {len(analysis.get('feedback', []))}",
            "duration_ms": max(5, int(total_latency_ms * 0.15)),
            "status": "success"
        })

        client.submit_trajectory(
            steps=steps,
            agent_name="stabil-surgical-evaluator",
            agent_id="stabil-workflow",
            conversation_id=session_id,
            model="stabil-precision-v1",
            final_status="success",
            async_send=True
        )
    except Exception as e:
        logger.warning(f"PRISMtrace trajectory submit error: {e}")
