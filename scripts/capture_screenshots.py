import os
import sys
import time
import subprocess
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
SCREENSHOTS_DIR = BASE_DIR / "docs" / "screenshots"
SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)

CHROME_BIN = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
if not os.path.exists(CHROME_BIN):
    CHROME_BIN = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"

print(f"Using browser binary: {CHROME_BIN}")

PAGES = [
    {
        "name": "overview_dashboard.png",
        "url": "http://127.0.0.1:5173/#overview",
        "delay_ms": 3000,
        "width": 1440,
        "height": 960
    },
    {
        "name": "flood_analysis_map.png",
        "url": "http://127.0.0.1:5173/#flood-analysis",
        "delay_ms": 5000,
        "width": 1440,
        "height": 1080
    },
    {
        "name": "infrastructure_exposure_map.png",
        "url": "http://127.0.0.1:5173/#infrastructure",
        "delay_ms": 5000,
        "width": 1440,
        "height": 1080
    },
    {
        "name": "settlement_connectivity_map.png",
        "url": "http://127.0.0.1:5173/#connectivity",
        "delay_ms": 5000,
        "width": 1440,
        "height": 1080
    },
    {
        "name": "situation_report_en.png",
        "url": "http://127.0.0.1:5173/#ai-report",
        "delay_ms": 4000,
        "width": 1440,
        "height": 1200
    },
    {
        "name": "situation_report_ne.png",
        "url": "http://127.0.0.1:5173/?lang=ne#ai-report",
        "delay_ms": 4000,
        "width": 1440,
        "height": 1200
    },
    {
        "name": "pdf_report_preview.png",
        "url": (BASE_DIR / "data" / "outputs" / "e2e-trishuli-aug2026" / "situation_report_en.pdf").as_uri(),
        "delay_ms": 3000,
        "width": 1200,
        "height": 1400
    }
]

def capture():
    for item in PAGES:
        output_file = SCREENSHOTS_DIR / item["name"]
        print(f"Capturing {item['name']} from {item['url']}...")
        cmd = [
            CHROME_BIN,
            "--headless=new",
            "--disable-gpu",
            "--hide-scrollbars",
            f"--window-size={item['width']},{item['height']}",
            f"--virtual-time-budget={item['delay_ms']}",
            f"--screenshot={str(output_file)}",
            item["url"]
        ]
        res = subprocess.run(cmd, capture_output=True, text=True)
        if output_file.exists() and output_file.stat().st_size > 0:
            print(f"  -> SUCCESS: {item['name']} ({output_file.stat().st_size} bytes)")
        else:
            print(f"  -> WARNING: Failed to capture {item['name']}. stderr: {res.stderr}")

if __name__ == "__main__":
    capture()
