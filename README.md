# Stabil 2.0 – AI Surgical Precision & Dexterity Trainer

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Backend-Flask-green.svg)](https://flask.palletsprojects.com/)
[![OpenCV](https://img.shields.io/badge/Vision-OpenCV-red.svg)](https://opencv.org/)
[![Hardware](https://img.shields.io/badge/Hardware-Arduino%20Ultrasonic%20%2B%20Buzzer-teal.svg)](https://www.arduino.cc/)
[![Observability](https://img.shields.io/badge/Observability-PRISM%20AI%20Tracing-purple.svg)](https://prism-api-prod.up.railway.app)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

**Stabil 2.0** is an AI-powered surgical hand precision training and psychomotor evaluation platform. By combining real-time multi-angle computer vision, physical Arduino ultrasonic telemetry, and clinical AI evaluation agents, Stabil objectively evaluates surgical movements and coaches trainees toward clinical competency.

---

## System Architecture & Workflow

```
                        STABIL 2.0
                            │
               ┌────────────┴────────────┐
               ↓                         ↓
    Dual-Camera Computer Vision       Arduino Hardware
    (Top 2D Path + Side Depth)    (Ultrasonic Reach + Buzzer)
               │                         │
               └────────────┬────────────┘
                            ↓
                    Performance Metrics
          (Tremor, Path Deviation, Depth, Pressure, Reach)
                            ↓
                 Precision Score Index (PSI)
                            ↓
                   AI Surgical Evaluator
               (Clinical Feedback & Mistakes)
                            ↓
                 AI Curriculum Planner
              (Adaptive Drill Recommendation)
                            ↓
                  PRISM AI Observability
             (Live Trace, Latency & Auditing)
```

---

## Key Features

### 1. Dual-Camera Spatial 3D Tracking
* **Overhead View (Top Camera):** Real-time optical trajectory tracking mapping tool coordinates against optimal surgical paths (Line, Circle, Incision, Suturing, Brain Path).
* **Profile View (Side Camera):** Depth penetration (Z-axis) monitoring and simulated tissue pressure approximation based on tool contour dynamics.
* **Micro-Tremor Extraction:** Isolates physiological tremor and involuntary hand vibrations from intentional surgical motions.

### 2. Physical Arduino Reach & Proximity Guard
* **Ultrasonic Distance Telemetry:** Streams surgeon working distance in real-time (`DIST: <cm>`) over USB serial.
* **10cm Proximity Safety Buzzer:** Emits real-time auditory buzzer warnings whenever the surgeon's hand or instrument breaches the restricted operating threshold (<10 cm).
* **Ergonomic Stability Metric:** Calculates standard deviation in working distance to penalize erratic posture shifts.

### 3. Precision Score Index (PSI)
A clinically calibrated metric (0–100%) synthesizing:
* Path Deviation Error
* Hand Tremor Amplitude
* Penetration Depth Variance
* Pressure Stability
* Ultrasonic Proximity Violations & Reach Error
* Path Completion Ratio

### 4. AI Clinical Evaluators & Adaptive Planning
* **AI Surgical Evaluator (`stabil-surgical-analyzer-v1`):** Generates structured mistake logs and constructive clinical debriefs.
* **Adaptive Drill Planner (`stabil-recommendation-planner-v1`):** Analyzes multi-session variance to prescribe targeted drills tailored to fix the trainee's primary weakness.
* **ML Learning Curve Predictor (`stabil-psi-predictor-v1`):** Forecasts competency progression over the next 5 sessions using regression modeling.

### 5. PRISM AI Observability & Safety Auditing
* **Live AI Traces:** Captures full prompt inputs, AI feedback outputs, execution duration, and session trajectories into the PRISM observability platform.
* **Safety & Compliance:** Audits AI clinical feedback for hallucinations, adherence to surgical training guidelines, and response latency.
* **Dataset Flywheel:** One-click export of verified surgeon sessions to train and fine-tune next-generation surgical foundation models.

---

## Project Structure

```
Stabil.-main/
├── app.py                  # Flask backend routes & API controllers
├── tracker.py              # Real-time OpenCV dual-camera tracking engine
├── hardware.py             # Arduino serial interface & ultrasonic telemetry
├── analysis.py             # Surgical evaluation & mistake classification
├── planner.py              # Adaptive curriculum recommendation engine
├── predictor.py            # Predictive PSI learning curve modeling
├── prism_client.py         # PRISM AI tracing & observability client
├── database.py             # SQLite persistence layer (stabil.db)
├── heatmap.py              # Spatial trajectory error heatmap generator
├── templates/              # Jinja2 web interface templates
│   ├── index.html          # Main landing dashboard
│   ├── train.html          # Interactive surgical training interface
│   └── result.html         # Post-procedure score card & analytics
├── static/                 # Stylesheets, diagrams, and assets
└── requirements.txt        # Python dependency manifest
```

---

## Setup & Installation

### 1. Prerequisites
* Python 3.10 or higher
* Dual Webcams or IP Webcam streaming apps (e.g. smartphone IP cameras)
* *(Optional)* Arduino Uno / Nano with HC-SR04 ultrasonic sensor and buzzer

### 2. Clone the Repository
```bash
git clone https://github.com/SanidhyaLabh/Stabil2.0.git
cd Stabil2.0
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables
Create a `.env` file in the root directory (or copy from `.env.example`):
```env
# PRISM Live Tracing Configuration
PRISMTRACE_API_KEY=pt-sk-your-prism-api-key
PRISMTRACE_PROJECT_ID=your-project-id
PRISMTRACE_HOST=https://prism-api-prod.up.railway.app

# Optional Hardware Serial Port (auto-detected if blank, e.g. COM3, COM4, /dev/ttyUSB0)
ARDUINO_PORT=COM3
```

### 5. Camera Configuration
Adjust default camera sources in `tracker.py` if using specific network streams:
* `DEFAULT_TOP_CAM_URL`: Overhead IP camera feed (e.g., `http://192.168.1.100:8080/video`)
* `DEFAULT_SIDE_CAM_URL`: Profile IP camera feed
* *Note: The system automatically falls back to local USB webcams (`CAM_SRC = 0`) or simulation mode if no IP camera is reachable.*

### 6. Run the Application
```bash
python app.py
```
Open your browser and navigate to **`http://localhost:5000`**.

---

## Live Demo & Documentation
* **Web App:** [https://stabil-1.netlify.app/](https://stabil-1.netlify.app/)
* **Project Documentation & Overview:** [Google Drive Documentation](https://drive.google.com/file/d/1fysmBcvuakcVgIWNuYiL-kFiY1bhs41D/view?usp=sharing)

---

## License
Distributed under the MIT License. See [LICENSE](LICENSE) for more information.
