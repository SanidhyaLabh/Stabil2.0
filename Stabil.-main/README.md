# Stabil – AI Surgical Precision Trainer

Stabil is an AI-powered surgical hand precision evaluation system that leverages real-time computer vision to objectively track, measure, and analyze surgical tool movements. By utilizing dual webcams (top and side views), the system evaluates vital psychomotor metrics to compute a comprehensive Precision Score Index (PSI).

**Website** : https://stabil-1.netlify.app/ 

## Key Features

*   **Real-time Trajectory Tracking**: Uses OpenCV to accurately trace the surgeon's tool in 3D space, capturing X, Y, and Z (depth) coordinates.
*   **Multiple Training Modules**: Includes various simulated surgical exercises such as Line tracking, Circle navigation, intricate Brain path navigation, Suturing, Depth Drills, and Needle Targeting.
*   **Objective Metrics Tracking**: 
    *   **Tremor Detection**: Measures instantaneous deviations in hand stability.
    *   **Path Deviation**: Calculates off-path errors against predefined optimal trajectories.
    *   **Depth Control**: Evaluates performance on the Z-axis to prevent over-penetration or shallow incisions.
    *   **Pressure Deviation**: Approximates applied tool pressure based on object contour area tracking.
*   **Precision Score Index (PSI)**: A custom algorithm that synthesizes all metrics into a single skill classification (Beginner, Intermediate, Expert).
*   **Analytics Dashboard**: Visualizes progress trends across sessions with predictive models forecasting future performance.
*   **Heatmap Replay**: Post-session debriefing tool to review the physical trajectory and identified error zones visually.

## Technology Stack

*   **Backend framework**: Python, Flask
*   **Computer Vision**: OpenCV (`cv2`)
*   **Database**: SQLite (`stabil.db`) for robust session data persistence
*   **Data Analysis**: Data tracking using NumPy for complex spatial calculations
*   **Frontend**: HTML5, CSS3, JavaScript (with Flask Jinja2 Templating)

## Setup and Installation

1. **Working Directory Update**:
   Ensure you are in the `Stabil-main` directory.

2. **Set up a Virtual Environment** (Optional but recommended):
   ```bash
   python -m venv venv
   # On Windows powershell:
   .\venv\Scripts\activate
   ```

3. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Camera Setup**:
   The application fundamentally leverages a multi-camera pipeline. 
   Configure your IP camera feeds or local webcams in `tracker.py` (Lines 8-9):
   *   `DEFAULT_TOP_CAM_URL`: Main top-down view.
   *   `DEFAULT_SIDE_CAM_URL`: Secondary side view used for accurate Z-depth tracking.
   *(Fallback to generic local cameras `CAM_SRC = 0` and `SIDE_CAM_SRC = 1` is natively supported if IP cameras fail)*

5. **Run the Application**:
   ```bash
   python app.py
   ```
   The application will start locally at `http://127.0.0.1:5000/`.

## Architecture Overview

*   **`tracker.py`**: The core OpenCV loop processing the video feeds. It executes HSV color-space masking (configured for blue surgical markers) and calculates the real-time arrays of trajectory metrics.
*   **`app.py`**: The Flask application entry point managing all routing for the Training modules, Dashboard, Heatmaps, and User Progress.
*   **`database.py`**: Handles SQLite abstractions to seamlessly save and retrieve large session JSON matrices.
*   **`analysis.py` & `predictor.py`**: Submodules dedicated to parsing recent metadata to recommend targeted training modalities and predict future PSI trajectory.

**Drive Link for the Project Overview and Aim :**
https://drive.google.com/file/d/1fysmBcvuakcVgIWNuYiL-kFiY1bhs41D/view?usp=sharing
