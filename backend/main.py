from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from nlu import parse_event
from calendar_bot import add_event_to_calendar
import subprocess
import time
import os

latest_recognized_text = None

app = FastAPI()

print("[DEBUG] FastAPI app starting...")

# ⚡ CORS setup
origins = [
    "http://localhost:8080",
    "http://127.0.0.1:8080",
    "file://"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],     # OK for debugging
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class SpeechInput(BaseModel):
    text: str
    
CHROME_PATH = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
USER_DATA_DIR = r"C:\temp\chrome_debug_profile"
DEBUG_PORT = 9222

os.makedirs(USER_DATA_DIR, exist_ok=True)

cmd = [
    CHROME_PATH,
    f"--remote-debugging-port={DEBUG_PORT}",
    f"--user-data-dir={USER_DATA_DIR}",
    "--no-first-run",
    "--no-default-browser-check",
]

chrome_proc = subprocess.Popen(cmd)

# 等待 Chrome 完全启动
time.sleep(3)

print("Chrome 已启动，调试端口:", DEBUG_PORT)

@app.post("/speech")
def handle_speech(data: SpeechInput):
    global latest_recognized_text
    latest_recognized_text = data.text
    print("[DEBUG] /speech endpoint called")
    print("[DEBUG] Raw input text:", data.text)

    print("[DEBUG] Parsing event from text...")
    event = parse_event(data.text)

    print("[DEBUG] Parsed event:", event)

    print("[DEBUG] Adding event to Google Calendar...")
    add_event_to_calendar(event)

    print("[DEBUG] Calendar event process finished")

    response = {
        "status": "success",
        "event": event
    }

    print("[DEBUG] Response sent to frontend:", response)
    return response

#chrome_proc.terminate()     # or .kill()
#chrome_proc.wait()