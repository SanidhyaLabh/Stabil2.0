import cv2
import numpy as np
import socket
from urllib.parse import urlparse

CAM_SRC = 0  # Default to 0 (internal webcam) for TOP view
SIDE_CAM_SRC = 1 # Default to 1 (second webcam) for SIDE view


DEFAULT_TOP_CAM_URL =  "http://192.168.1.3:8080/video"
DEFAULT_SIDE_CAM_URL = "http://10.234.207.98:8080/video"


def format_camera_url(raw_input):
    """
    Formats various camera inputs into a standard URL or device index.
    - Integer / numeric strings (e.g. 0, "0", 1, "1") -> int
    - Raw IP / IP:port (e.g. "192.168.1.5:8080") -> "http://192.168.1.5:8080/video"
    - IP without port (e.g. "192.168.1.5") -> "http://192.168.1.5:8080/video"
    - Standard URLs (e.g. "http://192.168.1.5:8080") -> "http://192.168.1.5:8080/video"
    - URLs with existing stream paths (e.g. "http://.../video", "rtsp://...") -> as-is
    """
    if raw_input is None:
        return None
    if isinstance(raw_input, int):
        return raw_input
    
    val = str(raw_input).strip()
    if not val:
        return None
    
    # Check if integer index (e.g. "0", "1", "2")
    if val.isdigit():
        return int(val)
    
    # Check if already has scheme (http://, https://, rtsp://, etc.)
    if val.startswith("http://") or val.startswith("https://") or val.startswith("rtsp://"):
        parsed = urlparse(val)
        if (val.startswith("http://") or val.startswith("https://")) and (not parsed.path or parsed.path == "/"):
            return val.rstrip("/") + "/video"
        return val
    
    # If raw IP or IP:Port or IP:Port/path
    if "/" in val:
        return f"http://{val}"
    else:
        if ":" in val:
            return f"http://{val}/video"
        else:
            return f"http://{val}:8080/video"


def is_camera_reachable(url_or_index, timeout=0.4):
    if isinstance(url_or_index, int):
        return True
    if not url_or_index:
        return False
    if isinstance(url_or_index, str) and url_or_index.isdigit():
        return True
    
    formatted = format_camera_url(url_or_index)
    if isinstance(formatted, int):
        return True
    if not formatted:
        return False

    try:
        parsed = urlparse(formatted)
        host = parsed.hostname
        port = parsed.port or (443 if parsed.scheme == "https" else 80)
        if not host:
            return False
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(timeout)
        result = s.connect_ex((host, port))
        s.close()
        return result == 0
    except Exception as e:
        print(f"Error checking camera reachability for {url_or_index}: {e}")
        return False


def classify_skill(psi, progress=100):
    if progress < 40 or psi < 30:
        return "Beginner (Incomplete)" if progress < 40 else "Beginner"
    elif psi >= 80 and progress >= 90:
        return "Expert"
    elif psi >= 60 and progress >= 75:
        return "Intermediate"
    else:
        return "Beginner"


def detect_blue_object(frame):
    if frame is None:
        return None, None, None, None

    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    lower_blue = np.array([100, 120, 70])
    upper_blue = np.array([140, 255, 255])
    mask = cv2.inRange(hsv, lower_blue, upper_blue)

    kernel = np.ones((5, 5), np.uint8)
    mask = cv2.erode(mask, kernel, iterations=1)
    mask = cv2.dilate(mask, kernel, iterations=1)

    cnts, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    if len(cnts) > 0:
        c = max(cnts, key=cv2.contourArea)
        ((x, y), radius) = cv2.minEnclosingCircle(c)
        area = cv2.contourArea(c)
        return int(x), int(y), radius, area
    
    return None, None, None, None


def start_tracking(mode, side_cam_url=None, top_cam_url=None):

    simulation_mode = False
    cap = None

    # Initialize Arduino reach sensor session
    try:
        from hardware import get_hardware_reader
        hw_reader = get_hardware_reader()
        hw_reader.start_session()
    except Exception:
        hw_reader = None

    # Format user inputs if supplied
    formatted_top = format_camera_url(top_cam_url)
    formatted_side = format_camera_url(side_cam_url)

    # Determine Top Camera Source
    top_source = CAM_SRC
    if formatted_top is not None:
        top_source = formatted_top
    elif DEFAULT_TOP_CAM_URL and len(DEFAULT_TOP_CAM_URL) > 5:
        top_source = DEFAULT_TOP_CAM_URL

    # Perform fast IP check for top camera
    if isinstance(top_source, str) and top_source.startswith("http"):
        print(f"Checking reachability of Top Camera (IP): {top_source}...")
        if not is_camera_reachable(top_source, timeout=0.4):
            print(f"WARNING: Top Camera IP {top_source} is unreachable. Falling back instantly to local webcam index {CAM_SRC}.")
            top_source = CAM_SRC
        
    cap = cv2.VideoCapture(top_source)
    if cap is not None:
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

    if cap is None or not cap.isOpened():
        print(f"ERROR: Failed to open Top Camera ({top_source})")
        # Try fallback to local CAM_SRC if we hadn't already tried it
        if top_source != CAM_SRC:
            print(f"Retrying Top Camera fallback with index {CAM_SRC}...")
            top_source = CAM_SRC
            cap = cv2.VideoCapture(top_source)
            if cap is not None:
                cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

    if cap is None or not cap.isOpened():
        print("ERROR: Failed to open Top Camera and all fallbacks. Running in forced Simulation Mode.")
        simulation_mode = True
    else:
        print(f"SUCCESS: Top Camera connected ({top_source}).")

    # Determine Side Camera Source logic with fallback
    side_source_primary = None
    if formatted_side is not None:
        side_source_primary = formatted_side
    elif DEFAULT_SIDE_CAM_URL and len(DEFAULT_SIDE_CAM_URL) > 5:
        side_source_primary = DEFAULT_SIDE_CAM_URL

    # Perform fast IP check for side camera
    if side_source_primary and isinstance(side_source_primary, str) and side_source_primary.startswith("http"):
        print(f"Checking reachability of Side Camera (IP): {side_source_primary}...")
        if not is_camera_reachable(side_source_primary, timeout=0.4):
            print(f"WARNING: Side Camera IP {side_source_primary} is unreachable. Skipping primary attempt.")
            side_source_primary = None

    cap_side = None
    
    # Try primary side source (IP or Index) if still set and not in forced simulation
    if not simulation_mode and side_source_primary is not None:
        print(f"Connecting to Side Camera (Primary): {side_source_primary}")
        temp_cap = cv2.VideoCapture(side_source_primary)
        if temp_cap is not None:
            temp_cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            if temp_cap.isOpened():
                cap_side = temp_cap
                print("SUCCESS: Side Camera connected (Primary).")
            else:
                print(f"WARNING: Failed to connect to Side Camera (Primary): {side_source_primary}")
                temp_cap.release()
    
    # Fallback to local index if primary failed or wasn't set and not in simulation
    if not simulation_mode and cap_side is None:
        print(f"Connecting to Side Camera (Fallback): Index {SIDE_CAM_SRC}")
        temp_cap = cv2.VideoCapture(SIDE_CAM_SRC)
        if temp_cap is not None:
            if temp_cap.isOpened():
                cap_side = temp_cap
                print(f"SUCCESS: Side Camera connected (Fallback Index {SIDE_CAM_SRC}).")
            else:
                print(f"WARNING: Failed to connect to Side Camera (Fallback Index {SIDE_CAM_SRC}). Side view disabled.")
                temp_cap.release()

    tremor = []
    errors = []
    depth_values = []
    pressure_values = []
    trajectory = []
    prev = None

    restricted_hits = 0
    stitch_scores = []
    targeting_errors = []

    # ==========================================
    # PATH CHECKPOINTS & PROGRESS INITIALIZATION
    # ==========================================
    w, h = 640, 480
    brain_path = np.array([[80, 300], [200, 180], [350, 260], [520, 160]], dtype=np.int32)

    path_checkpoints = []
    checkpoint_tolerance = 24
    is_path_mode = True
    circle_direction = None

    if mode == "line":
        # Discretize straight line from x=50 to x=590 along y=240
        num_pts = 80
        path_checkpoints = [(int(50 + (590 - 50) * i / (num_pts - 1)), 240) for i in range(num_pts)]
        checkpoint_tolerance = 24
    elif mode == "circle":
        # 80 checkpoints around circle of radius 100
        num_pts = 80
        cx, cy, r = w // 2, h // 2, 100
        # Start at 3 o'clock: (cx + r, cy) = (420, 240)
        path_checkpoints = [(int(cx + r * np.cos(2 * np.pi * i / num_pts)), 
                             int(cy + r * np.sin(2 * np.pi * i / num_pts))) for i in range(num_pts)]
        checkpoint_tolerance = 24
    elif mode == "brain":
        # Discretize piecewise linear path across all 3 segments
        path_checkpoints = []
        segs = [
            (brain_path[0], brain_path[1], 26),
            (brain_path[1], brain_path[2], 26),
            (brain_path[2], brain_path[3], 28)
        ]
        for p1, p2, count in segs:
            for i in range(count):
                frac = i / float(count)
                px = int(p1[0] + (p2[0] - p1[0]) * frac)
                py = int(p1[1] + (p2[1] - p1[1]) * frac)
                path_checkpoints.append((px, py))
        path_checkpoints.append((int(brain_path[-1][0]), int(brain_path[-1][1])))
        checkpoint_tolerance = 26
    elif mode == "suturing":
        # Suture line path from left (100) to right (540)
        num_pts = 70
        path_checkpoints = [(int(100 + (540 - 100) * i / (num_pts - 1)), 250) for i in range(num_pts)]
        checkpoint_tolerance = 36 # Accommodates vertical stitch oscillation
    elif mode == "needle_target":
        is_path_mode = False
        target_hold_frames = 0
        required_hold_frames = 90
    elif mode == "micro":
        is_path_mode = False
        target_hold_frames = 0
        required_hold_frames = 120
    elif mode == "depth_drill":
        is_path_mode = False
        target_hold_frames = 0
        required_hold_frames = 120
    else:
        num_pts = 80
        path_checkpoints = [(int(50 + (590 - 50) * i / (num_pts - 1)), 240) for i in range(num_pts)]
        checkpoint_tolerance = 24

    progress_idx = 0
    total_checkpoints = len(path_checkpoints) if is_path_mode else 100
    progress_percent = 0

    sim_step = 0
    while True:

        if simulation_mode:
            # Create a blank dark gray frame
            frame = np.zeros((480, 640, 3), dtype=np.uint8)
            frame[:, :] = (30, 30, 30) # Dark gray background
            h, w, _ = frame.shape
            ret = True
        else:
            ret, frame = cap.read()
            if not ret:
                continue

            frame = cv2.resize(frame, (640, 480))
            frame = cv2.flip(frame, 1)
            h, w, _ = frame.shape

        z_val = None
        if simulation_mode:
            sim_step += 1
            sim_t = min(1.0, sim_step / 200.0)
            
            # Simulate a target and tool motion moving along the actual path
            if mode == "line":
                x_target = 50 + sim_t * 540
                y_target = 240
                tremor_x = np.sin(sim_step * 0.8) * 1.8 + np.random.normal(0, 0.4)
                tremor_y = np.cos(sim_step * 0.7) * 2.2 + np.random.normal(0, 0.4)
                deviation_y = np.sin(sim_step * 0.05) * 4.0
                x = int(x_target + tremor_x)
                y = int(y_target + tremor_y + deviation_y)
                radius = 20 + np.sin(sim_step * 0.1) * 1.5
                area = np.pi * radius * radius
                z_val = int(240 + np.sin(sim_step * 0.05) * 40)
            elif mode == "circle":
                angle = sim_t * 2 * np.pi
                x_target = w // 2 + 100 * np.cos(angle)
                y_target = h // 2 + 100 * np.sin(angle)
                tremor_x = np.sin(sim_step * 0.8) * 1.5 + np.random.normal(0, 0.4)
                tremor_y = np.cos(sim_step * 0.7) * 1.5 + np.random.normal(0, 0.4)
                x = int(x_target + tremor_x)
                y = int(y_target + tremor_y)
                radius = 20 + np.sin(sim_step * 0.1) * 1.5
                area = np.pi * radius * radius
                z_val = int(240 + np.cos(sim_step * 0.05) * 40)
            elif mode == "brain":
                segment_t = sim_t * 3.0
                idx = min(int(segment_t), 2)
                local_t = segment_t - idx
                pt1 = brain_path[idx]
                pt2 = brain_path[idx+1]
                x_target = pt1[0] + (pt2[0] - pt1[0]) * local_t
                y_target = pt1[1] + (pt2[1] - pt1[1]) * local_t
                tremor_x = np.sin(sim_step * 0.8) * 1.5 + np.random.normal(0, 0.4)
                tremor_y = np.cos(sim_step * 0.7) * 1.5 + np.random.normal(0, 0.4)
                x = int(x_target + tremor_x)
                y = int(y_target + tremor_y)
                radius = 20
                area = np.pi * radius * radius
                z_val = int(240 + np.sin(sim_step * 0.05) * 30)
            elif mode == "suturing":
                x_target = 100 + sim_t * 440
                y_target = 250 + np.sin(sim_step * 0.2) * 20
                tremor_x = np.sin(sim_step * 0.8) * 1.0 + np.random.normal(0, 0.3)
                tremor_y = np.cos(sim_step * 0.7) * 1.0 + np.random.normal(0, 0.3)
                x = int(x_target + tremor_x)
                y = int(y_target + tremor_y)
                radius = 20
                area = np.pi * radius * radius
                z_val = int(240 + np.sin(sim_step * 0.1) * 20)
            elif mode == "depth_drill":
                x = int(w // 2 + np.sin(sim_step * 0.03) * 60)
                y = int(h // 2 + np.cos(sim_step * 0.03) * 60)
                radius = 25 + np.sin(sim_step * 0.07) * 10
                area = np.pi * radius * radius
                z_val = int(240 + np.sin(sim_step * 0.07) * 50)
            elif mode == "needle_target":
                dist_t = max(0.0, 1.0 - sim_t * 1.5)
                x_target = w // 2 + dist_t * 150 * np.cos(sim_step * 0.05)
                y_target = h // 2 + dist_t * 150 * np.sin(sim_step * 0.05)
                tremor_x = np.sin(sim_step * 0.8) * 1.0 + np.random.normal(0, 0.3)
                tremor_y = np.cos(sim_step * 0.7) * 1.0 + np.random.normal(0, 0.3)
                x = int(x_target + tremor_x)
                y = int(y_target + tremor_y)
                radius = 18
                area = np.pi * radius * radius
                z_val = int(240)
            else:
                x = int(w // 2 + np.sin(sim_step * 0.5) * 5)
                y = int(h // 2 + np.cos(sim_step * 0.5) * 5)
                radius = 20
                area = np.pi * radius * radius
                z_val = int(240)

            # Draw side view simulation
            frame_side = np.zeros((480, 640, 3), dtype=np.uint8)
            frame_side[:, :] = (30, 30, 30)
            sx, sy = z_val, 240
            cv2.circle(frame_side, (sx, sy), 5, (0, 255, 255), -1)
            cv2.putText(frame_side, f"Z: {sx} (SIM)", (10, 50), 
                        cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
            cv2.putText(frame_side, "DEMO MODE: Side View", (10, 430), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 1)
            cv2.imshow("Side View (Z-Axis)", frame_side)
        else:
            x, y, radius, area = detect_blue_object(frame)
            if cap_side:
                ret_side, frame_side = cap_side.read()
                if ret_side:
                    frame_side = cv2.resize(frame_side, (640, 480))
                    sx, sy, sr, sa = detect_blue_object(frame_side)
                    if sx is not None:
                        z_val = sx
                        cv2.circle(frame_side, (sx, sy), 5, (0, 255, 255), -1)
                        cv2.putText(frame_side, f"Z: {sx}", (10, 50), 
                                    cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
                    cv2.imshow("Side View (Z-Axis)", frame_side)

        # ==========================================
        # DRAW TEMPLATE PATHS & TRACED OVERLAYS
        # ==========================================

        if mode == "line":
            # Target Path (Base Guide in dark green)
            cv2.line(frame, (50, 240), (w - 50, 240), (0, 160, 0), 2)
            
            # Start/End Markers
            cv2.circle(frame, (50, 240), 10, (0, 255, 0), -1) # Green Start
            cv2.putText(frame, "START", (40, 220), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
            
            cv2.circle(frame, (w - 50, 240), 10, (0, 0, 255), -1) # Red End
            cv2.putText(frame, "END", (w - 70, 220), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)

            # Highlight Traced Line in Vibrant Sky-Blue
            if progress_idx > 0 and len(path_checkpoints) > 0:
                last_idx = min(progress_idx - 1, total_checkpoints - 1)
                cv2.line(frame, path_checkpoints[0], path_checkpoints[last_idx], (255, 230, 0), 4)

        elif mode == "circle":
            # Base circle guide
            cv2.circle(frame, (w // 2, h // 2), 100, (0, 160, 0), 2)
            
            # Start at 3 o'clock position
            sx, sy = w // 2 + 100, h // 2
            cv2.circle(frame, (sx, sy), 10, (0, 255, 0), -1)
            cv2.putText(frame, "START/END", (sx + 15, sy), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 2)

            # Highlight Traced Arc in Vibrant Sky-Blue
            if progress_idx > 1 and len(path_checkpoints) > 0:
                for cp_i in range(1, min(progress_idx, total_checkpoints)):
                    cv2.line(frame, path_checkpoints[cp_i - 1], path_checkpoints[cp_i], (255, 230, 0), 4)

        elif mode == "micro":
            cv2.circle(frame, (w // 2, h // 2), 40, (0, 255, 0), 2)
            cv2.putText(frame, "STEADY TARGET ZONE", (w // 2 - 90, h // 2 - 50), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)

        elif mode == "brain":
            cv2.polylines(frame, [brain_path], False, (0, 160, 0), 2)

            # Start/End from path
            bsx, bsy = brain_path[0]
            bex, bey = brain_path[-1]
            
            cv2.circle(frame, (bsx, bsy), 8, (0, 255, 0), -1)
            cv2.putText(frame, "START", (bsx - 20, bsy - 15), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
            
            cv2.circle(frame, (bex, bey), 8, (0, 0, 255), -1)
            cv2.putText(frame, "END", (bex + 10, bey), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)

            # Restricted zone
            rx1, ry1 = 300, 130
            rx2, ry2 = 420, 240
            cv2.rectangle(frame, (rx1, ry1), (rx2, ry2), (0, 0, 255), 2)
            cv2.putText(frame, "Restricted Zone", (rx1, ry1 - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)

            # Highlight Traced Segments in Vibrant Sky-Blue
            if progress_idx > 1 and len(path_checkpoints) > 0:
                for cp_i in range(1, min(progress_idx, total_checkpoints)):
                    cv2.line(frame, path_checkpoints[cp_i - 1], path_checkpoints[cp_i], (255, 230, 0), 4)

        elif mode == "angle":
            cv2.rectangle(frame, (w // 2 - 60, 200), (w // 2 + 60, 300), (255, 0, 0), 2)

        elif mode == "suturing":
            # Draw incision boundaries
            cv2.line(frame, (100, 220), (540, 220), (0, 160, 0), 2)
            cv2.line(frame, (100, 280), (540, 280), (0, 160, 0), 2)
            
            # Start/End for suture
            cv2.circle(frame, (100, 250), 8, (0, 255, 0), -1)
            cv2.putText(frame, "START", (80, 200), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
            
            cv2.circle(frame, (540, 250), 8, (0, 0, 255), -1)
            cv2.putText(frame, "END", (530, 200), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)

            # Draw stitch tick marks
            for sx_pt in range(130, 520, 60):
                cv2.line(frame, (sx_pt, 215), (sx_pt, 285), (0, 200, 100), 1)

            # Highlight Traced Suture Line in Vibrant Sky-Blue
            if progress_idx > 1 and len(path_checkpoints) > 0:
                for cp_i in range(1, min(progress_idx, total_checkpoints)):
                    cv2.line(frame, path_checkpoints[cp_i - 1], path_checkpoints[cp_i], (255, 230, 0), 4)

        elif mode == "depth_drill":
            cv2.putText(frame, "Maintain Depth Zone",
                        (180, 40),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.7, (0, 255, 0), 2)

        elif mode == "needle_target":
            cv2.circle(frame, (w // 2, h // 2), 16, (0, 255, 0), 2)
            cv2.circle(frame, (w // 2, h // 2), 6, (0, 255, 0), -1)
            cv2.putText(frame, "TARGET", (w // 2 - 30, h // 2 - 25), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)

        # Draw Active Waypoint Target Circle
        if is_path_mode and progress_idx < total_checkpoints:
            next_target = path_checkpoints[progress_idx]
            cv2.circle(frame, next_target, 7, (0, 255, 255), 2)
            if progress_idx == 0:
                cv2.putText(frame, "START HERE", (next_target[0] - 35, next_target[1] - 15), 
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 2)

        if x is not None and radius > 5:

            # =====================
            # REAL-TIME METRICS
            # =====================
            
            # Tremor (Instantaneous)
            instant_tremor = 0
            if prev is not None:
                instant_tremor = np.linalg.norm(np.array([x, y]) - np.array(prev))
                tremor.append(instant_tremor)
            prev = (x, y)

            # Error (Instantaneous)
            instant_error = 0
            if mode == "line":
                instant_error = abs(y - 240)
            elif mode == "circle":
                instant_error = abs(np.sqrt((x - w // 2) ** 2 + (y - h // 2) ** 2) - 100)
            elif mode == "brain":
                dist = cv2.pointPolygonTest(brain_path, (x, y), True)
                instant_error = max(0, abs(dist) - 15) # 15 is tolerance
            elif mode == "suturing":
                instant_error = abs(y - 250)
            elif mode == "needle_target":
                instant_error = np.sqrt((x - w // 2) ** 2 + (y - h // 2) ** 2)
            
            errors.append(instant_error)

            # Depth
            if z_val is not None:
                depth_values.append(z_val)
            else:
                depth_values.append(radius)

            # Pressure
            pressure_values.append(area / 500.0)

            # =====================
            # DYNAMIC FEEDBACK
            # =====================
            
            # Color logic: Green (Good), Red (Bad)
            color = (0, 255, 0) # Green
            warning_text = ""
            
            if instant_tremor > 15:
                color = (0, 0, 255) # Red
                warning_text = "HIGH TREMOR!"
            elif instant_error > 25:
                color = (0, 0, 255) # Red
                warning_text = "OFF PATH!"
            elif mode == "brain" and (300 < x < 420) and (130 < y < 240):
                color = (0, 0, 255)
                warning_text = "RESTRICTED AREA!"

            # Store (x, y, z, color)
            current_z = z_val if z_val is not None else radius
            trajectory.append((x, y, current_z, color))

            # Draw Trajectory with dynamic colors
            if len(trajectory) > 1:
                for i in range(1, len(trajectory)):
                    pt1 = trajectory[i-1][:2]
                    pt2 = trajectory[i][:2]
                    seg_color = trajectory[i][3]
                    cv2.line(frame, pt1, pt2, seg_color, 2)
            
            # Draw Warning
            if warning_text:
                cv2.putText(frame, warning_text, (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 
                            1, (0, 0, 255), 3)

            # ==========================================
            # PATH TRACING PROGRESS LOGIC
            # ==========================================

            if is_path_mode and total_checkpoints > 0:
                # Handle circle tracing direction (CW or CCW) on start
                if mode == "circle" and circle_direction is None and progress_idx == 0:
                    cx, cy, r = w // 2, h // 2, 100
                    ccw_first = (int(cx + r * np.cos(-2 * np.pi / num_pts)), int(cy + r * np.sin(-2 * np.pi / num_pts)))
                    cw_first = path_checkpoints[1]
                    dist_ccw = np.hypot(x - ccw_first[0], y - ccw_first[1])
                    dist_cw = np.hypot(x - cw_first[0], y - cw_first[1])
                    if dist_ccw < checkpoint_tolerance and dist_ccw < dist_cw:
                        circle_direction = 'ccw'
                        path_checkpoints = [(int(cx + r * np.cos(-2 * np.pi * i / num_pts)), 
                                             int(cy + r * np.sin(-2 * np.pi * i / num_pts))) for i in range(num_pts)]

                # Check strictly immediate next waypoint (max lookahead 2 to prevent point dwell jumping)
                lookahead = min(progress_idx + 2, total_checkpoints)
                for next_i in range(progress_idx, lookahead):
                    tgt_x, tgt_y = path_checkpoints[next_i]
                    dist_to_cp = np.hypot(x - tgt_x, y - tgt_y)
                    if dist_to_cp <= checkpoint_tolerance:
                        progress_idx = next_i + 1
                        break

                if mode == "brain":
                    if (300 < x < 420) and (130 < y < 240):
                        restricted_hits += 1

                elif mode == "suturing":
                    stitch_spacing = abs((x % 60) - 30)
                    stitch_scores.append(stitch_spacing)

                progress_percent = int((progress_idx / total_checkpoints) * 100)

            else:
                # Target Hold & Stability Modes
                if mode == "needle_target":
                    targeting_errors.append(instant_error)
                    if instant_error < 20 and instant_tremor < 15:
                        target_hold_frames += 1
                    progress_percent = min(100, int((target_hold_frames / required_hold_frames) * 100))

                elif mode == "micro":
                    dist_to_center = np.hypot(x - w // 2, y - h // 2)
                    if dist_to_center < 40 and instant_tremor < 12:
                        target_hold_frames += 1
                    progress_percent = min(100, int((target_hold_frames / required_hold_frames) * 100))

                elif mode == "depth_drill":
                    if 15 < radius < 40:
                        target_hold_frames += 1
                    progress_percent = min(100, int((target_hold_frames / required_hold_frames) * 100))

            cv2.circle(frame, (x, y), 6, color, -1)

        # Draw HUD / Progress Bar
        bar_width = int((progress_percent / 100.0) * w)
        cv2.rectangle(frame, (0, h - 22), (bar_width, h), (0, 255, 0), -1)
        cv2.rectangle(frame, (0, h - 22), (w, h), (120, 120, 120), 1)

        if is_path_mode:
            if progress_idx == 0:
                status_guide = "Start: Move tool to GREEN START marker"
            else:
                status_guide = f"Trace Path: {progress_percent}% ({progress_idx}/{total_checkpoints} pts)"
        else:
            status_guide = f"Hold Stability: {progress_percent}%"

        cv2.putText(frame, status_guide, 
                    (10, h - 30), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 255, 0), 2)

        # Draw Simulation Mode status on HUD
        if simulation_mode:
            cv2.putText(frame, "SIMULATION MODE ACTIVE", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 0, 255), 2)
            cv2.putText(frame, "Press 's' to switch to webcam", (10, h - 55), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 0), 1)
        else:
            cv2.putText(frame, "WEBCAM ACTIVE", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            cv2.putText(frame, "Press 's' to switch to simulation", (10, h - 55), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 0), 1)

        cv2.imshow("AI Surgical Trainer", frame)

        if progress_percent >= 100:
            break

        key = cv2.waitKey(1) & 0xFF
        if key == 27:
            break
        elif key == ord('s'):
            simulation_mode = not simulation_mode
            print(f"Simulation mode toggled: {simulation_mode}")

    if cap:
        cap.release()
    if cap_side:
        cap_side.release()
    cv2.destroyAllWindows()

    # Collect Arduino reach sensor metrics
    if hw_reader:
        hw_reader.stop_session()
        hw_metrics = hw_reader.get_session_metrics()
    else:
        hw_metrics = {
            "reach_distance": None,
            "reach_error": 0.0,
            "min_reach": None,
            "max_reach": None,
            "reach_violations": 0,
            "reach_samples": 0,
            "reach_sensor_connected": False
        }

    # METRIC CALCULATION

    tremor_score = float(np.std(tremor)) if len(tremor) > 5 else 0.0
    error_score = float(np.mean(errors)) if len(errors) > 5 else 0.0
    depth_error = float(np.std(depth_values)) if len(depth_values) > 5 else 0.0
    pressure_dev = float(np.std(pressure_values)) if len(pressure_values) > 5 else 0.0
    over_pen = sum(p > 1.3 for p in pressure_values)

    stitch_accuracy = 100 - np.mean(stitch_scores) if stitch_scores else None
    targeting_accuracy = 100 - np.mean(targeting_errors) if targeting_errors else None
    depth_variation_index = depth_error if mode == "depth_drill" else None

    # Base Dexterity Quality Score (evaluates tremor, path precision, depth consistency)
    tremor_penalty = min(35.0, tremor_score * 2.0)
    error_penalty = min(35.0, error_score * 1.2)
    depth_penalty = min(15.0, depth_error * 1.0)
    pressure_penalty = min(10.0, pressure_dev * 6.0)
    restricted_penalty = min(20.0, restricted_hits * 2.0)

    # Hardware Ultrasonic Reach penalty (if sensor connected and gathered readings)
    reach_penalty = 0.0
    if hw_metrics.get("reach_sensor_connected") and hw_metrics.get("reach_samples", 0) > 0:
        r_err = hw_metrics.get("reach_error", 0.0)
        r_viol = hw_metrics.get("reach_violations", 0)
        reach_penalty = min(15.0, r_err * 1.2 + r_viol * 2.5)

    dexterity_score = 100.0 - (tremor_penalty + error_penalty + depth_penalty + pressure_penalty + restricted_penalty + reach_penalty)
    dexterity_score = max(0.0, min(100.0, dexterity_score))

    # Overall PSI is scaled strictly by path completion rate:
    # 0% completion = 0.0 PSI score
    completion_ratio = progress_percent / 100.0
    if progress_percent <= 0 or len(trajectory) < 5:
        psi = 0.0
    else:
        psi = dexterity_score * completion_ratio

    psi = round(max(0.0, min(100.0, psi)), 2)

    result = {
        "psi": psi,
        "progress": progress_percent,
        "tremor": round(tremor_score, 2),
        "error": round(error_score, 2),
        "depth_error": round(depth_error, 2),
        "pressure_dev": round(pressure_dev, 2),
        "over_pen": over_pen,
        "skill": classify_skill(psi, progress_percent),
        "mode": mode,
        "trajectory": trajectory,
        "reach_distance": hw_metrics.get("reach_distance"),
        "reach_error": hw_metrics.get("reach_error", 0.0),
        "min_reach": hw_metrics.get("min_reach"),
        "max_reach": hw_metrics.get("max_reach"),
        "reach_violations": hw_metrics.get("reach_violations", 0),
        "reach_samples": hw_metrics.get("reach_samples", 0),
        "reach_sensor_connected": hw_metrics.get("reach_sensor_connected", False)
    }

    if stitch_accuracy is not None:
        result["stitch_accuracy"] = round(stitch_accuracy, 2)

    if targeting_accuracy is not None:
        result["targeting_accuracy"] = round(targeting_accuracy, 2)

    if depth_variation_index is not None:
        result["depth_variation_index"] = round(depth_variation_index, 2)

    return result