def analyze_session(data):

    feedback = []
    mistakes = []

    psi = data.get("psi", 0.0)
    progress = data.get("progress", 100)

    # Incomplete path analysis
    if progress < 100:
        mistakes.append(f"Incomplete procedure: Only {progress}% of path was completed.")
        feedback.append(f"Session finished with {progress}% path completion. Trace the full trajectory from START to END for full certification.")

    # Tremor analysis
    if data.get("tremor", 0) > 5:
        feedback.append("Reduce hand tremor. Practice slow steady movements.")
        mistakes.append("High tremor detected")

    # Path deviation
    if data.get("error", 0) > 30:
        feedback.append("Improve trajectory accuracy. Stay centered on the green guide line.")
        mistakes.append("High path deviation")

    # Depth control
    if data.get("depth_error", 0) > 8:
        feedback.append("Maintain consistent penetration depth.")
        mistakes.append("Depth instability")

    # Pressure control
    if data.get("pressure_dev", 0) > 1:
        feedback.append("Apply uniform pressure while tracing.")
        mistakes.append("Pressure variation")

    # Ultrasonic Reach Sensor feedback
    reach_dist = data.get("reach_distance")
    reach_err = data.get("reach_error", 0.0)
    reach_violations = data.get("reach_violations", 0)

    if reach_violations > 0:
        mistakes.append(f"Proximity boundary violation: Hand breached <10cm buzzer threshold {reach_violations} time(s).")
        feedback.append(f"Avoid over-reaching into surgical area. Proximity buzzer triggered ({reach_violations} alert(s)). Keep hand at safe reach distance.")
    elif reach_dist is not None and reach_err > 4.0:
        mistakes.append("High reach distance instability")
        feedback.append(f"Stabilize operating reach distance (ultrasonic deviation: +/-{reach_err} cm). Practice steady positioning.")

    if not feedback:
        feedback.append("Excellent surgical control. Maintain consistency.")

    return {
        "percentage": psi,
        "feedback": feedback,
        "mistakes": mistakes
    }
