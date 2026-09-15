#!/usr/bin/env python3
"""
STABIL - Unified Fullstack Runner & Deployment Script
Supports 1-click execution for development, production, and container deployments.
"""

import os
import sys
import subprocess
import argparse
import webbrowser
import time

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FRONTEND_DIR = os.path.join(BASE_DIR, "frontend")
FRONTEND_DIST = os.path.join(FRONTEND_DIR, "dist")


def check_and_install_python_deps():
    print("[*] Checking Python dependencies...")
    req_file = os.path.join(BASE_DIR, "requirements.txt")
    if os.path.exists(req_file):
        try:
            import flask
            import cv2
            import numpy
        except ImportError:
            print("[+] Installing missing Python packages from requirements.txt...")
            subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", req_file])
            print("[✓] Python dependencies installed.")
    else:
        print("[!] requirements.txt not found, skipping check.")


def build_frontend():
    print("[*] Checking frontend build...")
    if not os.path.exists(FRONTEND_DIR):
        print("[!] Frontend directory not found.")
        return False

    npm_cmd = "npm.cmd" if sys.platform == "win32" else "npm"
    
    # Check if npm is available
    try:
        subprocess.run([npm_cmd, "--version"], capture_output=True, check=True)
    except (subprocess.SubprocessError, FileNotFoundError):
        print("[!] Node/NPM not found on system path. Using Flask built-in Jinja templates UI.")
        return False

    node_modules = os.path.join(FRONTEND_DIR, "node_modules")
    if not os.path.exists(node_modules):
        print("[+] Installing frontend npm dependencies...")
        subprocess.check_call([npm_cmd, "install"], cwd=FRONTEND_DIR)

    print("[+] Building React production bundle with Vite...")
    subprocess.check_call([npm_cmd, "run", "build"], cwd=FRONTEND_DIR)
    print("[✓] Frontend build completed successfully -> frontend/dist.")
    return True


def run_dev():
    print("=" * 60)
    print("  STABIL DEVELOPMENT MODE (Backend + Frontend Hot-Reload)")
    print("=" * 60)
    check_and_install_python_deps()

    npm_cmd = "npm.cmd" if sys.platform == "win32" else "npm"

    # Start Flask Backend in subprocess
    print("[+] Launching Flask backend on http://127.0.0.1:5000 ...")
    backend_proc = subprocess.Popen(
        [sys.executable, "app.py"],
        cwd=BASE_DIR
    )

    # Start Vite Frontend dev server
    print("[+] Launching React Vite frontend on http://localhost:3000 ...")
    frontend_proc = None
    try:
        node_modules = os.path.join(FRONTEND_DIR, "node_modules")
        if not os.path.exists(node_modules):
            subprocess.check_call([npm_cmd, "install"], cwd=FRONTEND_DIR)
        
        frontend_proc = subprocess.Popen(
            [npm_cmd, "run", "dev"],
            cwd=FRONTEND_DIR
        )

        time.sleep(2)
        webbrowser.open("http://localhost:3000")

        # Wait for processes
        backend_proc.wait()
    except KeyboardInterrupt:
        print("\n[!] Stopping development servers...")
    finally:
        if backend_proc and backend_proc.poll() is None:
            backend_proc.terminate()
        if frontend_proc and frontend_proc.poll() is None:
            frontend_proc.terminate()


def run_app(port=5000, open_browser=True):
    print("=" * 60)
    print(f"  STABIL FULLSTACK APPLICATION (Port: {port})")
    print("=" * 60)

    check_and_install_python_deps()

    # If frontend dist doesn't exist yet, attempt to build it if npm is installed
    if not os.path.exists(os.path.join(FRONTEND_DIST, "index.html")):
        build_frontend()

    url = f"http://127.0.0.1:{port}"
    print(f"[✓] Starting server at {url}")
    
    if open_browser:
        def open_tab():
            time.sleep(1.5)
            webbrowser.open(url)
        import threading
        threading.Thread(target=open_tab, daemon=True).start()

    os.environ["PORT"] = str(port)
    from app import app
    app.run(host="0.0.0.0", port=port, debug=False)


def main():
    parser = argparse.ArgumentParser(description="STABIL Deployment & Launcher Utility")
    parser.add_argument("--dev", action="store_true", help="Run in development mode (Flask + Vite concurrently)")
    parser.add_argument("--build", action="store_true", help="Build frontend React distribution bundle")
    parser.add_argument("--port", type=int, default=5000, help="Port to run the application on (default: 5000)")
    parser.add_argument("--no-browser", action="store_true", help="Do not automatically open the web browser")

    args = parser.parse_args()

    if args.build:
        build_frontend()
    elif args.dev:
        run_dev()
    else:
        run_app(port=args.port, open_browser=not args.no_browser)


if __name__ == "__main__":
    main()
