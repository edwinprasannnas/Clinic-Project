# Willow Health Clinic — Backend

A minimal, real, working backend for the booking form on your landing page.

## What's inside

```
backend/
  main.py          FastAPI app — the API your frontend talks to
  database.py       SQLite storage layer
  requirements.txt
admin/
  dashboard.html    Live bookings dashboard (open directly in a browser)
```

## 1. Run the backend

```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

This starts the API at `http://localhost:8000` and creates `clinic.db`
(a SQLite file) next to `main.py` on first run — no separate database
server to install.

Check it's alive: `curl http://localhost:8000/api/health` → `{"status":"ok"}`

## 2. Wire your landing page to it

In your HTML file, replace the `submitForm` function in the `<script>` block
at the bottom with this:

```javascript
const API_BASE = "http://localhost:8000"; // change to your deployed URL later

async function submitForm(e){
  e.preventDefault();
  const payload = {
    name: document.getElementById('name').value,
    phone: document.getElementById('phone').value,
    date: document.getElementById('date').value,
    service: document.getElementById('service').value,
    doctor: document.getElementById('doctor').value || null,
  };

  const btn = e.target.querySelector('button[type="submit"]');
  btn.disabled = true; btn.textContent = 'Sending…';

  try {
    const res = await fetch(`${API_BASE}/api/bookings`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail?.[0]?.msg || 'Could not book this slot');
    }
    document.getElementById('confirmText').textContent =
      `Thanks, ${payload.name}. Your request for ${payload.service} has been noted — we'll call to confirm your slot.`;
    formView.style.display = 'none';
    confirmView.style.display = 'block';
  } catch (err) {
    alert(err.message);
  } finally {
    btn.disabled = false; btn.textContent = 'Request Appointment';
  }
}
```

That's the only change needed — the rest of your page (modal open/close,
validation, styling) stays exactly as is.

## 3. Watch bookings come in live

Open `admin/dashboard.html` directly in a browser (double-click it, or
`open admin/dashboard.html`) while the backend is running. It connects to
`/api/stream` over Server-Sent Events, so as soon as someone books on the
landing page, the row appears in the dashboard instantly — no refresh,
no polling. You can also confirm/cancel bookings from the dropdown in
each row, and that update is pushed live too.

## API reference

| Method | Path                          | Purpose                              |
|--------|-------------------------------|---------------------------------------|
| POST   | `/api/bookings`                | Create a booking (used by the modal)  |
| GET    | `/api/bookings?status=pending` | List bookings, optional status filter |
| PATCH  | `/api/bookings/{id}/status`    | Set status: pending/confirmed/cancelled |
| GET    | `/api/activity`                | Recent activity log                   |
| GET    | `/api/stream`                  | SSE feed for real-time dashboards     |

## About "real-time database"

You don't actually need a special "real-time database product" here — the
real-time behavior (live dashboard updates) comes from the SSE endpoint in
`main.py`, which pushes events to connected browsers the moment a booking
is written to SQLite. That's enough for a single clinic on one server.

**If you outgrow this** (multiple clinics, multiple servers, need for
bookings to sync across many independent apps/services), swap SQLite for
managed PostgreSQL — for example **Supabase** (Postgres + built-in realtime
subscriptions over websockets) or **Neon**. The `database.py` module is
deliberately isolated so you can swap its internals for `psycopg`/SQLAlchemy
+ Postgres without touching `main.py`'s routes.

## Deploying

Any host that runs a Python process works: Railway, Render, Fly.io, or a
small VPS. Point `API_BASE` in your landing page and `admin/dashboard.html`
at the deployed URL, and set `allow_origins` in `main.py` to your actual
domain instead of `"*"`.
