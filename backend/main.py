from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from nlu import parse_event
from calendar_bot import add_event_to_calendar

app = FastAPI()

# ⚡ CORS setup
origins = [
    "http://localhost:8080",  # your frontend URL
    "http://127.0.0.1:8080",
    "file://"                 # optional if using file:// protocol
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,    # can also use ["*"] for testing
    allow_credentials=True,
    allow_methods=["*"],      # allow GET, POST, OPTIONS, etc.
    allow_headers=["*"],
)

class SpeechInput(BaseModel):
    text: str

@app.post("/speech")
def handle_speech(data: SpeechInput):
    event = parse_event(data.text)
    add_event_to_calendar(event)
    return {
        "status": "success",
        "event": event
    }
