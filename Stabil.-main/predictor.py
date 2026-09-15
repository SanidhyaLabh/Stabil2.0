import time
import numpy as np
from database import get_all_sessions

try:
    from prism_client import trace_psi_prediction
except ImportError:
    trace_psi_prediction = None


def predict_next_psi(user_id="default", num_sessions=5):
    start_time = time.time()
    sessions = get_all_sessions(user_id)

    if len(sessions) < 3:
        if trace_psi_prediction:
            latency_ms = max(1, int((time.time() - start_time) * 1000))
            trace_psi_prediction(user_id, [], len(sessions), latency_ms)
        return []

    psi = np.array([float(s["psi"]) for s in sessions])
    x = np.arange(len(psi))

    if len(sessions) > 1:
        slope, intercept = np.polyfit(x, psi, 1)
        
        future_x = np.arange(len(psi), len(psi) + num_sessions)
        predicted_psi = slope * future_x + intercept
        
        # Clamp between 0 and 100
        predicted_psi = np.clip(predicted_psi, 0, 100)
        
        result = [round(float(p), 1) for p in predicted_psi]
        if trace_psi_prediction:
            latency_ms = max(1, int((time.time() - start_time) * 1000))
            trace_psi_prediction(user_id, result, len(sessions), latency_ms)
        return result
    
    return []
