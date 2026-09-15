

import os
import sys
import time
import threading
import logging
from typing import Optional, Dict, Any, List

logger = logging.getLogger("stabil.hardware")

try:
    import serial
    import serial.tools.list_ports
    HAS_SERIAL = True
except ImportError:
    HAS_SERIAL = False
    logger.warning("pyserial is not installed. Hardware serial features will be simulated or disabled.")


class ArduinoReachReader:
    def __init__(self, port: Optional[str] = None, baud: int = 9600):
        self.port = port or os.environ.get("ARDUINO_PORT")
        self.baud = baud
        self.serial_conn = None
        self.running = False
        self.thread = None
        self.lock = threading.Lock()

        self.latest_distance: Optional[float] = None
        self.is_connected = False
        self.last_seen_time = 0.0

        # Active session metrics buffer
        self.session_active = False
        self.session_readings: List[float] = []
        self.session_violations = 0
        self.buzz_threshold = 10.0

    def list_available_ports(self) -> List[Dict[str, str]]:
        if not HAS_SERIAL:
            return []
        ports = list(serial.tools.list_ports.comports())
        return [{"device": p.device, "description": p.description or p.device} for p in ports]

    def find_port(self) -> Optional[str]:
        if self.port:
            return self.port
        if not HAS_SERIAL:
            return None

        ports = list(serial.tools.list_ports.comports())
        # Priority 1: Match known Arduino/USB-serial descriptions
        for p in ports:
            desc = (p.description or "").lower()
            hwid = (p.hwid or "").lower()
            if any(k in desc or k in hwid for k in ["arduino", "ch340", "ftdi", "cp210", "usb-serial", "usb serial"]):
                logger.info(f"Detected Arduino hardware on port: {p.device} ({p.description})")
                return p.device

        # Priority 2: If only one or two COM ports exist, return the first
        if ports:
            return ports[0].device
        return None

    def connect(self, port: Optional[str] = None) -> bool:
        if not HAS_SERIAL:
            return False

        if port and self.serial_conn and self.port != port:
            self.disconnect()

        target_port = port or self.find_port()
        if not target_port:
            logger.debug("No serial port specified or detected.")
            return False

        try:
            self.serial_conn = serial.Serial(
                port=target_port,
                baudrate=self.baud,
                timeout=1.0
            )
            self.port = target_port
            self.is_connected = True
            self.running = True
            self.thread = threading.Thread(target=self._reader_loop, daemon=True)
            self.thread.start()
            logger.info(f"Connected to Arduino on {self.port} at {self.baud} baud.")
            return True
        except Exception as e:
            logger.debug(f"Could not open serial port {target_port}: {e}")
            self.is_connected = False
            self.serial_conn = None
            return False

    def disconnect(self):
        self.running = False
        if self.serial_conn:
            try:
                self.serial_conn.close()
            except Exception:
                pass
        self.is_connected = False
        self.serial_conn = None

    def _reader_loop(self):
        while self.running and self.serial_conn and self.serial_conn.is_open:
            try:
                raw_line = self.serial_conn.readline()
                if not raw_line:
                    continue
                line = raw_line.decode("utf-8", errors="ignore").strip()
                self._parse_line(line)
            except Exception as e:
                logger.debug(f"Serial read error: {e}")
                time.sleep(0.1)

    def _parse_line(self, line: str):
        if not line:
            return
        if line.startswith("DIST:"):
            val_str = line[5:].strip()
            if val_str == "NA":
                with self.lock:
                    self.latest_distance = None
                    self.last_seen_time = time.time()
            else:
                try:
                    dist = float(val_str)
                    with self.lock:
                        self.latest_distance = dist
                        self.last_seen_time = time.time()
                        if self.session_active:
                            self.session_readings.append(dist)
                            if dist < self.buzz_threshold:
                                self.session_violations += 1
                except ValueError:
                    pass

    def start_session(self):
        with self.lock:
            self.session_active = True
            self.session_readings = []
            self.session_violations = 0
            if not self.is_connected:
                # Try connecting if not already connected
                self.connect()

    def stop_session(self):
        with self.lock:
            self.session_active = False

    def get_current_distance(self) -> Optional[float]:
        with self.lock:
            # If reading is older than 3 seconds, treat as stale
            if time.time() - self.last_seen_time > 3.0:
                return None
            return self.latest_distance

    def get_session_metrics(self) -> Dict[str, Any]:
        with self.lock:
            readings = list(self.session_readings)
            violations = self.session_violations
            connected = self.is_connected

        if not readings:
            return {
                "reach_distance": None,
                "reach_error": 0.0,
                "min_reach": None,
                "max_reach": None,
                "reach_violations": 0,
                "reach_samples": 0,
                "reach_sensor_connected": connected
            }

        import numpy as np
        arr = np.array(readings, dtype=float)
        mean_reach = float(np.mean(arr))
        reach_std = float(np.std(arr)) if len(arr) > 1 else 0.0
        min_reach = float(np.min(arr))
        max_reach = float(np.max(arr))

        return {
            "reach_distance": round(mean_reach, 2),
            "reach_error": round(reach_std, 2),
            "min_reach": round(min_reach, 2),
            "max_reach": round(max_reach, 2),
            "reach_violations": int(violations),
            "reach_samples": len(readings),
            "reach_sensor_connected": True
        }

    def inject_synthetic_reading(self, distance: float):
        """Used for automated test suites or simulated training runs."""
        with self.lock:
            self.latest_distance = distance
            self.last_seen_time = time.time()
            if self.session_active:
                self.session_readings.append(distance)
                if distance < self.buzz_threshold:
                    self.session_violations += 1


# Global singleton reader
_hardware_reader = None

def get_hardware_reader() -> ArduinoReachReader:
    global _hardware_reader
    if _hardware_reader is None:
        _hardware_reader = ArduinoReachReader()
        # Attempt non-blocking connect on startup
        try:
            _hardware_reader.connect()
        except Exception:
            pass
    return _hardware_reader
