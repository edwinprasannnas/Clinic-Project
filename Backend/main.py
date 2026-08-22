"""
Willow Health Clinic — backend API.

Endpoints:
  POST /api/bookings              Create a booking (called from the landing page modal)
  GET  /api/bookings              List bookings (used by the admin dashboard)
  PATCH /api/bookings/{id}/status Update a booking's status (confirm/cancel)
  GET  /api/stream                Server-Sent Events feed — pushes every new booking
                                   or status change to any connected admin dashboard
                                   in real time, no polling needed.

Run:
  pip install -r requirements.txt
  uvicorn main:app --reload --port 8000
"""
import asyncio
import json
from datetime import date as date_cls
from typing import Optional

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field, field_validator

import database as db

app = FastAPI(title="Willow Health Clinic API")

# Allow the landing page (served from any origin/file during dev) to call this API.
# In production, replace "*" with your actual site domain.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

VALID_SERVICES = {
    "General Medicine", "Pediatrics", "Dermatology",
    "Physiotherapy", "Dental Care", "Diagnostics & Lab",
}
VALID_DOCTORS = {
    "Dr. Ananya Rajan", "Dr. Karthik Subramaniam",
    "Dr. Meera Iyer", "Dr. Arjun Nair",
}
VALID_STATUSES = {"pending", "confirmed", "cancelled"}

# --- Real-time fan-out: every connected admin dashboard gets its own queue ---
subscribers: list[asyncio.Queue] = []


async def broadcast(event: dict):
    dead = []
    for q in subscribers:
        try:
            q.put_nowait(event)
        except asyncio.QueueFull:
            dead.append(q)
    for q in dead:
        subscribers.remove(q)


class BookingIn(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    phone: str = Field(min_length=6, max_length=20)
    date: str
    service: str
    doctor: Optional[str] = None

    @field_validator("service")
    @classmethod
    def service_valid(cls, v):
        if v not in VALID_SERVICES:
            raise ValueError(f"Unknown service: {v}")
        return v

    @field_validator("doctor")
    @classmethod
    def doctor_valid(cls, v):
        if v and v not in VALID_DOCTORS:
            raise ValueError(f"Unknown doctor: {v}")
        return v

    @field_validator("date")
    @classmethod
    def date_not_past(cls, v):
        try:
            d = date_cls.fromisoformat(v)
        except ValueError:
            raise ValueError("date must be YYYY-MM-DD")
        if d < date_cls.today():
            raise ValueError("date cannot be in the past")
        return v


class StatusIn(BaseModel):
    status: str

    @field_validator("status")
    @classmethod
    def status_valid(cls, v):
        if v not in VALID_STATUSES:
            raise ValueError(f"status must be one of {VALID_STATUSES}")
        return v


@app.on_event("startup")
def startup():
    db.init_db()


@app.post("/api/bookings")
async def create_booking(payload: BookingIn):
    booking = db.create_booking(
        name=payload.name.strip(),
        phone=payload.phone.strip(),
        date=payload.date,
        service=payload.service,
        doctor=payload.doctor or None,
    )
    await broadcast({"type": "booking_created", "booking": booking})
    return {"ok": True, "booking": booking}


@app.get("/api/bookings")
def get_bookings(status: Optional[str] = None):
    if status and status not in VALID_STATUSES:
        raise HTTPException(400, f"status must be one of {VALID_STATUSES}")
    return {"bookings": db.list_bookings(status)}


@app.patch("/api/bookings/{booking_id}/status")
async def set_status(booking_id: int, payload: StatusIn):
    booking = db.update_booking_status(booking_id, payload.status)
    if not booking:
        raise HTTPException(404, "Booking not found")
    await broadcast({"type": "status_changed", "booking": booking})
    return {"ok": True, "booking": booking}


@app.get("/api/activity")
def get_activity():
    return {"activity": db.recent_activity()}


@app.get("/api/stream")
async def stream(request: Request):
    """Server-Sent Events — the admin dashboard listens here for live updates."""
    queue: asyncio.Queue = asyncio.Queue(maxsize=100)
    subscribers.append(queue)

    async def event_generator():
        try:
            yield f"data: {json.dumps({'type': 'connected'})}\n\n"
            while True:
                if await request.is_disconnected():
                    break
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=15)
                    yield f"data: {json.dumps(event)}\n\n"
                except asyncio.TimeoutError:
                    yield ": keep-alive\n\n"  # comment line, keeps the connection open
        finally:
            if queue in subscribers:
                subscribers.remove(queue)

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@app.get("/api/health")
def health():
    return {"status": "ok"}
